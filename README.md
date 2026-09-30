# Med-Pulse 360: Patient Journey Bottleneck Analyzer
**Problem Statement ID:** PNH1  
**Theme:** HealthTech, MedAI and Diagnostics  
**System Architecture:** Multi-Component Resilient Healthcare Analytics Platform  
**Compliance Standards:** HIPAA Title II / HITECH (§ 164.312) | Safe Harbor De-identification

---

## Executive Summary

Healthcare networks frequently suffer from fragmented data silos across Electronic Health Records (EHR), Diagnostic Information Systems (PACS/LIS), Hospital Scheduling, and Payer Pre-Authorization Feeds. These silos cause massive delays in patient care, inflated bed costs, and administrative burnout.

**Med-Pulse 360** is an enterprise-grade healthcare operations intelligence platform that:
1. **Normalizes & Ingests** fragmented multi-modal streams (EHR, PACS, Payer EDI 278, Scheduling).
2. **Autonomously Pinpoints Critical Choke Points** using statistical process mining and a mathematically rigorous **Bottleneck Criticality Index ($BCI$)**.
3. **Isolates Root Causes** via AI-driven multivariate correlation (Pearson/Spearman) between operational resource constraints and extended patient stays.
4. **Guarantees Adversarial Resilience** against corrupted timestamps, out-of-order logs, duplicate discharge summaries, and missing triage notes without skewing hospital-wide analytics.
5. **Simulates Counterfactual Interventions** with an interactive What-If discrete-event simulator predicting patient hours saved, bed recovery, and cost savings.
6. **Enforces Cryptographic HIPAA Compliance** through salted HMAC de-identification and an immutable SHA-256 blockchain-style audit ledger.

---

## 4-Level Architecture & Delivery Matrix

```
+----------------------------------------------------------------------------------------------------+
|  LEVEL 1: IDEA, ARCHITECTURE & PLANNING                                                            |
|  • docs/SRS.md                     : Full IEEE 830 Software Requirements Specification              |
|  • docs/SYSTEM_ARCHITECTURE.md     : C4 Architecture, Microservices & Mathematical Formulations     |
|  • docs/DATA_FLOW_DIAGRAMS.md       : DFD Level 0, 1, 2 for Ingestion & Reconstruction Engine       |
|  • docs/TECH_STACK_AND_ROADMAP.md   : Tech Stack Rationale & 4-Level Milestones Gantt Chart          |
|  • docs/UI_WIREFRAMES.md            : Visual Design System, Palettes & Wireframe Layouts             |
+----------------------------------------------------------------------------------------------------+
|  LEVEL 2: CORE FUNCTIONALITY (MVP)                                                                 |
|  • Multi-Source Ingestion Gateway   : Normalized endpoints for EHR, PACS, Payer, and Scheduling     |
|  • Database Schemas (SQLAlchemy)    : Patients, Normalized Events, Quarantines, Cryptographic Audits |
|  • Process Mining Engine            : Direct Transition Graph, P50/P90/P99 dwell times, SLAs        |
|  • Interactive Visual Dashboard     : Real-time Executive Radar, Top Choke Points, Alerts Feed     |
+----------------------------------------------------------------------------------------------------+
|  LEVEL 3: INTELLIGENCE, SECURITY & RESILIENCE                                                      |
|  • Adversarial Resilience Engine    : Causal DAG auto-heals out-of-order timestamps; deduplicates    |
|  • Root Cause Correlation AI        : Multivariate Pearson/Spearman matrix with prescriptive actions |
|  • What-If Counterfactual Simulator : Live queueing simulation with sliders & cost recovery meters  |
|  • HIPAA Cryptographic Audit Ledger : Chained SHA-256 blocks with mathematical proof verification   |
|  • Adversarial Live Test Sandbox    : Real-time injection harness for judges and evaluators          |
+----------------------------------------------------------------------------------------------------+
|  LEVEL 4: SCALABILITY, RELIABILITY & ENTERPRISE READINESS                                          |
|  • Multi-Stage Docker Packaging     : Production container with curl health probes                  |
|  • Container Orchestration          : docker-compose.yml with persistent volume mounts              |
|  • Observability & Monitoring       : Prometheus /metrics scrape endpoint + /health probe           |
|  • Automated CI/CD Pipeline         : GitHub Actions (.github/workflows/ci.yml) with matrix testing |
|  • Comprehensive Automated Tests    : 100% passing pytest suite across all subsystems                |
+----------------------------------------------------------------------------------------------------+
```

---

## Key Mathematical Foundations

### 1. Bottleneck Criticality Index ($BCI$)
Unlike naive thresholding, the $BCI$ evaluates multi-dimensional operational friction:

$$BCI(u \to v) = 0.5 \cdot \left(\frac{T_{P90}(u \to v)}{T_{SLA}(u \to v)}\right) + 0.3 \cdot \min\left(2.0, \frac{\sigma(u \to v)}{\mu(u \to v)}\right) + 0.2 \cdot \left(\frac{N_{queued}(u \to v)}{N_{total}}\right)$$

- Any transition with $BCI \ge 2.5$ is flagged as **CRITICAL CHOKE POINT**.
- Transitions with $1.5 \le BCI < 2.5$ are flagged as **MODERATE DELAYS**.

### 2. Causal Directed Acyclic Graph (DAG) Healing Heuristic
When an out-of-order event $e_v$ arrives with raw timestamp $t(e_v) < t(e_u)$ where $u \prec v$:
$$\hat{t}(e_v) = \max_{p \in \text{Ancestors}(v)} \left( t(e_p) \right) + \Delta_{SLA}(u \to v)$$
The record is stored with status `AUTOCORRECTED` and tags `["OUT_OF_ORDER_TIMESTAMP", "CAUSAL_DAG_HEALED"]`, ensuring hospital length-of-stay metrics are never skewed negatively.

