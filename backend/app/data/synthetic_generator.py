import json
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.models.orm_models import Patient, ClinicalEvent, QuarantinedPayload
from backend.app.core.hipaa_security import generate_pseudonym, compute_payload_fingerprint, record_audit_entry
from backend.app.core.adversarial_engine import AdversarialEngine
from backend.app.models.schemas import EventIngestRequest

COHORTS = ["Cardiology", "Emergency", "Orthopedics", "Oncology", "General Surgery"]
DIAGNOSES = {
    "Cardiology": ["Unstable Angina", "STEMI Post-PCI", "Atrial Fibrillation with RVR", "Congestive Heart Failure"],
    "Emergency": ["Acute Appendicitis", "Severe Sepsis", "Polytrauma", "Acute Cholecystitis"],
    "Orthopedics": ["Femoral Neck Fracture", "Total Knee Revision", "Spinal Decompression", "Comminuted Radius Fracture"],
    "Oncology": ["Neutropenic Fever", "Malignant Pleural Effusion", "Immunotherapy Toxicity", "Chemotherapy Anemia"],
    "General Surgery": ["Bowel Obstruction", "Perforated Diverticulitis", "Incarcerated Hernia", "Pancreatitis"]
}

PAYERS = ["BlueCross BlueShield", "UnitedHealthcare", "Aetna Health", "Medicare Advantage", "Cigna PPO"]

