import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    pseudonym_id = Column(String(64), unique=True, index=True)  # e.g., "PT-A892" (HIPAA safe)
    cohort = Column(String(64), default="General Medicine")    # Cardiology, Oncology, Ortho, etc.
    primary_diagnosis = Column(String(128), default="Unspecified")
    admission_time = Column(DateTime, nullable=True)
    discharge_time = Column(DateTime, nullable=True)
    total_duration_hours = Column(Float, default=0.0)
    status = Column(String(32), default="ACTIVE")  # ACTIVE, DISCHARGED, STALLED

    events = relationship("ClinicalEvent", back_populates="patient", cascade="all, delete-orphan")

class ClinicalEvent(Base):
    __tablename__ = "clinical_events"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    event_type = Column(String(64), index=True)  # e.g. TRIAGE, LAB_ORDER, PRIOR_AUTH_SUBMITTED
    source_system = Column(String(32), index=True)  # EHR, PACS, PAYER, SCHEDULING
    timestamp = Column(DateTime, index=True)        # Corrected normalized timestamp
    original_timestamp = Column(String(64))         # Original raw timestamp string
    raw_payload = Column(Text, nullable=True)
    status = Column(String(32), default="ACCEPTED") # ACCEPTED, AUTOCORRECTED, DUPLICATE_SUPPRESSED
    anomaly_tags = Column(String(255), default="[]") # JSON list of detected anomalies
    metadata_json = Column(Text, default="{}")       # Department, doctor ratio, lab batch latency, payer ID

    patient = relationship("Patient", back_populates="events")

class QuarantinedPayload(Base):
    __tablename__ = "quarantined_payloads"

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(32))
    received_at = Column(DateTime, default=datetime.datetime.utcnow)
    raw_payload = Column(Text)
    reason = Column(String(255))
    resolved = Column(Boolean, default=False)

class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    sequence_number = Column(Integer, unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    action = Column(String(64))  # INGEST_EVENT, AUTOCORRECT, QUARANTINE, RECONSTRUCT_JOURNEY
    actor = Column(String(64), default="SYSTEM_INGEST_GATEWAY")
    event_fingerprint = Column(String(64))
    previous_hash = Column(String(64))
    current_hash = Column(String(64), index=True)
