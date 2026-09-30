from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Ingestion Schemas
class EventIngestRequest(BaseModel):
    patient_identifier: str = Field(..., description="EHR Patient ID or MRN")
    event_type: str = Field(..., description="e.g., REGISTRATION, TRIAGE, LAB_ORDER, LAB_RESULT, PRIOR_AUTH_SUBMITTED, etc.")
    source_system: str = Field(..., description="EHR, PACS, PAYER, SCHEDULING")
    timestamp: str = Field(..., description="ISO 8601 or HL7 timestamp")
    cohort: Optional[str] = Field("General Medicine", description="Clinical department or specialty")
    primary_diagnosis: Optional[str] = Field("Unspecified", description="Clinical diagnosis code or description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Operational variables: doctor_ratio, lab_batch_latency, payer_id, etc.")

class EventIngestResponse(BaseModel):
    status: str
    patient_pseudonym: str
    event_id: Optional[int]
    anomaly_detected: bool
    anomaly_tags: List[str]
    audit_hash: str
    message: str

# Bottleneck and Process Mining Schemas
class GraphEdge(BaseModel):
    source: str
    target: str
    patient_count: int
    median_duration_hours: float
    p90_duration_hours: float
    p99_duration_hours: float
    sla_target_hours: float
    bci_score: float
    is_bottleneck: bool
    bottleneck_severity: str  # NORMAL, MODERATE, CRITICAL

class GraphNode(BaseModel):
    id: str
    label: str
    stage_category: str
    avg_dwell_hours: float
    queued_patients_count: int

class ProcessMiningGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_active_patients: int
    overall_avg_duration_hours: float
    critical_choke_points_count: int

class BottleneckItem(BaseModel):
    transition: str
    source_stage: str
    target_stage: str
    severity: str
    bci_score: float
    median_hours: float
    p90_hours: float
    sla_target_hours: float
    stalled_patients_count: int
    primary_choke_driver: str
    estimated_annual_cost_delay: float

class PatientTimelineEvent(BaseModel):
    id: int
    event_type: str
    source_system: str
    timestamp: str
    original_timestamp: str
    status: str
    anomaly_tags: List[str]
    duration_from_previous_hours: Optional[float]
    metadata: Dict[str, Any]

class PatientJourneyResponse(BaseModel):
    patient_id: int
    pseudonym_id: str
    cohort: str
    primary_diagnosis: str
    status: str
    total_duration_hours: float
    events: List[PatientTimelineEvent]
    bottlenecks_encountered: List[str]
    has_healed_anomalies: bool

# Root Cause AI and Simulation Schemas
class RootCauseFactor(BaseModel):
    factor_name: str
    category: str
    correlation_coefficient: float
    p_value: float
    impact_weight: float
    description: str
    recommended_intervention: str

class RootCauseAnalysisResponse(BaseModel):
    factors: List[RootCauseFactor]
    summary: str
    highest_impact_driver: str

class SimulationRequest(BaseModel):
    prior_auth_automation_pct: float = Field(0.0, ge=0.0, le=100.0, description="% reduction in prior-auth delay via automation")
    diagnostic_batch_speedup_pct: float = Field(0.0, ge=0.0, le=100.0, description="% reduction in lab/imaging wait times via flexible staffing")
    discharge_transport_speedup_pct: float = Field(0.0, ge=0.0, le=100.0, description="% reduction in discharge transit delay")

class SimulationResponse(BaseModel):
    baseline_avg_duration_hours: float
    projected_avg_duration_hours: float
    hours_saved_per_patient: float
    total_bed_hours_recovered: float
    wait_time_reduction_pct: float
    annual_cost_savings_estimate: float
    stage_breakdown: Dict[str, Dict[str, float]]

# Adversarial Test Request
class AdversarialTestRequest(BaseModel):
    scenario: str = Field(..., description="OUT_OF_ORDER, DUPLICATE_DISCHARGE, CORRUPTED_TIMESTAMP, MISSING_CLINICAL_NOTE, MALFORMED_PAYLOAD")
    patient_identifier: Optional[str] = "TEST-ADVERSARIAL-999"
    cohort: Optional[str] = "Emergency"
