/**
 * Counterfactual "What-If" Simulation Controller
 */
import { API } from './api.js';

export class WhatIfSimulatorUI {
  constructor() {
    this.sliderPA = document.getElementById('slider-pa');
    this.sliderDiag = document.getElementById('slider-diag');
    this.sliderDC = document.getElementById('slider-dc');

    this.valPA = document.getElementById('val-pa');
    this.valDiag = document.getElementById('val-diag');
    this.valDC = document.getElementById('val-dc');

    this.resSavedPt = document.getElementById('sim-saved-pt');
    this.resBedHours = document.getElementById('sim-bed-hours');
    this.resPct = document.getElementById('sim-pct');
    this.resCost = document.getElementById('sim-cost');
    this.breakdownContainer = document.getElementById('sim-breakdown-body');

    this.debounceTimer = null;
    this.setupListeners();
  }

  setupListeners() {
    const triggerSim = () => {
      this.valPA.textContent = `${this.sliderPA.value}%`;
      this.valDiag.textContent = `${this.sliderDiag.value}%`;
      this.valDC.textContent = `${this.sliderDC.value}%`;

      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => this.run(), 200);
    };

    if (this.sliderPA) this.sliderPA.addEventListener('input', triggerSim);
    if (this.sliderDiag) this.sliderDiag.addEventListener('input', triggerSim);
    if (this.sliderDC) this.sliderDC.addEventListener('input', triggerSim);
  }

  async run() {
    try {
      const payload = {
        prior_auth_automation_pct: parseFloat(this.sliderPA.value),
        diagnostic_batch_speedup_pct: parseFloat(this.sliderDiag.value),
        discharge_transport_speedup_pct: parseFloat(this.sliderDC.value)
      };

      const res = await API.runSimulation(payload);

      if (this.resSavedPt) this.resSavedPt.textContent = `${res.hours_saved_per_patient} hrs`;
      if (this.resBedHours) this.resBedHours.textContent = `${Math.round(res.total_bed_hours_recovered)} hrs`;
      if (this.resPct) this.resPct.textContent = `${res.wait_time_reduction_pct}%`;
      if (this.resCost) this.resCost.textContent = `$${res.annual_cost_savings_estimate.toLocaleString()}`;

      if (this.breakdownContainer && res.stage_breakdown) {
        let html = '';
        Object.entries(res.stage_breakdown).forEach(([stage, data]) => {
          html += `
            <div style="margin-bottom: 0.85rem;">
              <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.25rem;">
                <span>${stage}</span>
                <span style="color: var(--accent-emerald);">-${data.reduction_hours} hrs (-${data.baseline_avg_hours > 0 ? Math.round(data.reduction_hours / data.baseline_avg_hours * 100) : 0}%)</span>
              </div>
              <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; display: flex;">
                <div style="width: ${Math.max(5, (data.projected_avg_hours / Math.max(0.1, data.baseline_avg_hours)) * 100)}%; background: var(--accent-cyan); height: 100%;"></div>
                <div style="width: ${Math.min(95, (data.reduction_hours / Math.max(0.1, data.baseline_avg_hours)) * 100)}%; background: var(--accent-emerald); height: 100%;"></div>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted); margin-top: 0.15rem;">
                <span>Baseline: ${data.baseline_avg_hours}h</span>
                <span>Simulated: ${data.projected_avg_hours}h</span>
              </div>
            </div>
          `;
        });
        this.breakdownContainer.innerHTML = html;
      }
    } catch (err) {
      console.error("Simulation error:", err);
    }
  }
}
