/**
 * Adversarial Resilience Live Sandbox Harness
 */
import { API } from './api.js';

export class AdversarialSandboxUI {
  constructor(termBodyId, quarantineTableId) {
    this.termBody = document.getElementById(termBodyId);
    this.quarantineTable = document.getElementById(quarantineTableId);
    this.setupButtons();
    this.loadQuarantineRecords();
  }

  log(text, type = 'info') {
    if (!this.termBody) return;
    const time = new Date().toLocaleTimeString();
    const line = document.createElement('div');
    line.className = `term-line ${type}`;
    line.innerHTML = `<span class="dim">[${time}]</span> ${text}`;
    this.termBody.appendChild(line);
    this.termBody.scrollTop = this.termBody.scrollHeight;
  }

  setupButtons() {
    const buttons = document.querySelectorAll('[data-adversarial-scenario]');
    buttons.forEach(btn => {
      btn.addEventListener('click', async () => {
        const scenario = btn.getAttribute('data-adversarial-scenario');
        await this.runInjection(scenario);
      });
    });

    const refreshQuarantineBtn = document.getElementById('btn-refresh-quarantine');
    if (refreshQuarantineBtn) {
      refreshQuarantineBtn.addEventListener('click', () => this.loadQuarantineRecords());
    }

    const clearLogBtn = document.getElementById('btn-clear-term');
    if (clearLogBtn) {
      clearLogBtn.addEventListener('click', () => {
        if (this.termBody) this.termBody.innerHTML = '';
        this.log('Interactive Adversarial Terminal cleared. Ready for injection test.', 'dim');
      });
    }
  }

  async runInjection(scenario) {
    this.log(`>>> INJECTING ADVERSARIAL STRESS TEST: [${scenario}]`, 'warn');
    try {
      const res = await API.injectAdversarialTest(scenario);
      
      this.log(`PAYLOAD DETAILS: ${res.injection_description}`, 'dim');
      this.log(`RESILIENCE ACTION: ${res.engine_action}`, 'info');

      const outcome = res.result;
      if (outcome.status === 'QUARANTINED') {
        this.log(`STATUS: QUARANTINED (Safe Vault ID Generated, Zero Metric Skew)`, 'error');
        this.log(`AUDIT HASH: ${outcome.audit_hash.substring(0, 24)}... (SHA-256 Ledger Updated)`, 'info');
        await this.loadQuarantineRecords();
      } else if (outcome.status === 'DUPLICATE_SUPPRESSED') {
        this.log(`STATUS: DUPLICATE_SUPPRESSED (1-hour sliding fingerprint cache matched)`, 'warn');
        this.log(`AUDIT HASH: ${outcome.audit_hash.substring(0, 24)}...`, 'info');
      } else if (outcome.status === 'AUTOCORRECTED') {
        this.log(`STATUS: AUTOCORRECTED (Causal DAG successfully healed timestamp/data)`, 'success');
        this.log(`ANOMALY TAGS: [${outcome.anomaly_tags.join(', ')}]`, 'success');
        this.log(`AUDIT HASH: ${outcome.audit_hash.substring(0, 24)}...`, 'info');
      } else {
        this.log(`STATUS: ${outcome.status} - ${outcome.message}`, 'success');
      }

      this.log(`-----------------------------------------------------------------`, 'dim');
    } catch (err) {
      this.log(`Injection execution error: ${err.message}`, 'error');
    }
  }

  async loadQuarantineRecords() {
    if (!this.quarantineTable) return;
    try {
      const records = await API.getQuarantineRecords();
      if (!records || records.length === 0) {
        this.quarantineTable.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No quarantined payloads. System is clean.</td></tr>`;
        return;
      }

      let html = '';
      records.forEach(r => {
        html += `
          <tr>
            <td><code>#Q-${r.id}</code></td>
            <td><span class="badge-tag" style="background: rgba(255,255,255,0.06);">${r.source_system}</span></td>
            <td style="color: #FF5252; font-size: 0.78rem;">${r.reason}</td>
            <td style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted);">${r.received_at ? new Date(r.received_at).toLocaleTimeString() : 'N/A'}</td>
          </tr>
        `;
      });
      this.quarantineTable.innerHTML = html;
    } catch (err) {
      console.error("Failed to load quarantine records:", err);
    }
  }
}
