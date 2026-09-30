# Software Requirements Specification (SRS)
## Project: Patient Journey Bottleneck Analyzer
**Statement ID**: PNH1  
**Theme**: HealthTech, MedAI and Diagnostics  
**Version**: 1.0.0  
**Compliance Tier**: HIPAA / HITECH Ready (45 CFR § 164.312)

---

### 1. Introduction

#### 1.1 Purpose
The **Patient Journey Bottleneck Analyzer** is an enterprise-grade healthcare operations intelligence platform designed to reconstruct end-to-end patient journeys across disparate, siloed hospital systems (Electronic Health Records, Scheduling, Laboratory Information Systems/PACS, and Payer Pre-Authorization Feeds). The system detects systemic operational choke points, isolates root causes with multivariate AI correlation, withstands adversarial clinical data anomalies, and provides mathematically verified counterfactual simulations to reduce patient wait times.

#### 1.2 Scope
- **Data Ingestion**: Multi-modal connector engine for EHR (HL7 v2 / FHIR R4), PACS diagnostic logs (DICOM SR), Scheduling systems, and Payer Authorization webhooks (EDI X12 278).
- **Timeline Reconstruction**: Process-mining state-transition engine that normalizes multi-source events into unified, chronologically consistent patient journeys.
- **Bottleneck Detection**: Autonomous statistical and process mining algorithms to detect choke points (P50, P90, P99 wait times, cycle latency, queue dwell time).
- **Root Cause Correlation Engine**: AI-driven multivariate correlation linking operational factors (staffing, lab batch intervals, pre-auth re-submissions, transport delays) to patient stay extensions.
- **Adversarial Resilience**: Heuristic and causal validators to automatically repair out-of-order timestamps, deduplicate clinical summaries, quarantine corrupted payloads, and handle missing triage notes without skewing analytics.
- **Simulation & What-If Planner**: Counterfactual discrete-event simulation engine projecting hospital bed-hours saved and wait time reduction percentages.
- **HIPAA Compliance**: Cryptographic audit logging with SHA-256 hash chaining, role-based access control (RBAC), and automated de-identification (Safe Harbor / Safe Pseudonymization).

---

### 2. Overall Description

#### 2.1 System Environment & Architecture
The system employs a decoupled, micro-service ready architecture consisting of:
1. **Adversarial Ingestion & Validation Gateway**: Pre-processes incoming clinical events, enforces schema validation, cleanses anomalies, and assigns cryptographic audit IDs.
2. **Process Mining & Graph Reconstructor**: Constructs directed transition graphs with edge weights representing dwell times, failure probabilities, and transition frequencies.
3. **Statistical & AI Correlation Core**: Evaluates bottleneck criticality indices ($BCI$) and calculates Pearson/Spearman correlation matrices across departmental parameters.
4. **Counterfactual Simulator**: Evaluates queueing models ($M/M/c$ and empirical distributions) to model bottleneck mitigation interventions.
5. **Interactive Executive & Clinical Command Center UI**: Real-time responsive visual dashboard featuring interactive process mining graphs, patient chronology traces, and simulation sandboxes.

#### 2.2 User Classes & Roles
- **Hospital Chief Operating Officer (COO) / Operations Director**: Monitors macro-level hospital flow, systemic bottlenecks, and financial/bed-hour impacts.
- **Clinical Department Heads (Radiology, Emergency, Inpatient, Billing)**: Investigates department-specific wait times and operational dependencies.
- **Hospital Data Auditor & Compliance Officer**: Validates data integrity, inspects HIPAA SHA-256 audit trails, and reviews adversarial quarantine logs.
- **Attending Physicians & Nurse Navigators**: Tracks individual patient journey timelines and receives real-time delay alerts.

---

### 3. Functional Requirements

| Req ID | Category | Requirement Description | Priority |
| :--- | :--- | :--- | :--- |
| **FR-01** | Ingestion | Ingest FHIR R4 Encounter, Procedure, DiagnosticReport, and ClaimResponse objects | MUST |
| **FR-02** | Ingestion | Normalize legacy HL7 timestamps and ISO 8601 strings into unified UTC epoch timelines | MUST |
| **FR-03** | Resilience | Detect and autocorrect out-of-order clinical event timestamps using causal dependency trees | MUST |
| **FR-04** | Resilience | Deduplicate duplicate discharge summaries and triage notes with rapid string hash matching | MUST |
| **FR-05** | Resilience | Quarantine malformed or adversarial payloads to an audit-logged quarantine store | MUST |
| **FR-06** | Reconstruction | Construct directed process mining graphs for all completed and active patient traces | MUST |
| **FR-07** | Analytics | Calculate P50, P90, P99 wait times, standard deviations, and Bottleneck Criticality Indices ($BCI$) | MUST |
| **FR-08** | AI Correlation | Compute multivariate correlation between operational resource metrics and total journey duration | MUST |
| **FR-09** | Simulation | Provide interactive counterfactual simulation of wait-time reduction upon bottleneck mitigation | MUST |
| **FR-10** | Security | Provide HIPAA-compliant pseudonymization and an immutable SHA-256 audit log chain | MUST |
| **FR-11** | UX/Dashboard | Interactive Web UI with Process Flow Graph, Patient Timeline Explorer, and Sandbox | MUST |
| **FR-12** | Observability | Expose `/health` and Prometheus `/metrics` endpoints for production container monitoring | SHOULD |

---

### 4. Non-Functional Requirements

- **Performance**: Ingestion latency < 50ms per clinical event; Graph reconstruction < 200ms for 1,000 active patient traces.
- **Reliability & Resilience**: 100% tolerance to out-of-order events; zero crash on malformed payloads; adversarial quarantine alerts.
- **Security & Privacy**: Zero plaintext PHI (Protected Health Information) in analytics databases; HIPAA Safe Harbor compliant de-identification; SHA-256 chained audit trail.
- **Portability**: Containerized with Docker and Docker Compose; runnable on any Linux/Windows/macOS environment with zero cloud lock-in.
