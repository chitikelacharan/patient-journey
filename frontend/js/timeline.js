/**
 * Patient Journey Timeline Visualizer
 * Renders discrete clinical steps, delay anomalies, and auto-healed adversarial badges.
 */

export function renderPatientTimeline(journey, containerEl) {
  if (!containerEl) return;
  if (!journey) {
    containerEl.innerHTML = `
      <div style="color: var(--text-muted); text-align: center; padding: 3rem 0;">
        <i class="fas fa-user-clock" style="font-size: 2.5rem; opacity: 0.3; margin-bottom: 0.5rem;"></i>
        <p>Select a patient from the directory to inspect their reconstructed chronological journey.</p>
      </div>
    `;
    return;
  }

  const headerHtml = `
    <div style="background: rgba(13,20,36,0.8); border: 1px solid var(--surface-glass-border); border-radius: var(--radius-sm); padding: 1.25rem; margin-bottom: 1.5rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
        <div>
          <span style="font-size: 1.25rem; font-weight: 700; font-family: var(--font-display); color: #FFF;">
            ${journey.pseudonym_id}
          </span>
          <span class="badge-tag" style="background: rgba(0, 229, 255, 0.1); color: var(--accent-cyan); margin-left: 0.5rem;">
            ${journey.cohort}
          </span>
          ${journey.has_healed_anomalies ? `
            <span class="badge-tag pulse-live" style="margin-left: 0.5rem; background: rgba(0,230,118,0.15); border-color: rgba(0,230,118,0.4);">
              <i class="fas fa-shield-alt"></i> Adversarial Healed
            </span>
          ` : ''}
        </div>
        <div style="text-align: right;">
          <div style="font-size: 0.72rem; color: var(--text-muted);">Total In-Hospital Duration</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: ${journey.total_duration_hours > 40 ? '#FF5252' : '#00E676'}; font-family: var(--font-display);">
            ${journey.total_duration_hours} hrs
          </div>
        </div>
      </div>
      <div style="font-size: 0.82rem; color: var(--text-secondary); display: flex; gap: 1.5rem;">
        <span><strong>Diagnosis:</strong> ${journey.primary_diagnosis}</span>
        <span><strong>Status:</strong> ${journey.status}</span>
        <span><strong>Events Recorded:</strong> ${journey.events.length}</span>
      </div>
    </div>
  `;

  let stepsHtml = '';
  journey.events.forEach((evt, idx) => {
    const isHealed = evt.status === 'AUTOCORRECTED' || (evt.anomaly_tags && evt.anomaly_tags.length > 0);
    const isDelayed = evt.duration_from_previous_hours && evt.duration_from_previous_hours > 8.0;

    let chipBadges = '';
    if (evt.anomaly_tags && evt.anomaly_tags.length > 0) {
      evt.anomaly_tags.forEach(tag => {
        chipBadges += `<span class="meta-chip healed"><i class="fas fa-check-circle"></i> ${tag.replace(/_/g, ' ')}</span>`;
      });
    }

    if (evt.duration_from_previous_hours) {
      const isSevere = evt.duration_from_previous_hours > 12.0;
      chipBadges += `
        <span class="meta-chip ${isSevere ? 'delay' : ''}">
          <i class="fas fa-stopwatch"></i> +${evt.duration_from_previous_hours}h from prev stage
        </span>
      `;
    }

    // Source system badge
    chipBadges += `<span class="meta-chip"><i class="fas fa-database"></i> Source: ${evt.source_system}</span>`;

    stepsHtml += `
      <div class="timeline-step ${isHealed ? 'healed' : ''} ${isDelayed ? 'delayed' : ''}">
        <div class="timeline-marker">
          <i class="fas ${isHealed ? 'fa-magic' : (isDelayed ? 'fa-exclamation' : 'fa-circle')}"></i>
        </div>
        <div class="step-card">
          <div class="step-header">
            <span class="step-name">${evt.event_type.replace(/_/g, ' ')}</span>
            <span class="step-timestamp">${new Date(evt.timestamp).toLocaleString()}</span>
          </div>
          ${evt.status === 'AUTOCORRECTED' ? `
            <div style="font-size: 0.75rem; color: var(--accent-emerald); margin-bottom: 0.35rem;">
              <i class="fas fa-info-circle"></i> Original raw timestamp was: <code>${evt.original_timestamp}</code> (Causal DAG auto-realigned to preserve hospital analytics integrity)
            </div>
          ` : ''}
          <div class="step-meta-chips">
            ${chipBadges}
          </div>
        </div>
      </div>
    `;
  });

  containerEl.innerHTML = `
    ${headerHtml}
    <div class="timeline-stepper">
      ${stepsHtml}
    </div>
  `;
}
