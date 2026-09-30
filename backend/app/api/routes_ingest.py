import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.orm_models import Patient, ClinicalEvent, QuarantinedPayload
from backend.app.models.schemas import EventIngestRequest, EventIngestResponse
from backend.app.core.hipaa_security import generate_pseudonym, compute_payload_fingerprint, record_audit_entry
from backend.app.core.adversarial_engine import AdversarialEngine

router = APIRouter(prefix="/ingest", tags=["Multi-Source Ingestion & Adversarial Gateway"])

@router.post("/event", response_model=EventIngestResponse)
def ingest_clinical_event(req: EventIngestRequest, db: Session = Depends(get_db)):
    """
    Ingests an individual clinical event from EHR, PACS, Payer, or Scheduling feeds.
    Passes data through the Adversarial Resilience Engine to auto-correct out-of-order timestamps,
    suppress duplicates, impute missing fields, or quarantine corrupt feeds.
    """
    pseudo_id = generate_pseudonym(req.patient_identifier)
    
    # Retrieve or create patient record
    patient = db.query(Patient).filter(Patient.pseudonym_id == pseudo_id).first()
    if not patient:
        patient = Patient(
            pseudonym_id=pseudo_id,
            cohort=req.cohort or "General Medicine",
            primary_diagnosis=req.primary_diagnosis or "Unspecified",
            status="ACTIVE"
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    # Validate and process through Adversarial Engine
    event_status, final_ts, tags, q_reason = AdversarialEngine.process_and_validate(
        db=db,
        patient=patient,
        req=req
    )

    fingerprint = compute_payload_fingerprint(req.model_dump())

    if event_status == "QUARANTINED":
        q = QuarantinedPayload(
            source_system=req.source_system,
            raw_payload=json.dumps(req.model_dump(), default=str),
            reason=q_reason
        )
        db.add(q)
        db.commit()
        
        audit_entry = record_audit_entry(
            db=db,
            action=f"QUARANTINED_{req.event_type}",
            event_fingerprint=fingerprint
        )
        
        return EventIngestResponse(
            status="QUARANTINED",
            patient_pseudonym=pseudo_id,
            event_id=None,
            anomaly_detected=True,
            anomaly_tags=tags,
            audit_hash=audit_entry.current_hash,
            message=f"Payload quarantined: {q_reason}"
        )

    if event_status == "DUPLICATE_SUPPRESSED":
        audit_entry = record_audit_entry(
            db=db,
            action=f"SUPPRESSED_DUPLICATE_{req.event_type}",
            event_fingerprint=fingerprint
        )
        return EventIngestResponse(
            status="DUPLICATE_SUPPRESSED",
            patient_pseudonym=pseudo_id,
            event_id=None,
            anomaly_detected=True,
            anomaly_tags=tags,
            audit_hash=audit_entry.current_hash,
            message="Duplicate clinical summary suppressed to protect metric accuracy."
        )

    # Ingest clean or autocorrected event
    db_event = ClinicalEvent(
        patient_id=patient.id,
        event_type=req.event_type,
        source_system=req.source_system,
        timestamp=final_ts,
        original_timestamp=req.timestamp,
        raw_payload=json.dumps(req.metadata or {}, default=str),
        status=event_status,
        anomaly_tags=json.dumps(tags),
        metadata_json=json.dumps(req.metadata or {})
    )
    db.add(db_event)
    
    # Update patient timeline boundaries
    if not patient.admission_time or final_ts < patient.admission_time:
        patient.admission_time = final_ts
    if req.event_type == "DISCHARGE_COMPLETED":
        patient.discharge_time = final_ts
        patient.status = "DISCHARGED"
        if patient.admission_time:
            patient.total_duration_hours = max(0.1, (final_ts - patient.admission_time).total_seconds() / 3600.0)

    db.commit()
    db.refresh(db_event)

    audit_entry = record_audit_entry(
        db=db,
        action=f"INGEST_{event_status}_{req.event_type}",
        event_fingerprint=fingerprint
    )

    msg = "Event normalized and ingested successfully."
    if event_status == "AUTOCORRECTED":
        msg = f"Event normalized with auto-correction: {', '.join(tags)}"

    return EventIngestResponse(
        status=event_status,
        patient_pseudonym=pseudo_id,
        event_id=db_event.id,
        anomaly_detected=len(tags) > 0,
        anomaly_tags=tags,
        audit_hash=audit_entry.current_hash,
        message=msg
    )
