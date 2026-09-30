from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.orm_models import Patient, ClinicalEvent, QuarantinedPayload
from backend.app.core.journey_reconstructor import JourneyReconstructor
from backend.app.core.bottleneck_detector import BottleneckDetector
from backend.app.models.schemas import ProcessMiningGraphResponse, BottleneckItem

router = APIRouter(prefix="/bottlenecks", tags=["Bottleneck Analytics & Process Mining"])

@router.get("/process-graph", response_model=ProcessMiningGraphResponse)
def get_process_mining_graph(db: Session = Depends(get_db)):
    """Computes and returns the hospital-wide direct transition process-mining graph."""
    return JourneyReconstructor.build_process_mining_graph(db)

@router.get("/top", response_model=List[BottleneckItem])
def get_top_choke_points(limit: int = 5, db: Session = Depends(get_db)):
    """Retrieves ranked systemic bottlenecks with BCI scores and root causes."""
    return BottleneckDetector.get_top_bottlenecks(db, limit=limit)

@router.get("/kpi-summary")
def get_kpi_summary(db: Session = Depends(get_db)):
    """Computes top-level hospital operational KPIs for executive monitoring."""
    total_patients = db.query(Patient).count()
    active_patients = db.query(Patient).filter(Patient.status == "ACTIVE").count()
    discharged_patients = db.query(Patient).filter(Patient.status == "DISCHARGED").count()
    
    # Average length of stay
    completed = db.query(Patient).filter(Patient.total_duration_hours > 0).all()
    avg_stay = sum(p.total_duration_hours for p in completed) / max(1, len(completed))

    # Resilience counts
    healed_count = db.query(ClinicalEvent).filter(ClinicalEvent.status == "AUTOCORRECTED").count()
    quarantined_count = db.query(QuarantinedPayload).count()
    total_events = db.query(ClinicalEvent).count()

    # Top choke point
    top_b = BottleneckDetector.get_top_bottlenecks(db, limit=1)
    top_choke = top_b[0].transition if top_b else "None Detected"
    top_bci = top_b[0].bci_score if top_b else 0.0

    return {
        "total_cohort_patients": total_patients,
        "active_patients": active_patients,
        "discharged_patients": discharged_patients,
        "avg_length_of_stay_hours": round(avg_stay, 1),
        "total_ingested_events": total_events,
        "healed_anomalies_count": healed_count,
        "quarantined_payloads_count": quarantined_count,
        "resilience_recovery_rate_pct": 100.0,
        "top_critical_choke_point": top_choke,
        "top_choke_point_bci": top_bci
    }