### 3. Cryptographic Audit Proof (SHA-256 Chaining)
$$H_i = \text{SHA256}\left(H_{i-1} \parallel \text{Seq}_i \parallel \text{Action}_i \parallel \text{Actor}_i \parallel \text{Fingerprint}_i \parallel \text{Timestamp}_i\right)$$
Guarantees that no clinical log or timestamp modification can occur undetected.

---

## Quickstart Guide

### Option 1: Direct Local Execution (Python 3.10+)

1. **Clone or Navigate to the Repository:**
   ```bash
   cd "c:\Users\Manjula C\Desktop\junior"
   ```

2. **Install Dependencies:**
   ```bash
   py -m pip install -r requirements.txt
   ```

3. **Launch the Single-Command Runner:**
   ```bash
   py run.py
   ```

4. **Access the Web Application & APIs:**
   - **Interactive UI Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
   - **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - **Prometheus Telemetry Scrape**: [http://127.0.0.1:8000/metrics](http://127.0.0.1:8000/metrics)
   - **Kubernetes Health Probe**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### Option 2: Docker & Docker Compose (Containerized)

```bash
# Build and run containerized service
docker-compose up --build -d

# Check live logs
docker-compose logs -f

# Verify health status
curl http://localhost:8000/health
```

---

## Running the Automated Test Suite

Med-Pulse 360 includes a full suite of automated unit and integration tests:

```bash
py -m pytest -v tests/
```

### Test Coverage Highlights:
- `test_out_of_order_timestamp_healing`: Verifies Causal DAG timestamp forward correction.
- `test_duplicate_event_suppression`: Verifies 1-hour window duplicate suppression.
- `test_corrupted_timestamp_quarantine`: Verifies isolation of corrupt payloads into the Quarantine Vault.
- `test_missing_triage_note_imputation`: Verifies clinical acuity score imputation.
- `test_journey_reconstruction_single_patient`: Verifies discrete step chronological ordering.
- `test_process_mining_graph_generation`: Verifies edge dwell percentiles and graph matrix.
- `test_bottleneck_detection_ranking`: Verifies BCI computation and ranking.
- `test_hipaa_audit_verification_endpoint`: Validates SHA-256 mathematical proof verification.
- `test_what_if_simulation_endpoint`: Validates counterfactual wait-time reductions.

---

## Interactive Feature Walkthrough for Judges

1. **Executive Command Center (Tab 1)**:
   - Review live KPIs: Active patients, hospital mean length of stay, critical choke point, and adversarial resilience rate.
   - Inspect the ranked bottlenecks table showing median vs. P90 wait times, SLA benchmarks, and annualized delay costs.
   - Observe live operational alerts.

2. **Process Mining Graph (Tab 2)**:
   - Interactive flow graph displaying all stages from Registration to Discharge.
   - Glowing crimson pulse rings highlight critical bottlenecks (e.g. Prior-Auth and Bed Turnaround).
   - Animated particles travel along edges at velocities proportional to stage turnaround.
   - Click any stage node (e.g. `PRIOR_AUTH_SUBMITTED` or `BED_REQUESTED`) to inspect dwell times and downstream queues.

3. **Patient Journey Traces (Tab 3)**:
   - Search patients by Pseudonym ID or filter by clinical cohort (Cardiology, Emergency, Orthopedics, Oncology).
   - Inspect the reconstructed timeline showing discrete clinical events, delay flags, and green auto-repaired badges (`[CAUSAL_DAG_HEALED]`, `[IMPUTED_MISSING_NOTE]`).

4. **Root Cause AI & What-If Simulator (Tab 4)**:
   - Inspect the AI correlation cards displaying Pearson $r$ and $p$-values linking operational variables to total delay.
   - Adjust the **Prior-Authorization Automation** slider to 60%, **Off-Peak Diagnostic Speedup** to 30%, and **Discharge Transit** to 40%.
   - Watch the counterfactual simulator instantly calculate projected patient hours saved, recovered bed-hours, and annual cost savings.

5. **Adversarial Resilience Sandbox (Tab 5)**:
   - Click **Inject** next to **Out-of-Order Timestamp**; observe the live terminal log show Causal DAG correction with zero system downtime.
   - Click **Inject** next to **Duplicate Discharge Summary**; observe 1-hour sliding fingerprint deduplication.
   - Click **Inject** next to **Corrupted Null/Hex Timestamp**; observe safe routing to the Quarantined Payloads Vault.

6. **HIPAA SHA-256 Audit Trail (Tab 6)**:
   - Review the cryptographic ledger showing chronological sequence numbers, actions, actors, and chained hashes.
   - Click **Run Cryptographic Proof Verification** to verify complete mathematical chain integrity.

---

## Production Security & Compliance
- **HIPAA Title II § 164.312(a)**: AES-256 encryption in transit and at rest.
- **HIPAA Title II § 164.312(b)**: Immutable SHA-256 hash-chained audit trails.
- **Safe Harbor Pseudonymization**: Real Patient Identifiers (MRN, SSN, Name) are never stored in plaintext; salted HMAC irreversible tokens (`PT-XXXXXX`) are utilized hospital-wide.

---

## Authors & Acknowledgments
- **Project Team**: Med-Pulse 360 Engineering Team
- **Hackathon Theme**: HealthTech, MedAI and Diagnostics (Statement ID: PNH1)
- **Year**: 2026
