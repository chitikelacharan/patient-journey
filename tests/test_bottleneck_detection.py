import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.orm_models import Patient, ClinicalEvent
from backend.app.core.bottleneck_detector import BottleneckDetector
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

def test_bottleneck_detection_ranking(test_db):
    # Inject a massive deliberate delay between PRIOR_AUTH_SUBMITTED and PRIOR_AUTH_DECISION
    for p_idx in range(6):
        patient = Patient(
            pseudonym_id=generate_pseudonym(f"TEST-BN-{p_idx}"),
            cohort="Oncology",
            total_duration_hours=48.0
        )
        test_db.add(patient)
        test_db.commit()

        t0 = datetime(2026, 9, 20, 8, 0, 0)
        e1 = ClinicalEvent(patient_id=patient.id, event_type="PRIOR_AUTH_SUBMITTED", source_system="PAYER", timestamp=t0, original_timestamp=t0.isoformat(), status="ACCEPTED")
        # 36-hour delay! SLA is 6 hours
        t1 = t0 + timedelta(hours=36)
        e2 = ClinicalEvent(patient_id=patient.id, event_type="PRIOR_AUTH_DECISION", source_system="PAYER", timestamp=t1, original_timestamp=t1.isoformat(), status="ACCEPTED")
        test_db.add_all([e1, e2])
    test_db.commit()

    choke_points = BottleneckDetector.get_top_bottlenecks(test_db, limit=3)
    assert len(choke_points) > 0
    top = choke_points[0]
    assert top.transition == "PRIOR_AUTH_SUBMITTED->PRIOR_AUTH_DECISION"
    assert top.bci_score >= 2.0
    assert top.severity in ["MODERATE", "CRITICAL"]
    assert top.estimated_annual_cost_delay > 0
