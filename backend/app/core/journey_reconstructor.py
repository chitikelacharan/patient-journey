import json
import numpy as np
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models.orm_models import Patient, ClinicalEvent
from backend.app.models.schemas import GraphNode, GraphEdge, ProcessMiningGraphResponse

class JourneyReconstructor:
    """
    Process Mining and Patient Journey Reconstruction Engine.
    Converts fragmented, multi-modal event logs into normalized chronological traces,
    directed process-mining graphs, and state-dwell metrics.
    """

    STAGE_CATEGORIES = {
        "REGISTRATION": "Admissions",
        "TRIAGE": "Admissions",
        "LAB_ORDER": "Diagnostics",
        "LAB_RESULT": "Diagnostics",
        "IMAGING_ORDER": "Diagnostics",
        "IMAGING_COMPLETE": "Diagnostics",
        "SPECIALIST_CONSULT": "Consultation",
        "PRIOR_AUTH_SUBMITTED": "Payer & Finance",
        "PRIOR_AUTH_DECISION": "Payer & Finance",
        "BED_REQUESTED": "Inpatient Ops",
        "BED_ASSIGNED": "Inpatient Ops",
        "DISCHARGE_ORDER": "Discharge & Transition",
        "DISCHARGE_COMPLETED": "Discharge & Transition"
    }

    @classmethod
    def get_patient_timeline(cls, db: Session, patient_id: int) -> Dict[str, Any]:
        """Reconstructs the strictly ordered chronological trace for a single patient."""
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return None

        events = db.query(ClinicalEvent).filter(
            ClinicalEvent.patient_id == patient_id,
            ClinicalEvent.status.in_(["ACCEPTED", "AUTOCORRECTED"])
        ).order_by(ClinicalEvent.timestamp.asc()).all()

        timeline_events = []
        prev_ts = None
        bottlenecks_encountered = []
        has_healed = False

        for evt in events:
            duration_from_prev = None
            if prev_ts:
                duration_from_prev = round((evt.timestamp - prev_ts).total_seconds() / 3600.0, 2)
            prev_ts = evt.timestamp

            try:
                anomaly_list = json.loads(evt.anomaly_tags) if evt.anomaly_tags else []
            except Exception:
                anomaly_list = []

            if evt.status == "AUTOCORRECTED" or "CAUSAL_DAG_HEALED" in anomaly_list:
                has_healed = True

            try:
                meta = json.loads(evt.metadata_json) if evt.metadata_json else {}
            except Exception:
                meta = {}

            # Check if this step exceeded SLA
            if duration_from_prev is not None and len(timeline_events) > 0:
                prev_type = timeline_events[-1]["event_type"]
                transition_key = f"{prev_type}->{evt.event_type}"
                sla = settings.SLA_BENCHMARKS.get(transition_key, 4.0)
                if duration_from_prev > (sla * 1.5):
                    bottlenecks_encountered.append(f"{transition_key} ({duration_from_prev}h vs SLA {sla}h)")

            timeline_events.append({
                "id": evt.id,
                "event_type": evt.event_type,
                "source_system": evt.source_system,
                "timestamp": evt.timestamp.isoformat(),
                "original_timestamp": evt.original_timestamp,
                "status": evt.status,
                "anomaly_tags": anomaly_list,
                "duration_from_previous_hours": duration_from_prev,
                "metadata": meta
            })

        return {
            "patient_id": patient.id,
            "pseudonym_id": patient.pseudonym_id,
            "cohort": patient.cohort,
            "primary_diagnosis": patient.primary_diagnosis,
            "status": patient.status,
            "total_duration_hours": round(patient.total_duration_hours, 2),
            "events": timeline_events,
            "bottlenecks_encountered": bottlenecks_encountered,
            "has_healed_anomalies": has_healed
        }

    @classmethod
    def build_process_mining_graph(cls, db: Session) -> ProcessMiningGraphResponse:
        """
        Constructs the hospital-wide process-mining transition graph across all active & completed journeys.
        Calculates edge transitions, median / P90 / P99 dwell durations, and BCI scores.
        """
        patients = db.query(Patient).all()
        transition_durations: Dict[Tuple[str, str], List[float]] = {}
        node_dwells: Dict[str, List[float]] = {}
        node_counts: Dict[str, int] = {}

        total_durations = []

        for p in patients:
            if p.total_duration_hours > 0:
                total_durations.append(p.total_duration_hours)

            events = db.query(ClinicalEvent).filter(
                ClinicalEvent.patient_id == p.id,
                ClinicalEvent.status.in_(["ACCEPTED", "AUTOCORRECTED"])
            ).order_by(ClinicalEvent.timestamp.asc()).all()

            for i in range(len(events) - 1):
                u = events[i].event_type
                v = events[i+1].event_type
                delta_hours = max(0.05, (events[i+1].timestamp - events[i].timestamp).total_seconds() / 3600.0)
                
                key = (u, v)
                if key not in transition_durations:
                    transition_durations[key] = []
                transition_durations[key].append(delta_hours)

                # Dwell time recording for node u
                if u not in node_dwells:
                    node_dwells[u] = []
                    node_counts[u] = 0
                node_dwells[u].append(delta_hours)
                node_counts[u] += 1

            if events:
                last_node = events[-1].event_type
                node_counts[last_node] = node_counts.get(last_node, 0) + 1

        # Build Graph Nodes
        all_nodes_set = set()
        for u, v in transition_durations.keys():
            all_nodes_set.add(u)
            all_nodes_set.add(v)

        nodes_list: List[GraphNode] = []
        for n in sorted(list(all_nodes_set)):
            dwells = node_dwells.get(n, [0.0])
            avg_dwell = float(np.mean(dwells)) if dwells else 0.0
            nodes_list.append(GraphNode(
                id=n,
                label=n.replace("_", " ").title(),
                stage_category=cls.STAGE_CATEGORIES.get(n, "General"),
                avg_dwell_hours=round(avg_dwell, 2),
                queued_patients_count=node_counts.get(n, 0)
            ))

        # Build Graph Edges with Statistical Percentiles & BCI
        edges_list: List[GraphEdge] = []
        critical_choke_count = 0

        for (u, v), durations in transition_durations.items():
            arr = np.array(durations)
            p50 = float(np.percentile(arr, 50))
            p90 = float(np.percentile(arr, 90))
            p99 = float(np.percentile(arr, 99))
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr)) if len(arr) > 1 else 0.0

            transition_key = f"{u}->{v}"
            sla = settings.SLA_BENCHMARKS.get(transition_key, 3.0)
            
            # Bottleneck Criticality Index (BCI) Formula:
            # BCI = 0.5 * (P90 / SLA) + 0.3 * (std / mean) + 0.2 * (count_queued / total_patients)
            total_pts = max(1, len(patients))
            cv = (std_val / mean_val) if mean_val > 0 else 0.0
            bci = 0.5 * (p90 / sla) + 0.3 * min(2.0, cv) + 0.2 * (len(arr) / total_pts)
            bci = round(bci, 2)

            if bci >= 2.5:
                severity = "CRITICAL"
                is_bottleneck = True
                critical_choke_count += 1
            elif bci >= 1.5:
                severity = "MODERATE"
                is_bottleneck = True
            else:
                severity = "NORMAL"
                is_bottleneck = False

            edges_list.append(GraphEdge(
                source=u,
                target=v,
                patient_count=len(arr),
                median_duration_hours=round(p50, 2),
                p90_duration_hours=round(p90, 2),
                p99_duration_hours=round(p99, 2),
                sla_target_hours=round(sla, 2),
                bci_score=bci,
                is_bottleneck=is_bottleneck,
                bottleneck_severity=severity
            ))

        overall_avg = float(np.mean(total_durations)) if total_durations else 36.5

        return ProcessMiningGraphResponse(
            nodes=nodes_list,
            edges=edges_list,
            total_active_patients=len(patients),
            overall_avg_duration_hours=round(overall_avg, 2),
            critical_choke_points_count=critical_choke_count
        )
