# UI Wireframes & Design System Specifications
## Project: Patient Journey Bottleneck Analyzer (PNH1)

---

### 1. Visual Hierarchy & Dashboard Layout Wireframe

```
+-------------------------------------------------------------------------------------------------------------+
|  [+] MED-PULSE 360  |  Patient Journey Bottleneck Analyzer         [Live Mode] [HIPAA Verified] [Role: Admin] |
+-------------------------------------------------------------------------------------------------------------+
|  [Tab 1: Command Center]  [Tab 2: Process Mining]  [Tab 3: Patient Traces]  [Tab 4: AI Simulator]  [Tab 5: Sandbox]  [Tab 6: Audit] |
+-------------------------------------------------------------------------------------------------------------+
|  KPI HEADER ROW:                                                                                            |
|  +--------------------+  +--------------------+  +--------------------+  +--------------------+             |
|  | Active Patients    |  | Avg Journey Length |  | Critical Choke Pt  |  | Healed Anomalies   |             |
|  |   148              |  |   42.4 hrs         |  | Prior-Auth Wait    |  |   27 Auto-Repaired |             |
|  | (+12% vs benchmark)|  | (-3.2h post-action)|  | (BCI: 3.82 - HIGH) |  | (100% Resilience)  |             |
|  +--------------------+  +--------------------+  +--------------------+  +--------------------+             |
+-------------------------------------------------------------------------------------------------------------+
|  LEFT PANEL: SYSTEMIC BOTTLENECK RADAR (60%)           | RIGHT PANEL: REAL-TIME OPERATIONAL ALERTS (40%)    |
|  +---------------------------------------------------+ | +------------------------------------------------+ |
|  | [Process Mining Transition Graph Canvas]           | | [!] CRITICAL: Prior-Authorization Latency        | |
|  |                                                   | |     Payer BlueCross delay > 36h (9 patients)     | |
|  | (Emergency Triage) --[0.8h]--> (Lab Diagnostics)   | |     Impact: +18.4 hrs hospital stay             | |
|  |         |                            |            | |                                                  | |
|  |         v                            v            | | [!] HIGH: Radiology CT Scan Batch Queue          | |
|  |  (Specialist Consult) ----> [PRIOR AUTH STALL!]   | |     Technician shortage during 18:00-22:00 shift | |
|  |                                      | (28.4h)    | |                                                  | |
|  |                                      v            | | [i] HEALED: 3 Corrupted Scheduling Feeds Fixed   | |
|  |  (Discharge Prep) <---- (Inpatient Bed Occupied)   | |     Causal DAG reordered out-of-order timestamps | |
|  +---------------------------------------------------+ | +------------------------------------------------+ |
+-------------------------------------------------------------------------------------------------------------+
|  BOTTOM SECTION: MULTIVARIATE ROOT CAUSE AI CORRELATION & WHAT-IF MITIGATION SLIDER SIMULATOR                |
|  +---------------------------------------------------+  +-------------------------------------------------+ |
|  | Root Cause Correlation Factor Matrix              |  | Interactive What-If Simulation Engine           | |
|  |  • Payer Pre-Auth Latency: r = 0.88 (p < 0.001)    |  |  Payer Automation: [========|====] 65% reduction | |
|  |  • Night Shift Diagnostic Staffing: r = 0.74       |  |  Discharge Transport: [===|========] 25% faster | |
|  |  • Inpatient Bed Turnaround: r = 0.69              |  |  ---------------------------------------------- | |
|  |                                                   |  |  PROJECTED RESULT:                              | |
|  | Recommended Intervention: Auto-escalate Auth      |  |  >> 14.8 Hours Saved per Patient                | |
|  | requests past 12hr threshold to dedicated liaison |  |  >> $420,000 Annual Bed Cost Recovery          | |
|  +---------------------------------------------------+  +-------------------------------------------------+ |
+-------------------------------------------------------------------------------------------------------------+
```

---

### 2. Design System Tokens & Aesthetics

- **Theme**: Premium MedTech Dark Glassmorphism with clinical cyan/emerald accents and high-visibility alert amber/crimson.
- **Palette Tokens**:
  - Background: `#0B0F19` (Deep Navy Obsidian)
  - Card Glass Surface: `rgba(18, 26, 47, 0.75)` with `backdrop-filter: blur(16px)` and `1px solid rgba(255, 255, 255, 0.08)`
  - Primary Accent: `#00E5FF` (Clinical Electric Cyan)
  - Success / Normal Flow: `#00E676` (Mint Emerald)
  - Warning / Moderate Bottleneck: `#FFB300` (Amber Gold)
  - Critical Choke Point: `#FF1744` (Vibrant Crimson)
  - Text Primary: `#F8FAFC`
  - Text Secondary: `#94A3B8`
- **Typography**: Google Fonts `Inter` & `Outfit` for numerical telemetry and crisp clinical readability.
- **Micro-animations**: Pulse halos on active choke points, smooth transitions on simulation sliders, animated SVG particles on transition edges.
