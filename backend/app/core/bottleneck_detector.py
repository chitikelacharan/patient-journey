from typing import List
from sqlalchemy.orm import Session
from backend.app.core.journey_reconstructor import JourneyReconstructor
from backend.app.models.schemas import BottleneckItem

class BottleneckDetector:
    """
    Evaluates systemic healthcare operational choke points,
    computes Bottleneck Criticality Indices (BCI), and projects financial impact.
    """

    CHOKE_DRIVERS = {
        "PRIOR_AUTH_SUBMITTED->PRIOR_AUTH_DECISION": "Payer Pre-Authorization Backlog (Manual payer review & redundant clinical documentation requests)",
        "BED_REQUESTED->BED_ASSIGNED": "Inpatient Bed Turnaround Delay (Housekeeping disinfection queues and nurse staffing shift handover)",
        "LAB_ORDER->LAB_RESULT": "Laboratory Batch Processing Delay (Off-peak centrifuge batching and pathology consult queuing)",
        "IMAGING_ORDER->IMAGING_COMPLETE": "Radiology PACS Bottleneck (Evening MRI/CT scanner capacity constraints and transport availability)",
        "DISCHARGE_ORDER->DISCHARGE_COMPLETED": "Discharge Transit & Pharmacy Hold (Prescription reconciliation and non-emergent patient transport wait)"
    }

    @classmethod
    def get_top_bottlenecks(cls, db: Session, limit: int = 5) -> List[BottleneckItem]:
        graph = JourneyReconstructor.build_process_mining_graph(db)
        
        # Sort edges by BCI score descending
        sorted_edges = sorted(graph.edges, key=lambda e: e.bci_score, reverse=True)
        
        results: List[BottleneckItem] = []
        for edge in sorted_edges:
            if not edge.is_bottleneck and len(results) >= limit:
                continue

            transition_key = f"{edge.source}->{edge.target}"
            driver = cls.CHOKE_DRIVERS.get(
                transition_key,
                f"Operational latency between {edge.source.replace('_', ' ')} and {edge.target.replace('_', ' ')}"
            )

            # Estimated financial cost: $75 per excess patient wait-hour (approx $1,800/day hospital stay cost)
            excess_hours = max(0.0, edge.median_duration_hours - edge.sla_target_hours)
            annual_cost = excess_hours * edge.patient_count * 52 * 75.0  # extrapolated annualized impact

            results.append(BottleneckItem(
                transition=transition_key,
                source_stage=edge.source,
                target_stage=edge.target,
                severity=edge.bottleneck_severity,
                bci_score=edge.bci_score,
                median_hours=edge.median_duration_hours,
                p90_hours=edge.p90_duration_hours,
                sla_target_hours=edge.sla_target_hours,
                stalled_patients_count=edge.patient_count,
                primary_choke_driver=driver,
                estimated_annual_cost_delay=round(annual_cost, 2)
            ))

            if len(results) >= limit:
                break

        return results