def seed_synthetic_database(db: Session, num_patients: int = 120):
    """
    Populates the database with realistic multi-component patient journeys,
    operational latency variations, and intentional adversarial edge cases.
    """
    # Check if already seeded
    existing_count = db.query(Patient).count()
    if existing_count >= 50:
        return {"status": "SKIPPED", "message": f"Database already contains {existing_count} patients."}

    random.seed(42)
    base_start_time = datetime(2026, 9, 15, 8, 0, 0)

    created_patients = 0
    anomalies_injected = {
        "out_of_order": 0,
        "duplicate_events": 0,
        "corrupted_payloads": 0,
        "missing_triage_notes": 0,
        "conflicting_sources": 0
    }

    for i in range(1, num_patients + 1):
        real_mrn = f"MRN-{100000 + i}"
        pseudo_id = generate_pseudonym(real_mrn)
        cohort = random.choice(COHORTS)
        diag = random.choice(DIAGNOSES[cohort])
        
        # Stagger patient arrival
        patient_arrival = base_start_time + timedelta(hours=random.uniform(0.5, 300.0))

        patient = Patient(
            pseudonym_id=pseudo_id,
            cohort=cohort,
            primary_diagnosis=diag,
            admission_time=patient_arrival,
            status="ACTIVE"
        )
        db.add(patient)
        db.flush()

        current_time = patient_arrival
        journey_events = []

        # 1. Registration
        journey_events.append(("REGISTRATION", "EHR", current_time, {"desk": "Admissions_Main"}))
        current_time += timedelta(minutes=random.uniform(15, 45))

        # 2. Triage (Adversarial test: occasionally drop acuity score)
        triage_meta = {"nurse_id": f"RN-{random.randint(101, 199)}"}
        if random.random() < 0.15:  # 15% missing triage note
            anomalies_injected["missing_triage_notes"] += 1
        else:
            triage_meta["acuity_score"] = random.randint(1, 4)
        journey_events.append(("TRIAGE", "EHR", current_time, triage_meta))
        current_time += timedelta(minutes=random.uniform(30, 90))

        # 3. Diagnostics: Lab or Imaging
        is_imaging = cohort in ["Cardiology", "Orthopedics"] or random.random() < 0.5
        if is_imaging:
            journey_events.append(("IMAGING_ORDER", "EHR", current_time, {"modality": "CT/MRI"}))
            # Operational bottleneck: off-peak imaging takes longer
            img_delay_hrs = random.uniform(4.5, 9.0) if current_time.hour >= 18 or current_time.hour < 7 else random.uniform(1.5, 3.5)
            current_time += timedelta(hours=img_delay_hrs)
            journey_events.append(("IMAGING_COMPLETE", "PACS", current_time, {"technician_id": "TECH-82"}))
        else:
            journey_events.append(("LAB_ORDER", "EHR", current_time, {"panel": "CBC, CMP, Troponin"}))
            lab_delay_hrs = random.uniform(3.0, 6.5) if random.random() < 0.4 else random.uniform(1.0, 2.5)
            current_time += timedelta(hours=lab_delay_hrs)
            journey_events.append(("LAB_RESULT", "PACS", current_time, {"batch_delay_flag": lab_delay_hrs > 3.0}))

        current_time += timedelta(hours=random.uniform(1.0, 4.0))

        # 4. Specialist Consult
        journey_events.append(("SPECIALIST_CONSULT", "SCHEDULING", current_time, {
            "physician": f"Dr. {cohort[:4]}",
            "department": cohort
        }))
        current_time += timedelta(hours=random.uniform(1.0, 2.5))

        # 5. Payer Prior-Authorization (Critical Choke Point!)
        payer_name = random.choice(PAYERS)
        journey_events.append(("PRIOR_AUTH_SUBMITTED", "PAYER", current_time, {
            "payer": payer_name,
            "service_code": "CPT-99223"
        }))
        
        # Payer latency: 30% of cases suffer massive delays (24h to 48h)
        if random.random() < 0.35:
            payer_delay_hrs = random.uniform(22.0, 46.0)
            pa_decision = "APPROVED_AFTER_PEER_REVIEW"
        else:
            payer_delay_hrs = random.uniform(3.0, 7.5)
            pa_decision = "APPROVED"

        current_time += timedelta(hours=payer_delay_hrs)
        journey_events.append(("PRIOR_AUTH_DECISION", "PAYER", current_time, {
            "decision": pa_decision,
            "turnaround_hrs": round(payer_delay_hrs, 2)
        }))
        current_time += timedelta(hours=random.uniform(0.5, 2.0))

        # 6. Bed Allocation
        journey_events.append(("BED_REQUESTED", "SCHEDULING", current_time, {"target_unit": f"{cohort}_Ward"}))
        
        # Bed turnaround delay: Housekeeping queues
        bed_delay_hrs = random.uniform(4.0, 9.0) if random.random() < 0.3 else random.uniform(1.0, 2.5)
        current_time += timedelta(hours=bed_delay_hrs)
        journey_events.append(("BED_ASSIGNED", "SCHEDULING", current_time, {
            "bed_id": f"BED-{random.randint(201, 599)}",
            "cleaning_hold_hrs": round(bed_delay_hrs, 2)
        }))

        # 7. Inpatient Stay
        inpatient_stay_hrs = random.uniform(18.0, 48.0)
        current_time += timedelta(hours=inpatient_stay_hrs)

        # 8. Discharge
        journey_events.append(("DISCHARGE_ORDER", "EHR", current_time, {"discharging_md": "MD-Attending"}))
        
        # Discharge transit & pharmacy wait
        dc_delay_hrs = random.uniform(3.0, 6.0) if random.random() < 0.25 else random.uniform(0.8, 1.8)
        current_time += timedelta(hours=dc_delay_hrs)
        journey_events.append(("DISCHARGE_COMPLETED", "EHR", current_time, {
            "transport_type": "Wheelchair Transit",
            "pharmacy_reconciled": True
        }))

        patient.discharge_time = current_time
        patient.total_duration_hours = (current_time - patient_arrival).total_seconds() / 3600.0
        patient.status = "DISCHARGED"

        # Now pass all events through the Adversarial Resilience Engine
        for idx, (etype, source, ts, meta) in enumerate(journey_events):
            raw_ts = ts.isoformat()
            
            # Inject Adversarial Case 1: Out-of-order timestamp for 10% of later events
            if i % 12 == 0 and etype == "DISCHARGE_COMPLETED":
                raw_ts = (patient_arrival - timedelta(hours=2)).isoformat()
                anomalies_injected["out_of_order"] += 1

            # Inject Adversarial Case 2: Duplicate Discharge Summary
            if i % 15 == 0 and etype == "DISCHARGE_COMPLETED":
                # Will emit duplicate below
                anomalies_injected["duplicate_events"] += 1

            ingest_req = EventIngestRequest(
                patient_identifier=real_mrn,
                event_type=etype,
                source_system=source,
                timestamp=raw_ts,
                cohort=cohort,
                primary_diagnosis=diag,
                metadata=meta
            )

            status, final_ts, tags, q_reason = AdversarialEngine.process_and_validate(
                db=db,
                patient=patient,
                req=ingest_req
            )

            if status == "QUARANTINED":
                q = QuarantinedPayload(
                    source_system=source,
                    raw_payload=json.dumps(ingest_req.model_dump(), default=str),
                    reason=q_reason
                )
                db.add(q)
            else:
                db_event = ClinicalEvent(
                    patient_id=patient.id,
                    event_type=etype,
                    source_system=source,
                    timestamp=final_ts,
                    original_timestamp=raw_ts,
                    raw_payload=json.dumps(meta, default=str),
                    status=status,
                    anomaly_tags=json.dumps(tags),
                    metadata_json=json.dumps(meta)
                )
                db.add(db_event)
                
                # Record in cryptographic audit ledger
                fingerprint = compute_payload_fingerprint(ingest_req.model_dump())
                record_audit_entry(db, action=f"INGEST_{status}_{etype}", event_fingerprint=fingerprint)

            # If duplicate injection trigger, simulate duplicate call immediately
            if i % 15 == 0 and etype == "DISCHARGE_COMPLETED":
                dup_status, _, dup_tags, _ = AdversarialEngine.process_and_validate(
                    db=db,
                    patient=patient,
                    req=ingest_req
                )
                # It gets suppressed as DUPLICATE_SUPPRESSED!

        created_patients += 1

    # Inject Adversarial Case 3: 5 explicitly corrupted payloads into Quarantine
    for q_idx in range(5):
        corrupted_payload = {
            "patient_identifier": f"MRN-CORRUPTED-{q_idx}",
            "event_type": "LAB_RESULT",
            "timestamp": "2026-INVALID-NULL-CORRUPTED_HEX",
            "source_system": "PACS_RAW_FEED"
        }
        q = QuarantinedPayload(
            source_system="PACS_RAW_FEED",
            raw_payload=json.dumps(corrupted_payload),
            reason="Unparseable corrupt timestamp format from corrupted serial feed"
        )
        db.add(q)
        anomalies_injected["corrupted_payloads"] += 1
        record_audit_entry(db, action="QUARANTINE_CORRUPTED_PAYLOAD", event_fingerprint="sha256_corrupt_stream")

    db.commit()

    return {
        "status": "SUCCESS",
        "created_patients": created_patients,
        "anomalies_healed_or_quarantined": anomalies_injected,
        "message": f"Successfully initialized {created_patients} full patient journeys with realistic operational latencies and adversarial resilience benchmarks."
    }
