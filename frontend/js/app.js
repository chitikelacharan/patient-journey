/**
 * Main Application Orchestrator for Med-Pulse 360
 * Patient Journey Bottleneck Analyzer
 */

import { API } from './api.js';
import { ProcessMiningGraph } from './graph.js';
import { renderPatientTimeline } from './timeline.js';
import { WhatIfSimulatorUI } from './simulator.js';
import { AdversarialSandboxUI } from './adversarial_sandbox.js';

class MedPulseApp {
  constructor() {
    this.currentTab = 'tab-dashboard';
    this.processGraph = null;
    this.simulatorUI = null;
    this.adversarialUI = null;
    this.allPatients = [];
    this.selectedPatientId = null;

    this.init();
  }

  async init() {
    this.setupTabs();
    this.setupQuickActions();

    // Initialize Subsystems
    this.processGraph = new ProcessMiningGraph('graph-canvas', 'graph-node-details');
    this.simulatorUI = new WhatIfSimulatorUI();
    this.adversarialUI = new AdversarialSandboxUI('sandbox-term-body', 'quarantine-tbody');

    // Initial Data Fetch
    await this.refreshDashboard();
    await this.loadPatientsList();
    await this.loadAuditLogs();

    // Run baseline simulation calculation
    await this.simulatorUI.run();
  }

  setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
        if (targetTab === this.currentTab) return;

        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        const activeContent = document.getElementById(targetTab);
        if (activeContent) activeContent.classList.add('active');

        this.currentTab = targetTab;

