from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db, Base, engine
from backend.app.models.orm_models import AuditLogEntry, Patient, ClinicalEvent, QuarantinedPayload
from backend.app.core.hipaa_security import verify_audit_chain_integrity
from backend.app.data.synthetic_generator import seed_synthetic_database

router = APIRouter(prefix="/audit", tags=["HIPAA Compliance & Audit Integrity"])

@router.get("/logs")
def list_audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Retrieves immutable SHA-256 chained audit log records."""
    logs = db.query(AuditLogEntry).order_by(AuditLogEntry.sequence_number.desc()).limit(limit).all()
    return [{
        "sequence_number": l.sequence_number,
        "timestamp": l.timestamp.isoformat() if l.timestamp else None,
        "action": l.action,
        "actor": l.actor,
        "event_fingerprint": l.event_fingerprint,
        "previous_hash": l.previous_hash,
        "current_hash": l.current_hash
    } for l in logs]

@router.get("/verify")
def verify_integrity(db: Session = Depends(get_db)):
    """
    Executes a cryptographic proof verification of the entire SHA-256 audit ledger.
    Guarantees that no clinical record or timestamp has been tampered with.
    """
    return verify_audit_chain_integrity(db)

@router.post("/seed")
def seed_data(patients: int = 120, db: Session = Depends(get_db)):
    """Initializes the database with multi-component patient traces and adversarial benchmarks."""
    return seed_synthetic_database(db, num_patients=patients)

@router.post("/reset")
def reset_database(db: Session = Depends(get_db)):
    """Resets and regenerates the database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return seed_synthetic_database(db, num_patients=120)
