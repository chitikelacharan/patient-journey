import numpy as np
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.orm_models import Patient, ClinicalEvent
from backend.app.models.schemas import SimulationRequest, SimulationResponse

class WhatIfSimulator:
    """
    Counterfactual Discrete-Event Simulation Engine.
    Simulates operational interventions and quantifies projected reductions in patient wait times
    and hospital bed-hours saved.
    """

    @classmethod
    def simulate(cls, db: Session, req: SimulationRequest) -> SimulationResponse:
        patients = db.query(Patient).all()
        if not patients:
            return SimulationResponse(
                baseline_avg_duration_hours=42.0,
                projected_avg_duration_hours=42.0,
                hours_saved_per_patient=0.0,
                total_bed_hours_recovered=0.0,
                wait_time_reduction_pct=0.0,
                annual_cost_savings_estimate=0.0,
                stage_breakdown={}
            )

        pa_factor = 1.0 - (req.prior_auth_automation_pct / 100.0)
        diag_factor = 1.0 - (req.diagnostic_batch_speedup_pct / 100.0)
        dc_factor = 1.0 - (req.discharge_transport_speedup_pct / 100.0)

        baseline_durations = []
        projected_durations = []

        stage_deltas = {
            "Prior-Authorization": {"baseline": 0.0, "projected": 0.0},
            "Diagnostics & Labs": {"baseline": 0.0, "projected": 0.0},
            "Discharge & Transit": {"baseline": 0.0, "projected": 0.0},
            "Inpatient Stay": {"baseline": 0.0, "projected": 0.0}
        }

        total_pts = len(patients)

        for p in patients:
            events = db.query(ClinicalEvent).filter(
                ClinicalEvent.patient_id == p.id,
                ClinicalEvent.status.in_(["ACCEPTED", "AUTOCORRECTED"])
            ).order_by(ClinicalEvent.timestamp.asc()).all()

            if len(events) < 2:
                baseline_durations.append(p.total_duration_hours)
                projected_durations.append(p.total_duration_hours)
                continue

            sim_patient_total = 0.0

            for i in range(len(events) - 1):
                u = events[i].event_type
                v = events[i+1].event_type
                actual_delta = max(0.1, (events[i+1].timestamp - events[i].timestamp).total_seconds() / 3600.0)

                # Apply counterfactual multipliers
                if "PRIOR_AUTH" in u and "PRIOR_AUTH" in v:
                    sim_delta = actual_delta * pa_factor
                    stage_deltas["Prior-Authorization"]["baseline"] += actual_delta
                    stage_deltas["Prior-Authorization"]["projected"] += sim_delta
                elif ("LAB" in u or "IMAGING" in u) and ("RESULT" in v or "COMPLETE" in v):
                    sim_delta = actual_delta * diag_factor
                    stage_deltas["Diagnostics & Labs"]["baseline"] += actual_delta
                    stage_deltas["Diagnostics & Labs"]["projected"] += sim_delta
                elif "DISCHARGE_ORDER" in u and "DISCHARGE_COMPLETED" in v:
                    sim_delta = actual_delta * dc_factor
                    stage_deltas["Discharge & Transit"]["baseline"] += actual_delta
                    stage_deltas["Discharge & Transit"]["projected"] += sim_delta
                else:
                    sim_delta = actual_delta
                    stage_deltas["Inpatient Stay"]["baseline"] += actual_delta
                    stage_deltas["Inpatient Stay"]["projected"] += sim_delta

                sim_patient_total += sim_delta

            baseline_durations.append(p.total_duration_hours)
            projected_durations.append(sim_patient_total)

        base_avg = float(np.mean(baseline_durations)) if baseline_durations else 42.5
        proj_avg = float(np.mean(projected_durations)) if projected_durations else 34.0
        saved_per_pt = max(0.0, base_avg - proj_avg)
        total_recovered = saved_per_pt * total_pts
        pct_reduced = (saved_per_pt / base_avg * 100.0) if base_avg > 0 else 0.0

        # Estimated annual savings: 1,500 annual admissions * saved_per_pt * $75/hr
        annual_savings = round(1500 * saved_per_pt * 75.0, 2)

        # Average stage metrics
        breakdown_avg = {}
        for stage, data in stage_deltas.items():
            breakdown_avg[stage] = {
                "baseline_avg_hours": round(data["baseline"] / max(1, total_pts), 2),
                "projected_avg_hours": round(data["projected"] / max(1, total_pts), 2),
                "reduction_hours": round((data["baseline"] - data["projected"]) / max(1, total_pts), 2)
            }

        return SimulationResponse(
            baseline_avg_duration_hours=round(base_avg, 2),
            projected_avg_duration_hours=round(proj_avg, 2),
            hours_saved_per_patient=round(saved_per_pt, 2),
            total_bed_hours_recovered=round(total_recovered, 2),
            wait_time_reduction_pct=round(pct_reduced, 1),
            annual_cost_savings_estimate=annual_savings,
            stage_breakdown=breakdown_avg
        )
