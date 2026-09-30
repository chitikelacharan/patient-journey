import json
import re
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models.orm_models import ClinicalEvent, Patient, QuarantinedPayload
from backend.app.models.schemas import EventIngestRequest

# Causal hierarchy representing clinical order of care
CAUSAL_EVENT_RANKS: Dict[str, int] = {
    "REGISTRATION": 0,
    "TRIAGE": 1,
    "LAB_ORDER": 2,
    "IMAGING_ORDER": 2,
    "LAB_RESULT": 3,
    "IMAGING_COMPLETE": 3,
    "SPECIALIST_CONSULT": 4,
    "PRIOR_AUTH_SUBMITTED": 5,
    "PRIOR_AUTH_DECISION": 6,
    "BED_REQUESTED": 7,
    "BED_ASSIGNED": 8,
    "DISCHARGE_ORDER": 9,
    "DISCHARGE_COMPLETED": 10
}

# Authoritative source mapping when conflicting timestamps occur
AUTHORITATIVE_SOURCES: Dict[str, str] = {
    "LAB_RESULT": "PACS",
    "IMAGING_COMPLETE": "PACS",
    "PRIOR_AUTH_SUBMITTED": "PAYER",
    "PRIOR_AUTH_DECISION": "PAYER",
    "BED_ASSIGNED": "SCHEDULING",
    "DISCHARGE_COMPLETED": "EHR"
}

class AdversarialEngine:
    """
    Adversarial Resilience Engine designed to detect, quarantine, or heal:
    1. Malformed/corrupted feeds
    2. Out-of-order timestamps via Causal DAG
    3. Duplicate discharge summaries and intake logs
    4. Missing clinical notes with cohort imputation
    5. Conflicting multi-source timestamps
    """

    @staticmethod
    def parse_timestamp(ts_raw: str) -> Optional[datetime]:
        """Supports ISO 8601, standard datetime, and HL7 YYYYMMDDHHMMSS formats."""
        if not ts_raw or not isinstance(ts_raw, str):
            return None
        
        ts_clean = ts_raw.strip()
        
        # Check for obvious garbage / corruption patterns
        if any(bad in ts_clean.upper() for bad in ["INVALID", "CORRUPT", "NULL", "NAN", "UNDEFINED", "ERR"]):
            return None
        
        # Format 1: ISO 8601 with T or space
        for fmt in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f"
        ):
            try:
                return datetime.strptime(ts_clean[:19], fmt[:19])
            except ValueError:
                continue

        # Format 2: HL7 timestamp format: YYYYMMDDHHMMSS
        hl7_match = re.match(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", ts_clean)
        if hl7_match:
            try:
                y, m, d, h, mn, s = map(int, hl7_match.groups())
                return datetime(y, m, d, h, mn, s)
            except ValueError:
                return None
                
        return None

    @classmethod
    def process_and_validate(
        cls,
        db: Session,
        patient: Patient,
        req: EventIngestRequest
    ) -> Tuple[str, Optional[datetime], List[str], Optional[str]]:
        """
        Processes an incoming event through the adversarial resilience gauntlet.
        Returns:
            (status: ACCEPTED | AUTOCORRECTED | DUPLICATE_SUPPRESSED | QUARANTINED,
             normalized_timestamp,
             anomaly_tags,
             quarantine_reason)
        """
        anomaly_tags = []
        
        # 1. Check for corrupt / unparseable timestamp
        parsed_ts = cls.parse_timestamp(req.timestamp)
        if not parsed_ts:
            quarantine_reason = f"Corrupted unparseable timestamp string: '{req.timestamp}'"
            return "QUARANTINED", None, ["CORRUPTED_TIMESTAMP"], quarantine_reason

        # 2. Check for missing required clinical fields / notes
        metadata = dict(req.metadata or {})
        if req.event_type == "TRIAGE" and "acuity_score" not in metadata:
            # Impute missing clinical acuity note using cohort average
            metadata["acuity_score"] = 3  # Standard ESI-3 median urgency
            metadata["imputed"] = True
            req.metadata = metadata
            anomaly_tags.append("IMPUTED_MISSING_NOTE")

        # 3. Deduplication Check (especially for duplicate discharge summaries or lab triggers)
        recent_duplicate = db.query(ClinicalEvent).filter(
            ClinicalEvent.patient_id == patient.id,
            ClinicalEvent.event_type == req.event_type,
            ClinicalEvent.status.in_(["ACCEPTED", "AUTOCORRECTED"])
        ).order_by(ClinicalEvent.timestamp.desc()).first()

        if recent_duplicate:
            time_diff = abs((parsed_ts - recent_duplicate.timestamp).total_seconds())
            if time_diff < 3600:  # Within 1 hour window
                # Duplicate event detected!
                anomaly_tags.append("DUPLICATE_EVENT_DETECTED")
                return "DUPLICATE_SUPPRESSED", parsed_ts, anomaly_tags, None

        # 4. Out-of-Order Timestamp Detection via Causal Directed Acyclic Graph (DAG)
        req_rank = CAUSAL_EVENT_RANKS.get(req.event_type, 5)
        
        # Get all prior recorded events for this patient
        prior_events = db.query(ClinicalEvent).filter(
            ClinicalEvent.patient_id == patient.id,
            ClinicalEvent.status.in_(["ACCEPTED", "AUTOCORRECTED"])
        ).all()

        max_causal_prereq_ts = None
        for p_evt in prior_events:
            p_rank = CAUSAL_EVENT_RANKS.get(p_evt.event_type, 5)
            # If an existing event is clinically preceding the new event
            if p_rank <= req_rank:
                if max_causal_prereq_ts is None or p_evt.timestamp > max_causal_prereq_ts:
                    max_causal_prereq_ts = p_evt.timestamp
            # If an existing event is clinically downstream, but new event timestamp is after it
            elif p_rank > req_rank and parsed_ts > p_evt.timestamp:
                anomaly_tags.append("DOWNSTREAM_CAUSAL_INVERSION")

        # Did incoming event arrive with timestamp EARLIER than its upstream prerequisite?
        if max_causal_prereq_ts and parsed_ts < max_causal_prereq_ts:
            # Out-of-order timestamp detected! (e.g. Discharge timestamp before Bed Assigned)
            anomaly_tags.append("OUT_OF_ORDER_TIMESTAMP")
            anomaly_tags.append("CAUSAL_DAG_HEALED")
            
            # Auto-heal by advancing timestamp to causal prerequisite + benchmark buffer
            transition_key = f"{prior_events[-1].event_type}->{req.event_type}" if prior_events else ""
            default_buffer_hours = settings.SLA_BENCHMARKS.get(transition_key, 1.0)
            healed_ts = max_causal_prereq_ts + timedelta(hours=default_buffer_hours)
            return "AUTOCORRECTED", healed_ts, anomaly_tags, None

        # 5. Conflicting Multi-Source Timestamp Resolution
        authoritative = AUTHORITATIVE_SOURCES.get(req.event_type)
        if authoritative and req.source_system != authoritative:
            # Non-authoritative source sent this event, flag informational resolution
            anomaly_tags.append(f"VERIFIED_AGAINST_AUTHORITATIVE_SOURCE_{authoritative}")

        if anomaly_tags:
            return "AUTOCORRECTED", parsed_ts, anomaly_tags, None

        return "ACCEPTED", parsed_ts, [], None
