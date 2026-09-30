/**
 * Interactive Process Mining Graph Renderer
 * Visualizes stage nodes, flow rates, dwell latencies, and animated pulse halos on bottlenecks.
 */

export class ProcessMiningGraph {
  constructor(canvasId, infoPanelId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.infoPanel = document.getElementById(infoPanelId);
    this.graphData = null;
    this.nodes = [];
    this.edges = [];
    this.selectedNode = null;
    this.particles = [];
    this.animationId = null;

    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
    this.setupInteractivity();
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * window.devicePixelRatio;
    this.canvas.height = rect.height * window.devicePixelRatio;
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    this.width = rect.width;
    this.height = rect.height;
    if (this.graphData) this.layoutGraph();
  }

  setData(graphData) {
    this.graphData = graphData;
    this.layoutGraph();
    this.initParticles();
    if (!this.animationId) {
      this.animate();
    }
  }

  layoutGraph() {
    if (!this.graphData) return;

    // Define topological column levels for hospital workflow
    const STAGE_COLUMNS = {
      "REGISTRATION": 0,
      "TRIAGE": 1,
      "LAB_ORDER": 2,
      "IMAGING_ORDER": 2,
      "LAB_RESULT": 3,
      "IMAGING_COMPLETE": 3,
      "SPECIALIST_CONSULT": 4,
      "PRIOR_AUTH_SUBMITTED": 5,
      "PRIOR_AUTH_DECISION": 6,
      "BED_REQUESTED": 7,
      "BED_ASSIGNED": 8,
      "DISCHARGE_ORDER": 9,
      "DISCHARGE_COMPLETED": 10
    };

    const totalCols = 11;
    const colWidth = (this.width - 120) / (totalCols - 1);

    // Group nodes by column
    const colGroups = {};
    this.graphData.nodes.forEach(n => {
      const col = STAGE_COLUMNS[n.id] !== undefined ? STAGE_COLUMNS[n.id] : 5;
      if (!colGroups[col]) colGroups[col] = [];
      colGroups[col].push(n);
    });

    this.nodes = [];
    Object.keys(colGroups).forEach(colKey => {
      const col = parseInt(colKey);
      const group = colGroups[col];
      const x = 60 + col * colWidth;

      group.forEach((node, idx) => {
        // Vertical spacing
        const yOffset = (this.height / (group.length + 1)) * (idx + 1);
        this.nodes.push({
          ...node,
          x,
          y: yOffset,
          radius: 22
        });
      });
    });

    // Map edges
    this.edges = this.graphData.edges.map(e => {
      const sourceNode = this.nodes.find(n => n.id === e.source);
      const targetNode = this.nodes.find(n => n.id === e.target);
      return {
        ...e,
        sourceNode,
        targetNode
      };
    }).filter(e => e.sourceNode && e.targetNode);
  }

  initParticles() {
    this.particles = [];
    this.edges.forEach((edge, eIdx) => {
      const count = edge.is_bottleneck ? 4 : 2;
      for (let i = 0; i < count; i++) {
        this.particles.push({
          edge,
          progress: Math.random(),
          speed: edge.is_bottleneck ? 0.003 : 0.006
        });
      }
    });
  }

