from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.orm_models import Patient, ClinicalEvent
from backend.app.core.journey_reconstructor import JourneyReconstructor

router = APIRouter(prefix="/journeys", tags=["Patient Journeys & Chronological Traces"])

@router.get("/patients")
def list_patients(
    cohort: Optional[str] = None,
    status: Optional[str] = None,
    has_healed: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Lists patients with optional cohort filtering, anomaly tracking, and search."""
    query = db.query(Patient)
    if cohort:
        query = query.filter(Patient.cohort == cohort)
    if status:
        query = query.filter(Patient.status == status)
    if search:
        query = query.filter(
            (Patient.pseudonym_id.ilike(f"%{search}%")) | 
            (Patient.primary_diagnosis.ilike(f"%{search}%"))
        )

    total = query.count()
    patients = query.order_by(Patient.id.desc()).offset(offset).limit(limit).all()

    results = []
    for p in patients:
        # Check if patient has any healed events
        healed_count = db.query(ClinicalEvent).filter(
            ClinicalEvent.patient_id == p.id,
            ClinicalEvent.status == "AUTOCORRECTED"
        ).count()

        if has_healed is not None:
            if has_healed and healed_count == 0:
                continue
            if not has_healed and healed_count > 0:
                continue

        event_count = db.query(ClinicalEvent).filter(ClinicalEvent.patient_id == p.id).count()

        results.append({
            "id": p.id,
            "pseudonym_id": p.pseudonym_id,
            "cohort": p.cohort,
            "primary_diagnosis": p.primary_diagnosis,
            "status": p.status,
            "total_duration_hours": round(p.total_duration_hours, 1),
            "event_count": event_count,
            "healed_anomalies_count": healed_count
        })

    return {
        "total": total,
        "returned": len(results),
        "patients": results
    }

@router.get("/{patient_id}")
def get_patient_journey(patient_id: int, db: Session = Depends(get_db)):
    """Reconstructs the detailed end-to-end chronological journey of a single patient."""
    timeline = JourneyReconstructor.get_patient_timeline(db, patient_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Patient journey not found.")
    return timeline
