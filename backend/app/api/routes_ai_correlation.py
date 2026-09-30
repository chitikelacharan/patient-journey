from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.core.root_cause_ai import RootCauseAI
from backend.app.core.what_if_simulator import WhatIfSimulator
from backend.app.models.schemas import (
    RootCauseAnalysisResponse,
    SimulationRequest,
    SimulationResponse
)

router = APIRouter(prefix="/ai", tags=["Root Cause AI & Counterfactual Simulation"])

@router.get("/root-cause", response_model=RootCauseAnalysisResponse)
def get_root_cause_analysis(db: Session = Depends(get_db)):
    """
    Executes multivariate statistical correlation across all patient journeys
    to isolate operational drivers of extended wait times.
    """
    return RootCauseAI.analyze(db)

@router.post("/simulate", response_model=SimulationResponse)
def run_what_if_simulation(req: SimulationRequest, db: Session = Depends(get_db)):
    """
    Runs counterfactual discrete-event simulation to project hours saved,
    capacity recovery, and financial gains from specific administrative interventions.
    """
    return WhatIfSimulator.simulate(db, req)
