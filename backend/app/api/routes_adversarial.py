import json
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.orm_models import QuarantinedPayload, Patient, ClinicalEvent
from backend.app.models.schemas import AdversarialTestRequest, EventIngestRequest
from backend.app.api.routes_ingest import ingest_clinical_event

router = APIRouter(prefix="/adversarial", tags=["Adversarial Resilience Sandbox"])

@router.post("/inject")
def inject_adversarial_anomaly(req: AdversarialTestRequest, db: Session = Depends(get_db)):
    """
    Interactive test harness allowing clinicians or evaluators to deliberately inject
    corrupted, out-of-order, duplicate, or malformed payloads and witness real-time healing.
    """
    now = datetime.now(timezone.utc)
    patient_id = req.patient_identifier or "TEST-ADV-101"

    if req.scenario == "OUT_OF_ORDER":
        # First ensure patient has an admission event at T=now
        ingest_clinical_event(EventIngestRequest(
            patient_identifier=patient_id,
            event_type="REGISTRATION",
            source_system="EHR",
            timestamp=now.isoformat(),
            cohort=req.cohort or "Emergency"
        ), db=db)

        # Now deliberately send a DISCHARGE_COMPLETED event timestamped 24 hours BEFORE admission!
        adversarial_event = EventIngestRequest(
            patient_identifier=patient_id,
            event_type="DISCHARGE_COMPLETED",
            source_system="EHR",
            timestamp=(now - timedelta(hours=24)).isoformat(),
            cohort=req.cohort or "Emergency",
            metadata={"notes": "Adversarial test: inverted chronologies"}
        )
        resp = ingest_clinical_event(adversarial_event, db=db)
        return {
            "scenario": "OUT_OF_ORDER_TIMESTAMP",
            "injection_description": "Injected DISCHARGE_COMPLETED event dated 24h prior to patient REGISTRATION.",
            "engine_action": "Causal DAG reordered timestamp forward past prerequisite with standard buffer.",
            "result": resp
        }

    elif req.scenario == "DUPLICATE_DISCHARGE":
        # Send primary discharge
        ingest_clinical_event(EventIngestRequest(
            patient_identifier=patient_id,
            event_type="DISCHARGE_COMPLETED",
            source_system="EHR",
            timestamp=now.isoformat(),
            cohort=req.cohort or "Cardiology"
        ), db=db)

        # Immediately send duplicate discharge summary
        dup_event = EventIngestRequest(
            patient_identifier=patient_id,
            event_type="DISCHARGE_COMPLETED",
            source_system="EHR",
            timestamp=(now + timedelta(seconds=45)).isoformat(),
            cohort=req.cohort or "Cardiology",
            metadata={"notes": "Duplicate EHR webhook transmission"}
        )
        resp = ingest_clinical_event(dup_event, db=db)
        return {
            "scenario": "DUPLICATE_DISCHARGE_SUMMARY",
            "injection_description": "Injected duplicate discharge summary within 45 seconds of original event.",
            "engine_action": "Payload fingerprint matched active window; duplicate suppressed to protect metric accuracy.",
            "result": resp
        }

    elif req.scenario == "CORRUPTED_TIMESTAMP":
        corrupted_event = EventIngestRequest(
            patient_identifier=patient_id,
            event_type="LAB_RESULT",
            source_system="PACS",
            timestamp="2026-INVALID-DATE_HEX_ERR##NULL",
            cohort=req.cohort or "Oncology",
            metadata={"panel": "Troponin-T"}
        )
        resp = ingest_clinical_event(corrupted_event, db=db)
        return {
            "scenario": "CORRUPTED_TIMESTAMP",
            "injection_description": "Injected unparseable corrupt timestamp string: '2026-INVALID-DATE_HEX_ERR##NULL'.",
            "engine_action": "Payload safely routed to Quarantine Vault with zero metric pollution or server crash.",
            "result": resp
        }

    elif req.scenario == "MISSING_CLINICAL_NOTE":
        missing_note_event = EventIngestRequest(
            patient_identifier=patient_id,
            event_type="TRIAGE",
            source_system="EHR",
            timestamp=now.isoformat(),
            cohort=req.cohort or "Emergency",
            metadata={}  # Empty metadata without required acuity_score
        )
        resp = ingest_clinical_event(missing_note_event, db=db)
        return {
            "scenario": "MISSING_CLINICAL_NOTE",
            "injection_description": "Injected emergency triage log missing mandated clinical acuity score.",
            "engine_action": "Engine imputed cohort median acuity score (ESI-3) and attached anomaly tracking tag.",
            "result": resp
        }

    elif req.scenario == "CONFLICTING_SOURCE":
        conflicting_event = EventIngestRequest(
            patient_identifier=patient_id,
            event_type="LAB_RESULT",
            source_system="SCHEDULING",  # Non-authoritative for lab results (PACS is authoritative)
            timestamp=now.isoformat(),
            cohort=req.cohort or "General Surgery",
            metadata={"note": "Scheduling feed claiming lab result completed"}
        )
        resp = ingest_clinical_event(conflicting_event, db=db)
        return {
            "scenario": "CONFLICTING_SOURCE",
            "injection_description": "Injected lab result event from SCHEDULING feed rather than authoritative PACS gateway.",
            "engine_action": "Resolved via authoritative precedence matrix (PACS > SCHEDULING).",
            "result": resp
        }

    return {"error": f"Unknown scenario: {req.scenario}"}

@router.get("/quarantine")
def list_quarantined_records(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieves all quarantined payloads for compliance review."""
    records = db.query(QuarantinedPayload).order_by(QuarantinedPayload.id.desc()).limit(limit).all()
    return [{
        "id": r.id,
        "source_system": r.source_system,
        "received_at": r.received_at.isoformat() if r.received_at else None,
        "raw_payload": r.raw_payload,
        "reason": r.reason,
        "resolved": r.resolved
    } for r in records]
