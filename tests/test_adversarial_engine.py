import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.orm_models import Patient, ClinicalEvent, QuarantinedPayload
from backend.app.models.schemas import EventIngestRequest
from backend.app.core.adversarial_engine import AdversarialEngine
from backend.app.core.hipaa_security import generate_pseudonym

# In-memory test SQLite DB
@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_out_of_order_timestamp_healing(test_db):
    """Verifies that an inverted timestamp is detected and healed via Causal DAG."""
    pseudo = generate_pseudonym("TEST-MRN-001")
    patient = Patient(pseudonym_id=pseudo, cohort="Emergency")
    test_db.add(patient)
    test_db.commit()

    base_time = datetime(2026, 9, 20, 10, 0, 0)
    
    # 1. Add registration event
    evt1 = ClinicalEvent(
        patient_id=patient.id,
        event_type="REGISTRATION",
        source_system="EHR",
        timestamp=base_time,
        original_timestamp=base_time.isoformat(),
        status="ACCEPTED"
    )
    test_db.add(evt1)
    test_db.commit()

    # 2. Ingest downstream DISCHARGE_COMPLETED with timestamp 5 hours BEFORE registration!
    corrupt_ts = (base_time - timedelta(hours=5)).isoformat()
    req = EventIngestRequest(
        patient_identifier="TEST-MRN-001",
        event_type="DISCHARGE_COMPLETED",
        source_system="EHR",
        timestamp=corrupt_ts
    )

    status, healed_ts, tags, q_reason = AdversarialEngine.process_and_validate(test_db, patient, req)

    assert status == "AUTOCORRECTED"
    assert "OUT_OF_ORDER_TIMESTAMP" in tags
    assert "CAUSAL_DAG_HEALED" in tags
    # Healed timestamp should be adjusted strictly AFTER registration
    assert healed_ts > base_time

def test_duplicate_event_suppression(test_db):
    """Verifies that identical events received within 1 hour are suppressed."""
    pseudo = generate_pseudonym("TEST-MRN-002")
    patient = Patient(pseudonym_id=pseudo, cohort="Cardiology")
    test_db.add(patient)
    test_db.commit()

    now = datetime(2026, 9, 20, 12, 0, 0)
    evt1 = ClinicalEvent(
        patient_id=patient.id,
        event_type="DISCHARGE_COMPLETED",
        source_system="EHR",
        timestamp=now,
        original_timestamp=now.isoformat(),
        status="ACCEPTED"
    )
    test_db.add(evt1)
    test_db.commit()

    # Second discharge summary arriving 2 minutes later
    req = EventIngestRequest(
        patient_identifier="TEST-MRN-002",
        event_type="DISCHARGE_COMPLETED",
        source_system="EHR",
        timestamp=(now + timedelta(minutes=2)).isoformat()
    )

    status, _, tags, _ = AdversarialEngine.process_and_validate(test_db, patient, req)
    assert status == "DUPLICATE_SUPPRESSED"
    assert "DUPLICATE_EVENT_DETECTED" in tags

def test_corrupted_timestamp_quarantine(test_db):
    """Verifies that unparseable garbage timestamps are routed to quarantine."""
    pseudo = generate_pseudonym("TEST-MRN-003")
    patient = Patient(pseudonym_id=pseudo, cohort="Oncology")
    test_db.add(patient)
    test_db.commit()

    req = EventIngestRequest(
        patient_identifier="TEST-MRN-003",
        event_type="LAB_RESULT",
        source_system="PACS",
        timestamp="2026-INVALID-NULL-CORRUPTED_HEX"
    )

    status, _, tags, reason = AdversarialEngine.process_and_validate(test_db, patient, req)
    assert status == "QUARANTINED"
    assert "CORRUPTED_TIMESTAMP" in tags
    assert "Corrupted" in reason

def test_missing_triage_note_imputation(test_db):
    """Verifies that missing clinical triage acuity notes are imputed with cohort defaults."""
    pseudo = generate_pseudonym("TEST-MRN-004")
    patient = Patient(pseudonym_id=pseudo, cohort="Emergency")
    test_db.add(patient)
    test_db.commit()

    req = EventIngestRequest(
        patient_identifier="TEST-MRN-004",
        event_type="TRIAGE",
        source_system="EHR",
        timestamp="2026-09-20T14:00:00",
        metadata={}
    )

    status, ts, tags, _ = AdversarialEngine.process_and_validate(test_db, patient, req)
    assert "IMPUTED_MISSING_NOTE" in tags
    assert req.metadata["acuity_score"] == 3
