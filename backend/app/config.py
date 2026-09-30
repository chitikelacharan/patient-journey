import os
from pydantic import BaseModel
from typing import Dict

class Settings(BaseModel):
    PROJECT_NAME: str = "Patient Journey Bottleneck Analyzer (PNH1)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = "sqlite:///./healthcare_analyzer.db"
    HIPAA_SALT: str = "HIPAA_SECURE_SALT_MEDPULSE_2026_X9"
    AUDIT_ENABLED: bool = True
    
    # Standard Clinical Target SLAs (in hours)
    SLA_BENCHMARKS: Dict[str, float] = {
        "REGISTRATION->TRIAGE": 0.5,
        "TRIAGE->LAB_ORDER": 1.0,
        "TRIAGE->IMAGING_ORDER": 1.5,
        "LAB_ORDER->LAB_RESULT": 2.5,
        "IMAGING_ORDER->IMAGING_COMPLETE": 3.0,
        "LAB_RESULT->SPECIALIST_CONSULT": 3.5,
        "IMAGING_COMPLETE->SPECIALIST_CONSULT": 4.0,
        "SPECIALIST_CONSULT->PRIOR_AUTH_SUBMITTED": 2.0,
        "PRIOR_AUTH_SUBMITTED->PRIOR_AUTH_DECISION": 6.0,  # Frequently breached choke point
        "PRIOR_AUTH_DECISION->BED_REQUESTED": 1.5,
        "BED_REQUESTED->BED_ASSIGNED": 3.0,               # Bed turnaround choke point
        "BED_ASSIGNED->DISCHARGE_ORDER": 24.0,
        "DISCHARGE_ORDER->DISCHARGE_COMPLETED": 2.0        # Discharge delay choke point
    }

settings = Settings()
