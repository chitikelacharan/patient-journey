import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.orm_models import Patient, ClinicalEvent
from backend.app.core.journey_reconstructor import JourneyReconstructor
from backend.app.core.hipaa_security import generate_pseudonym

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

def test_journey_reconstruction_single_patient(test_db):
    patient = Patient(
        pseudonym_id=generate_pseudonym("TEST-MRN-501"),
        cohort="Cardiology",
        primary_diagnosis="Unstable Angina",
        status="DISCHARGED",
        total_duration_hours=26.5
    )
    test_db.add(patient)
    test_db.commit()

    base_time = datetime(2026, 9, 20, 8, 0, 0)
    stages = ["REGISTRATION", "TRIAGE", "LAB_ORDER", "LAB_RESULT", "DISCHARGE_COMPLETED"]
    
    for i, s in enumerate(stages):
        evt = ClinicalEvent(
            patient_id=patient.id,
            event_type=s,
            source_system="EHR",
            timestamp=base_time + timedelta(hours=i * 2.5),
            original_timestamp=(base_time + timedelta(hours=i * 2.5)).isoformat(),
            status="ACCEPTED"
        )
        test_db.add(evt)
    test_db.commit()

    timeline = JourneyReconstructor.get_patient_timeline(test_db, patient.id)
    assert timeline is not None
    assert timeline["pseudonym_id"] == patient.pseudonym_id
    assert len(timeline["events"]) == 5
    assert timeline["events"][0]["event_type"] == "REGISTRATION"
    assert timeline["events"][-1]["event_type"] == "DISCHARGE_COMPLETED"

def test_process_mining_graph_generation(test_db):
    # Add multiple patient traces
    for p_idx in range(5):
        patient = Patient(
            pseudonym_id=generate_pseudonym(f"TEST-MRN-60{p_idx}"),
            cohort="General",
            total_duration_hours=10.0
        )
        test_db.add(patient)
        test_db.commit()

        base_time = datetime(2026, 9, 20, 8, 0, 0)
        stages = ["REGISTRATION", "TRIAGE", "LAB_ORDER", "LAB_RESULT"]
        for i, s in enumerate(stages):
            evt = ClinicalEvent(
                patient_id=patient.id,
                event_type=s,
                source_system="EHR",
                timestamp=base_time + timedelta(hours=i * 1.5),
                original_timestamp=(base_time + timedelta(hours=i * 1.5)).isoformat(),
                status="ACCEPTED"
            )
            test_db.add(evt)
    test_db.commit()

    graph = JourneyReconstructor.build_process_mining_graph(test_db)
    assert len(graph.nodes) >= 4
    assert len(graph.edges) >= 3
    assert graph.total_active_patients == 5