  setupInteractivity() {
    this.canvas.addEventListener('click', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      let clicked = null;
      for (const n of this.nodes) {
        const dist = Math.hypot(n.x - mouseX, n.y - mouseY);
        if (dist <= n.radius + 6) {
          clicked = n;
          break;
        }
      }

      this.selectedNode = clicked;
      this.renderNodeDetails(clicked);
    });
  }

  renderNodeDetails(node) {
    if (!this.infoPanel) return;
    if (!node) {
      this.infoPanel.innerHTML = `
        <div style="color: var(--text-muted); text-align: center; padding: 2rem 0;">
          <i class="fas fa-hand-pointer" style="font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.4;"></i>
          <p>Click any stage node to inspect dwell metrics & active queue</p>
        </div>
      `;
      return;
    }

    const incoming = this.edges.filter(e => e.target === node.id);
    const outgoing = this.edges.filter(e => e.source === node.id);

    let outgoingHtml = outgoing.map(o => `
      <div style="display: flex; justify-content: space-between; font-size: 0.78rem; padding: 0.35rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
        <span>To: <strong>${o.target.replace('_', ' ')}</strong></span>
        <span style="color: ${o.is_bottleneck ? '#FF5252' : '#00E5FF'};">
          ${o.median_duration_hours}h (P90: ${o.p90_duration_hours}h) | BCI: ${o.bci_score}
        </span>
      </div>
    `).join('');

    this.infoPanel.innerHTML = `
      <div style="border-left: 3px solid var(--accent-cyan); padding-left: 0.85rem; margin-bottom: 1rem;">
        <h4 style="font-family: var(--font-display); font-size: 1.15rem; color: #FFF;">${node.label}</h4>
        <span class="badge-tag" style="background: rgba(255,255,255,0.06); color: var(--text-secondary); margin-top: 0.2rem;">
          Category: ${node.stage_category}
        </span>
      </div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="background: rgba(7,11,20,0.5); padding: 0.75rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);">
          <div style="font-size: 0.72rem; color: var(--text-muted);">Avg Stage Dwell</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: var(--accent-cyan); font-family: var(--font-display);">
            ${node.avg_dwell_hours} hrs
          </div>
        </div>
        <div style="background: rgba(7,11,20,0.5); padding: 0.75rem; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);">
          <div style="font-size: 0.72rem; color: var(--text-muted);">Queued Patients</div>
          <div style="font-size: 1.4rem; font-weight: 700; color: #FFF; font-family: var(--font-display);">
            ${node.queued_patients_count}
          </div>
        </div>
      </div>

      <div style="font-size: 0.82rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem;">
        Downstream Transitions & Latency:
      </div>
      <div>${outgoingHtml || '<span style="font-size: 0.75rem; color: var(--text-muted);">Final exit stage</span>'}</div>
    `;
  }

  animate() {
    this.ctx.clearRect(0, 0, this.width, this.height);
    const now = Date.now() * 0.002;

    // Draw Edges
    this.edges.forEach(edge => {
      const u = edge.sourceNode;
      const v = edge.targetNode;
      if (!u || !v) return;

      this.ctx.beginPath();
      this.ctx.moveTo(u.x, u.y);

      // Curved control point for non-adjacent or branch lines
      const cpX = (u.x + v.x) / 2;
      const cpY = (u.y + v.y) / 2 + (u.y === v.y ? 0 : (v.y - u.y) * 0.15);
      this.ctx.quadraticCurveTo(cpX, cpY, v.x, v.y);

      if (edge.is_bottleneck) {
        this.ctx.strokeStyle = edge.bottleneck_severity === 'CRITICAL' ? 'rgba(255, 23, 68, 0.7)' : 'rgba(255, 179, 0, 0.6)';
        this.ctx.lineWidth = edge.bottleneck_severity === 'CRITICAL' ? 3.5 : 2.5;
      } else {
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
        this.ctx.lineWidth = 1.5;
      }
      this.ctx.stroke();

      // Draw Edge Label (median duration)
      const midX = cpX;
      const midY = cpY - 8;
      this.ctx.font = '10px "Plus Jakarta Sans", sans-serif';
      this.ctx.fillStyle = edge.is_bottleneck ? '#FF8A80' : 'rgba(148, 163, 184, 0.7)';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(`${edge.median_duration_hours}h`, midX, midY);
    });

    // Update & Draw Flow Particles
    this.particles.forEach(p => {
      p.progress += p.speed;
      if (p.progress > 1.0) p.progress = 0;

      const u = p.edge.sourceNode;
      const v = p.edge.targetNode;
      if (!u || !v) return;

      const cpX = (u.x + v.x) / 2;
      const cpY = (u.y + v.y) / 2 + (u.y === v.y ? 0 : (v.y - u.y) * 0.15);

      // Quadratic bezier point calculation
      const t = p.progress;
      const px = (1 - t) * (1 - t) * u.x + 2 * (1 - t) * t * cpX + t * t * v.x;
      const py = (1 - t) * (1 - t) * u.y + 2 * (1 - t) * t * cpY + t * t * v.y;

      this.ctx.beginPath();
      this.ctx.arc(px, py, p.edge.is_bottleneck ? 3.5 : 2.5, 0, Math.PI * 2);
      this.ctx.fillStyle = p.edge.is_bottleneck ? '#FF1744' : '#00E5FF';
      this.ctx.shadowColor = p.edge.is_bottleneck ? '#FF1744' : '#00E5FF';
      this.ctx.shadowBlur = 6;
      this.ctx.fill();
      this.ctx.shadowBlur = 0;
    });

    // Draw Nodes
    this.nodes.forEach(node => {
      const isSelected = this.selectedNode && this.selectedNode.id === node.id;
      const hasCriticalOutgoing = this.edges.some(e => e.source === node.id && e.bottleneck_severity === 'CRITICAL');

      // Pulse Halo for choke points
      if (hasCriticalOutgoing) {
        const pulseR = node.radius + 6 + Math.sin(now * 3) * 4;
        this.ctx.beginPath();
        this.ctx.arc(node.x, node.y, pulseR, 0, Math.PI * 2);
        this.ctx.strokeStyle = 'rgba(255, 23, 68, 0.4)';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
      }

      // Main Node Circle
      this.ctx.beginPath();
      this.ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = isSelected ? '#1E293B' : '#0F172A';
      this.ctx.fill();

      this.ctx.lineWidth = isSelected ? 3 : 2;
      this.ctx.strokeStyle = hasCriticalOutgoing 
        ? '#FF1744' 
        : (isSelected ? '#00E5FF' : 'rgba(0, 229, 255, 0.5)');
      this.ctx.stroke();

      // Node Label
      this.ctx.font = '10px "Outfit", sans-serif';
      this.ctx.fillStyle = '#FFFFFF';
      this.ctx.textAlign = 'center';
      const shortName = node.label.length > 12 ? node.label.substring(0, 10) + '..' : node.label;
      this.ctx.fillText(shortName, node.x, node.y + 3);

      // Sub-badge: queued count
      this.ctx.font = '9px monospace';
      this.ctx.fillStyle = 'rgba(148, 163, 184, 0.8)';
      this.ctx.fillText(`n=${node.queued_patients_count}`, node.x, node.y + node.radius + 12);
    });

    this.animationId = requestAnimationFrame(() => this.animate());
  }

  destroy() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
  }
}
