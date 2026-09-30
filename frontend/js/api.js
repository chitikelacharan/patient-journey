/**
 * API Client for Patient Journey Bottleneck Analyzer Backend
 */
const API_BASE = window.location.origin.includes(':8000') || window.location.origin.includes('localhost') 
  ? '/api' 
  : 'http://127.0.0.1:8000/api';

export const API = {
  async getKpiSummary() {
    const res = await fetch(`${API_BASE}/bottlenecks/kpi-summary`);
    if (!res.ok) throw new Error('Failed to fetch KPI summary');
    return await res.json();
  },

  async getProcessGraph() {
    const res = await fetch(`${API_BASE}/bottlenecks/process-graph`);
    if (!res.ok) throw new Error('Failed to fetch process mining graph');
    return await res.json();
  },

  async getTopBottlenecks(limit = 5) {
    const res = await fetch(`${API_BASE}/bottlenecks/top?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch top bottlenecks');
    return await res.json();
  },

  async getPatients(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${API_BASE}/journeys/patients?${query}`);
    if (!res.ok) throw new Error('Failed to fetch patients list');
    return await res.json();
  },

  async getPatientTimeline(patientId) {
    const res = await fetch(`${API_BASE}/journeys/${patientId}`);
    if (!res.ok) throw new Error('Failed to fetch patient timeline');
    return await res.json();
  },

  async getRootCauseAnalysis() {
    const res = await fetch(`${API_BASE}/ai/root-cause`);
    if (!res.ok) throw new Error('Failed to fetch root cause analysis');
    return await res.json();
  },

  async runSimulation(payload) {
    const res = await fetch(`${API_BASE}/ai/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Simulation calculation failed');
    return await res.json();
  },

  async injectAdversarialTest(scenario, patientIdentifier = 'TEST-ADV-101', cohort = 'Emergency') {
    const res = await fetch(`${API_BASE}/adversarial/inject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario, patient_identifier: patientIdentifier, cohort })
    });
    if (!res.ok) throw new Error('Adversarial injection failed');
    return await res.json();
  },

  async getQuarantineRecords() {
    const res = await fetch(`${API_BASE}/adversarial/quarantine`);
    if (!res.ok) throw new Error('Failed to fetch quarantine vault records');
    return await res.json();
  },

  async getAuditLogs(limit = 30) {
    const res = await fetch(`${API_BASE}/audit/logs?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch audit logs');
    return await res.json();
  },

  async verifyAuditChain() {
    const res = await fetch(`${API_BASE}/audit/verify`);
    if (!res.ok) throw new Error('Audit verification failed');
    return await res.json();
  },

  async resetData() {
    const res = await fetch(`${API_BASE}/audit/reset`, { method: 'POST' });
    if (!res.ok) throw new Error('Data reset failed');
    return await res.json();
  }
};