        // Specific tab activation logic
        if (targetTab === 'tab-graph' && this.processGraph) {
          setTimeout(() => this.processGraph.resizeCanvas(), 50);
        }
        if (targetTab === 'tab-audit') {
          this.loadAuditLogs();
        }
      });
    });
  }

  setupQuickActions() {
    // Audit Verification Button
    const verifyBtn = document.getElementById('btn-verify-audit');
    if (verifyBtn) {
      verifyBtn.addEventListener('click', async () => {
        try {
          const res = await API.verifyAuditChain();
          alert(`HIPAA Cryptographic Audit Proof:\nStatus: ${res.status}\nVerified Block Count: ${res.verified_count}\nTamper Detected: ${res.tamper_detected}\nMessage: ${res.message}`);
        } catch (e) {
          alert(`Verification failed: ${e.message}`);
        }
      });
    }

    // Refresh Data Button
    const refreshBtn = document.getElementById('btn-refresh-all');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        await this.refreshDashboard();
        await this.loadPatientsList();
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Telemetry';
      });
    }

    // Reset / Re-seed Button
    const resetBtn = document.getElementById('btn-reset-db');
    if (resetBtn) {
      resetBtn.addEventListener('click', async () => {
        if (confirm("Reset and re-seed the clinical database with 120 synthetic patients?")) {
          resetBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Resetting...';
          await API.resetData();
          await this.refreshDashboard();
          await this.loadPatientsList();
          resetBtn.innerHTML = '<i class="fas fa-database"></i> Reset & Re-Seed';
        }
      });
    }

    // Search and filter for Patient Directory
    const searchInput = document.getElementById('patient-search-input');
    const cohortFilter = document.getElementById('patient-cohort-filter');

    const handleFilterChange = () => {
      const q = searchInput ? searchInput.value.trim() : '';
      const c = cohortFilter ? cohortFilter.value : '';
      this.loadPatientsList({ search: q, cohort: c });
    };

    if (searchInput) searchInput.addEventListener('input', handleFilterChange);
    if (cohortFilter) cohortFilter.addEventListener('change', handleFilterChange);
  }

  async refreshDashboard() {
    try {
      // 1. KPI Summary
      const kpi = await API.getKpiSummary();
      document.getElementById('kpi-active-patients').textContent = kpi.active_patients;
      document.getElementById('kpi-cohort-total').textContent = `${kpi.total_cohort_patients} Total Traces`;
      document.getElementById('kpi-avg-stay').textContent = `${kpi.avg_length_of_stay_hours}h`;
      document.getElementById('kpi-top-choke').textContent = kpi.top_critical_choke_point.split('->')[0].replace(/_/g, ' ');
      document.getElementById('kpi-choke-bci').textContent = `BCI: ${kpi.top_choke_point_bci} (Critical)`;
      document.getElementById('kpi-healed-count').textContent = kpi.healed_anomalies_count;
      document.getElementById('kpi-quarantine-count').textContent = `${kpi.quarantined_payloads_count} Quarantined Feeds`;

      // 2. Process Mining Graph Data
      const graphData = await API.getProcessGraph();
      if (this.processGraph) {
        this.processGraph.setData(graphData);
      }

      // 3. Top Bottlenecks Table
      const bottlenecks = await API.getTopBottlenecks(5);
      this.renderBottlenecksTable(bottlenecks);

      // 4. Operational Alerts Feed
      this.renderAlertFeed(bottlenecks, kpi);

      // 5. Root Cause AI Factors
      const rootCause = await API.getRootCauseAnalysis();
      this.renderRootCauseCards(rootCause);

    } catch (err) {
      console.error("Dashboard refresh error:", err);
    }
  }

  renderBottlenecksTable(bottlenecks) {
    const tbody = document.getElementById('bottlenecks-table-body');
    if (!tbody) return;

    if (!bottlenecks || bottlenecks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No critical choke points detected.</td></tr>`;
      return;
    }

    let html = '';
    bottlenecks.forEach(b => {
      const isCritical = b.severity === 'CRITICAL';
      html += `
        <tr>
          <td>
            <strong>${b.source_stage.replace(/_/g, ' ')}</strong>
            <i class="fas fa-arrow-right" style="font-size: 0.7rem; color: var(--accent-cyan); margin: 0 0.35rem;"></i>
            <strong>${b.target_stage.replace(/_/g, ' ')}</strong>
            <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.2rem;">${b.primary_choke_driver}</div>
          </td>
          <td><span class="severity-pill ${b.severity}">${b.severity}</span></td>
          <td><strong style="color: ${isCritical ? '#FF5252' : '#FFD54F'}; font-family: var(--font-mono);">${b.bci_score}</strong></td>
          <td><span style="font-family: var(--font-mono);">${b.median_hours}h</span> <span style="font-size:0.75rem; color:var(--text-muted);">(P90: ${b.p90_hours}h)</span></td>
          <td><span style="font-family: var(--font-mono);">${b.sla_target_hours}h</span></td>
          <td style="color: #FF5252; font-family: var(--font-mono); font-weight: 600;">$${b.estimated_annual_cost_delay.toLocaleString()}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  }

  renderAlertFeed(bottlenecks, kpi) {
    const alertList = document.getElementById('alert-feed-container');
    if (!alertList) return;

    let items = '';

    // Bottleneck alerts
    bottlenecks.forEach(b => {
      const isCritical = b.severity === 'CRITICAL';
      items += `
        <div class="alert-item ${isCritical ? 'critical' : 'moderate'}">
          <div class="alert-icon"><i class="fas fa-exclamation-triangle"></i></div>
          <div class="alert-content">
            <div class="alert-title">${b.transition.replace(/_/g, ' ')} Choke Point</div>
            <div class="alert-meta">
              Median duration ${b.median_hours}h exceeds SLA ${b.sla_target_hours}h | ${b.stalled_patients_count} patients impacted.
            </div>
          </div>
        </div>
      `;
    });

    // Healed resilience alert
    items += `
      <div class="alert-item healed">
        <div class="alert-icon"><i class="fas fa-shield-virus"></i></div>
        <div class="alert-content">
          <div class="alert-title">Adversarial Resilience Active</div>
          <div class="alert-meta">
            ${kpi.healed_anomalies_count} out-of-order & duplicate clinical events auto-repaired. ${kpi.quarantined_payloads_count} malformed payloads isolated.
          </div>
        </div>
      </div>
    `;

    alertList.innerHTML = items;
  }

  renderRootCauseCards(rootCause) {
    const container = document.getElementById('root-cause-cards-container');
    if (!container) return;

    let html = '';
    rootCause.factors.forEach(f => {
      const isPositive = f.correlation_coefficient > 0;
      html += `
        <div class="glass-panel" style="padding: 1.25rem; border-left: 3px solid ${isPositive ? 'var(--accent-crimson)' : 'var(--accent-cyan)'};">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <div>
              <span class="badge-tag" style="background: rgba(255,255,255,0.06); font-size: 0.68rem; margin-bottom: 0.35rem;">${f.category}</span>
              <h4 style="font-family: var(--font-display); font-size: 1rem; color: #FFF;">${f.factor_name}</h4>
            </div>
            <div style="text-align: right;">
              <div style="font-family: var(--font-mono); font-size: 1.1rem; font-weight: 700; color: ${f.correlation_coefficient > 0.6 ? '#FF5252' : '#FFD54F'};">
                r = ${f.correlation_coefficient}
              </div>
              <div style="font-size: 0.68rem; color: var(--text-muted);">p = ${f.p_value}</div>
            </div>
          </div>
          <p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.75rem;">${f.description}</p>
          <div style="background: rgba(0, 229, 255, 0.06); border: 1px solid rgba(0, 229, 255, 0.15); border-radius: var(--radius-sm); padding: 0.65rem 0.85rem; font-size: 0.76rem; color: var(--accent-cyan);">
            <strong><i class="fas fa-lightbulb"></i> Recommended Action:</strong> ${f.recommended_intervention}
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  }

  async loadPatientsList(filterParams = {}) {
    const tbody = document.getElementById('patient-directory-tbody');
    if (!tbody) return;

    try {
      const res = await API.getPatients(filterParams);
      this.allPatients = res.patients;

      if (!this.allPatients || this.allPatients.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No patients found matching criteria.</td></tr>`;
        return;
      }

      let html = '';
      this.allPatients.forEach(p => {
        const isSelected = this.selectedPatientId === p.id;
        html += `
          <tr data-patient-id="${p.id}" style="cursor: pointer; ${isSelected ? 'background: rgba(0,229,255,0.08);' : ''}">
            <td><strong style="color: var(--accent-cyan); font-family: var(--font-mono);">${p.pseudonym_id}</strong></td>
            <td>${p.cohort}</td>
            <td style="font-size: 0.8rem;">${p.primary_diagnosis}</td>
            <td><span class="badge-tag" style="background: rgba(255,255,255,0.06);">${p.status}</span></td>
            <td><span style="font-family: var(--font-mono);">${p.total_duration_hours}h</span></td>
            <td>
              ${p.healed_anomalies_count > 0 ? `
                <span class="badge-tag" style="background: rgba(0,230,118,0.12); color: var(--accent-emerald);">
                  <i class="fas fa-shield-alt"></i> ${p.healed_anomalies_count} Healed
                </span>
              ` : '<span style="color: var(--text-muted); font-size: 0.75rem;">Clean</span>'}
            </td>
          </tr>
        `;
      });
      tbody.innerHTML = html;

      // Bind row clicks
      tbody.querySelectorAll('tr[data-patient-id]').forEach(row => {
        row.addEventListener('click', async () => {
          tbody.querySelectorAll('tr').forEach(r => r.style.background = 'transparent');
          row.style.background = 'rgba(0, 229, 255, 0.08)';

          const pid = parseInt(row.getAttribute('data-patient-id'));
          this.selectedPatientId = pid;
          await this.inspectPatient(pid);
        });
      });

      // Select first patient by default if none selected
      if (!this.selectedPatientId && this.allPatients.length > 0) {
        this.selectedPatientId = this.allPatients[0].id;
        await this.inspectPatient(this.selectedPatientId);
      }
    } catch (err) {
      console.error("Failed to load patients list:", err);
    }
  }

  async inspectPatient(patientId) {
    const timelineContainer = document.getElementById('patient-timeline-container');
    if (!timelineContainer) return;
    try {
      const journey = await API.getPatientTimeline(patientId);
      renderPatientTimeline(journey, timelineContainer);
    } catch (err) {
      console.error("Failed to inspect patient:", err);
    }
  }

  async loadAuditLogs() {
    const tbody = document.getElementById('audit-log-tbody');
    if (!tbody) return;

    try {
      const logs = await API.getAuditLogs(30);
      let html = '';
      logs.forEach(l => {
        html += `
          <tr>
            <td><code>#${l.sequence_number}</code></td>
            <td style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted);">${new Date(l.timestamp).toLocaleTimeString()}</td>
            <td><strong>${l.action}</strong></td>
            <td><span class="badge-tag" style="background: rgba(255,255,255,0.06);">${l.actor}</span></td>
            <td><code style="color: var(--accent-cyan); font-size: 0.72rem;">${l.current_hash.substring(0, 16)}...</code></td>
            <td><code style="color: var(--text-muted); font-size: 0.72rem;">${l.previous_hash.substring(0, 16)}...</code></td>
          </tr>
        `;
      });
      tbody.innerHTML = html;
    } catch (err) {
      console.error("Failed to load audit logs:", err);
    }
  }
}

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new MedPulseApp();
});
