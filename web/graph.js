/*
 * vinhlong360 — Interactive Knowledge Graph Visualization
 *
 * Pure JS force-directed graph on HTML5 Canvas.
 * Reads data via window.Store (entities, relationships, byId, TYPE_META).
 *
 * Public API:
 *   initGraph(containerId, centerEntityId)  — mount and render
 *   expandNode(entityId)                    — add neighbors to view
 *   highlightPath(fromId, toId)             — shortest-path highlight
 *   getVisibleGraph(entityId, hops)         — extract subgraph data
 */

(function () {
  "use strict";

  /* ================================================================
   *  CONSTANTS & CONFIG
   * ================================================================ */

  const MAX_NODES = 50;

  // Node colors by entity type (matches map palette)
  const TYPE_COLORS = {
    attraction:    "#3b82f6", // blue
    nature:        "#22c55e", // green (not in current data but spec'd)
    product:       "#f97316", // orange
    dish:          "#ef4444", // red
    experience:    "#8b5cf6", // violet
    craft_village: "#d97706", // amber
    event:         "#ec4899", // pink
    history:       "#6b7280", // gray
    accommodation: "#14b8a6", // teal
    organization:  "#64748b", // slate
    place:         "#a855f7", // purple
  };

  // Emoji icons rendered inside nodes
  const TYPE_EMOJI = {
    attraction:    "\u{1F3DB}️", // 🏛️
    nature:        "\u{1F33F}",        // 🌿
    product:       "\u{1F34A}",        // 🍊
    dish:          "\u{1F35C}",        // 🍜
    experience:    "\u{1F33E}",        // 🌾
    craft_village: "\u{1F3FA}",        // 🏺
    event:         "\u{1F3AD}",        // 🎭
    history:       "\u{1F4DC}",        // 📜
    accommodation: "\u{1F3E0}",        // 🏠
    organization:  "\u{1F3E2}",        // 🏢
    place:         "\u{1F4CD}",        // 📍
  };

  // Edge styles by relationship type
  const EDGE_STYLES = {
    near:        { color: "#9ca3af", dash: [4, 4], width: 1   },
    related_to:  { color: "#3b82f6", dash: [],     width: 1.5 },
    belongs_to:  { color: "#22c55e", dash: [],     width: 1.5 },
    hosts:       { color: "#8b5cf6", dash: [],     width: 1.5 },
    offered_by:  { color: "#f59e0b", dash: [6, 3], width: 1   },
    made_by:     { color: "#f97316", dash: [6, 3], width: 1   },
    produced_in: { color: "#22c55e", dash: [],     width: 1.5 },
    supplies_to: { color: "#06b6d4", dash: [4, 4], width: 1   },
  };
  const DEFAULT_EDGE = { color: "#d1d5db", dash: [], width: 1 };

  // Physics constants
  const REPULSION   = 3000;
  const ATTRACTION   = 0.005;
  const DAMPING      = 0.85;
  const MIN_VELOCITY = 0.1;
  const MAX_STEPS    = 300;

  /* ================================================================
   *  CSS INJECTION
   * ================================================================ */

  function injectCSS() {
    if (document.getElementById("graph-styles")) return;
    const style = document.createElement("style");
    style.id = "graph-styles";
    style.textContent = `
      .graph-wrapper {
        position: relative;
        width: 100%;
        height: 100%;
        min-height: 400px;
        background: #0f172a;
        border-radius: 12px;
        overflow: hidden;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      }
      .graph-canvas {
        display: block;
        width: 100%;
        height: 100%;
        cursor: grab;
      }
      .graph-canvas.dragging { cursor: grabbing; }

      /* --- Controls panel --- */
      .graph-controls {
        position: absolute;
        top: 12px;
        left: 12px;
        background: rgba(15, 23, 42, 0.92);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 14px;
        color: #e2e8f0;
        font-size: 13px;
        max-width: 260px;
        z-index: 10;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .graph-controls h4 {
        margin: 0 0 2px;
        font-size: 14px;
        color: #f8fafc;
        font-weight: 600;
      }
      .graph-controls input[type="text"] {
        width: 100%;
        padding: 6px 10px;
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 6px;
        background: rgba(30,41,59,0.8);
        color: #f1f5f9;
        font-size: 13px;
        outline: none;
        box-sizing: border-box;
      }
      .graph-controls input[type="text"]::placeholder { color: #64748b; }
      .graph-controls input[type="text"]:focus { border-color: #3b82f6; }
      .graph-search-results {
        max-height: 120px;
        overflow-y: auto;
        background: rgba(30,41,59,0.95);
        border-radius: 6px;
        display: none;
      }
      .graph-search-results.show { display: block; }
      .graph-search-item {
        padding: 6px 10px;
        cursor: pointer;
        font-size: 12px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
      }
      .graph-search-item:hover { background: rgba(59,130,246,0.2); }

      .graph-type-filters {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
      }
      .graph-type-filters label {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        cursor: pointer;
        padding: 2px 6px;
        border-radius: 4px;
        background: rgba(255,255,255,0.05);
        user-select: none;
      }
      .graph-type-filters label:hover { background: rgba(255,255,255,0.1); }
      .graph-type-filters input { margin: 0; }

      .graph-depth-sel {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .graph-depth-sel select {
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid rgba(255,255,255,0.15);
        background: rgba(30,41,59,0.8);
        color: #f1f5f9;
        font-size: 12px;
        outline: none;
      }

      .graph-btn {
        padding: 5px 12px;
        border: none;
        border-radius: 6px;
        background: #3b82f6;
        color: #fff;
        font-size: 12px;
        cursor: pointer;
        font-weight: 500;
      }
      .graph-btn:hover { background: #2563eb; }
      .graph-btn.secondary {
        background: rgba(255,255,255,0.08);
        color: #94a3b8;
      }
      .graph-btn.secondary:hover { background: rgba(255,255,255,0.15); }

      .graph-node-count {
        font-size: 11px;
        color: #64748b;
        text-align: right;
      }

      /* --- Info panel --- */
      .graph-info {
        position: absolute;
        bottom: 12px;
        right: 12px;
        background: rgba(15, 23, 42, 0.94);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 16px;
        color: #e2e8f0;
        font-size: 13px;
        max-width: 300px;
        z-index: 10;
        display: none;
      }
      .graph-info.show { display: block; }
      .graph-info h3 {
        margin: 0 0 4px;
        font-size: 15px;
        color: #f8fafc;
      }
      .graph-info .gi-type {
        font-size: 11px;
        color: #94a3b8;
        margin-bottom: 8px;
        text-transform: capitalize;
      }
      .graph-info .gi-summary {
        font-size: 12px;
        line-height: 1.5;
        color: #cbd5e1;
        margin-bottom: 8px;
      }
      .graph-info .gi-connections {
        font-size: 11px;
        color: #64748b;
      }
      .graph-info .gi-close {
        position: absolute;
        top: 8px;
        right: 10px;
        background: none;
        border: none;
        color: #64748b;
        cursor: pointer;
        font-size: 16px;
        line-height: 1;
      }
      .graph-info .gi-close:hover { color: #f1f5f9; }
      .graph-info .gi-dblclick {
        font-size: 10px;
        color: #475569;
        margin-top: 6px;
        font-style: italic;
      }

      /* --- Controls collapse on small screens --- */
      .graph-controls-toggle {
        display: none;
        position: absolute;
        top: 12px;
        left: 12px;
        z-index: 11;
      }
      @media (max-width: 600px) {
        .graph-controls { display: none; }
        .graph-controls.open { display: flex; top: 44px; }
        .graph-controls-toggle { display: block; }
      }
    `;
    document.head.appendChild(style);
  }

  /* ================================================================
   *  DATA HELPERS
   * ================================================================ */

  const S = () => window.Store;

  /**
   * Build adjacency lists from relationships.
   * Returns { adj: Map<id, [{to, type}]> }
   */
  function buildAdj() {
    const adj = new Map();
    const rels = S().relationships;
    for (let i = 0; i < rels.length; i++) {
      const r = rels[i];
      if (!adj.has(r.from)) adj.set(r.from, []);
      if (!adj.has(r.to))   adj.set(r.to, []);
      adj.get(r.from).push({ to: r.to, type: r.type });
      adj.get(r.to).push({ to: r.from, type: r.type });
    }
    return adj;
  }

  /**
   * getVisibleGraph(entityId, hops) — BFS out from entityId up to `hops` depth.
   * Returns { nodes: Set<id>, edges: [{from, to, type}] }
   */
  function getVisibleGraph(entityId, hops, adj, typeFilter) {
    hops = hops || 2;
    const nodes = new Set();
    const edgeSet = new Set();
    const edges = [];
    const queue = [{ id: entityId, depth: 0 }];
    nodes.add(entityId);

    while (queue.length > 0) {
      const { id, depth } = queue.shift();
      if (depth >= hops) continue;
      const neighbors = adj.get(id) || [];
      for (const nb of neighbors) {
        const entity = S().byId(nb.to);
        if (!entity) continue;
        if (typeFilter && !typeFilter.has(entity.type)) continue;
        if (nodes.size >= MAX_NODES && !nodes.has(nb.to)) continue;

        const edgeKey = [id, nb.to].sort().join("::") + "::" + nb.type;
        if (!edgeSet.has(edgeKey)) {
          edgeSet.add(edgeKey);
          edges.push({ from: id, to: nb.to, type: nb.type });
        }
        if (!nodes.has(nb.to)) {
          nodes.add(nb.to);
          queue.push({ id: nb.to, depth: depth + 1 });
        }
      }
    }

    // Also add edges between already-visible nodes
    const rels = S().relationships;
    for (let i = 0; i < rels.length; i++) {
      const r = rels[i];
      if (nodes.has(r.from) && nodes.has(r.to)) {
        const edgeKey = [r.from, r.to].sort().join("::") + "::" + r.type;
        if (!edgeSet.has(edgeKey)) {
          edgeSet.add(edgeKey);
          edges.push({ from: r.from, to: r.to, type: r.type });
        }
      }
    }

    return { nodes, edges };
  }

  /**
   * BFS shortest path between two entity IDs.
   * Returns array of IDs from start to end, or null if unreachable.
   */
  function bfsPath(fromId, toId, adj) {
    if (fromId === toId) return [fromId];
    const visited = new Set([fromId]);
    const parent = new Map();
    const queue = [fromId];
    while (queue.length > 0) {
      const cur = queue.shift();
      const neighbors = adj.get(cur) || [];
      for (const nb of neighbors) {
        if (visited.has(nb.to)) continue;
        visited.add(nb.to);
        parent.set(nb.to, cur);
        if (nb.to === toId) {
          // Reconstruct path
          const path = [toId];
          let p = toId;
          while (parent.has(p)) { p = parent.get(p); path.push(p); }
          return path.reverse();
        }
        queue.push(nb.to);
      }
    }
    return null;
  }

  /**
   * Count connections for an entity (degree in the full graph).
   */
  function connectionCount(entityId, adj) {
    const neighbors = adj.get(entityId);
    return neighbors ? neighbors.length : 0;
  }

  /* ================================================================
   *  GRAPH INSTANCE
   * ================================================================ */

  /**
   * Main graph constructor. One instance per container.
   */
  function GraphViz(container, centerEntityId) {
    this.container = container;
    this.adj = buildAdj();
    this.centerEntityId = centerEntityId;
    this.hops = 2;

    // Active type filters (all enabled by default)
    this.typeFilter = null; // null = allow all

    // Graph data
    this.graphNodes = [];     // [{id, x, y, vx, vy, radius, entity, pinned}]
    this.graphEdges = [];     // [{from, to, type, sourceNode, targetNode}]
    this.nodeMap = new Map(); // id -> node object

    // Interaction state
    this.selectedNode = null;
    this.hoveredNode = null;
    this.dragNode = null;
    this.highlightedPath = null; // Set of node IDs on highlighted path
    this.highlightedEdges = null; // Set of edge keys on highlighted path

    // Camera
    this.offsetX = 0;
    this.offsetY = 0;
    this.scale = 1;
    this.isPanning = false;
    this.panStart = { x: 0, y: 0 };

    // Simulation
    this.simStep = 0;
    this.simRunning = false;
    this.animFrameId = null;

    // DOM
    this.canvas = null;
    this.ctx = null;
    this.infoPanel = null;
    this.controlsPanel = null;
    this.nodeCountEl = null;
    this.searchInput = null;
    this.searchResults = null;
    this.depthSelect = null;

    this._init();
  }

  /* ---- Initialization ---- */

  GraphViz.prototype._init = function () {
    injectCSS();
    this._buildDOM();
    this._buildGraph(this.centerEntityId);
    this._bindEvents();
    this._startSim();
  };

  GraphViz.prototype._buildDOM = function () {
    const wrap = document.createElement("div");
    wrap.className = "graph-wrapper";

    // Canvas
    const canvas = document.createElement("canvas");
    canvas.className = "graph-canvas";
    wrap.appendChild(canvas);
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");

    // Controls toggle (mobile)
    const toggle = document.createElement("button");
    toggle.className = "graph-btn graph-controls-toggle";
    toggle.textContent = "⚙️ Bảng điều khiển";
    wrap.appendChild(toggle);

    // Controls panel
    const ctrl = document.createElement("div");
    ctrl.className = "graph-controls";
    ctrl.innerHTML = this._controlsHTML();
    wrap.appendChild(ctrl);
    this.controlsPanel = ctrl;

    toggle.addEventListener("click", function () {
      ctrl.classList.toggle("open");
    });

    // Info panel
    const info = document.createElement("div");
    info.className = "graph-info";
    wrap.appendChild(info);
    this.infoPanel = info;

    this.container.innerHTML = "";
    this.container.appendChild(wrap);

    // Cache references
    this.searchInput = ctrl.querySelector(".graph-search-input");
    this.searchResults = ctrl.querySelector(".graph-search-results");
    this.depthSelect = ctrl.querySelector(".graph-depth-select");
    this.nodeCountEl = ctrl.querySelector(".graph-node-count");

    // Size canvas
    this._resizeCanvas();
  };

  GraphViz.prototype._controlsHTML = function () {
    const types = S().TYPE_META || {};
    let filterHTML = "";
    for (const t in types) {
      const emoji = TYPE_EMOJI[t] || types[t].emoji || "";
      filterHTML += '<label><input type="checkbox" class="graph-type-cb" value="' + t + '" checked /> ' + emoji + " " + types[t].label + "</label>";
    }

    return (
      '<h4>\u{1F578}️ Đồ thị tri thức</h4>' +
      '<input type="text" class="graph-search-input" placeholder="Tìm entity..." />' +
      '<div class="graph-search-results"></div>' +
      '<div class="graph-type-filters">' + filterHTML + "</div>" +
      '<div class="graph-depth-sel">' +
        '<span>Độ sâu:</span>' +
        '<select class="graph-depth-select">' +
          '<option value="1">1 hop</option>' +
          '<option value="2" selected>2 hops</option>' +
          '<option value="3">3 hops</option>' +
        "</select>" +
      "</div>" +
      '<div style="display:flex;gap:6px">' +
        '<button class="graph-btn graph-reset-btn">Reset</button>' +
        '<button class="graph-btn secondary graph-fit-btn">Vừa khung</button>' +
      "</div>" +
      '<div class="graph-node-count"></div>'
    );
  };

  GraphViz.prototype._resizeCanvas = function () {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.canvas.style.width = rect.width + "px";
    this.canvas.style.height = rect.height + "px";
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.canvasW = rect.width;
    this.canvasH = rect.height;
  };

  /* ---- Graph building ---- */

  GraphViz.prototype._buildGraph = function (centerId) {
    const sub = getVisibleGraph(centerId, this.hops, this.adj, this.typeFilter);

    this.graphNodes = [];
    this.graphEdges = [];
    this.nodeMap = new Map();
    this.highlightedPath = null;
    this.highlightedEdges = null;

    const cx = this.canvasW / 2;
    const cy = this.canvasH / 2;

    // Create node objects with random initial positions in a circle
    let idx = 0;
    const count = sub.nodes.size;
    sub.nodes.forEach(function (id) {
      const entity = S().byId(id);
      if (!entity) return;
      const angle = (idx / count) * Math.PI * 2;
      const r = 80 + Math.random() * 60;
      const deg = connectionCount(id, this.adj);
      const radius = Math.min(25, Math.max(8, 6 + Math.sqrt(deg) * 3));
      const node = {
        id: id,
        x: cx + Math.cos(angle) * r,
        y: cy + Math.sin(angle) * r,
        vx: 0,
        vy: 0,
        radius: radius,
        entity: entity,
        pinned: id === centerId,
        isCenter: id === centerId,
      };
      this.graphNodes.push(node);
      this.nodeMap.set(id, node);
      idx++;
    }.bind(this));

    // Pin center node at center
    const centerNode = this.nodeMap.get(centerId);
    if (centerNode) {
      centerNode.x = cx;
      centerNode.y = cy;
    }

    // Build edge objects
    for (const e of sub.edges) {
      const src = this.nodeMap.get(e.from);
      const tgt = this.nodeMap.get(e.to);
      if (src && tgt) {
        this.graphEdges.push({
          from: e.from,
          to: e.to,
          type: e.type,
          sourceNode: src,
          targetNode: tgt,
        });
      }
    }

    this._updateNodeCount();

    // Reset camera to center
    this.offsetX = 0;
    this.offsetY = 0;
    this.scale = 1;
  };

  GraphViz.prototype._addNeighbors = function (entityId) {
    const neighbors = this.adj.get(entityId) || [];
    const added = [];
    const cx = this.canvasW / 2;
    const cy = this.canvasH / 2;

    for (const nb of neighbors) {
      if (this.nodeMap.has(nb.to)) continue;
      if (this.graphNodes.length >= MAX_NODES) break;
      const entity = S().byId(nb.to);
      if (!entity) continue;
      if (this.typeFilter && !this.typeFilter.has(entity.type)) continue;

      const parentNode = this.nodeMap.get(entityId);
      const angle = Math.random() * Math.PI * 2;
      const r = 40 + Math.random() * 30;
      const deg = connectionCount(nb.to, this.adj);
      const radius = Math.min(25, Math.max(8, 6 + Math.sqrt(deg) * 3));
      const node = {
        id: nb.to,
        x: (parentNode ? parentNode.x : cx) + Math.cos(angle) * r,
        y: (parentNode ? parentNode.y : cy) + Math.sin(angle) * r,
        vx: 0,
        vy: 0,
        radius: radius,
        entity: entity,
        pinned: false,
        isCenter: false,
      };
      this.graphNodes.push(node);
      this.nodeMap.set(nb.to, node);
      added.push(nb.to);
    }

    // Add edges for newly visible nodes
    const rels = S().relationships;
    const edgeSet = new Set(this.graphEdges.map(function (e) {
      return [e.from, e.to].sort().join("::") + "::" + e.type;
    }));
    for (const r of rels) {
      if (this.nodeMap.has(r.from) && this.nodeMap.has(r.to)) {
        const key = [r.from, r.to].sort().join("::") + "::" + r.type;
        if (!edgeSet.has(key)) {
          edgeSet.add(key);
          this.graphEdges.push({
            from: r.from,
            to: r.to,
            type: r.type,
            sourceNode: this.nodeMap.get(r.from),
            targetNode: this.nodeMap.get(r.to),
          });
        }
      }
    }

    this._updateNodeCount();
    if (added.length > 0) this._startSim();
  };

  GraphViz.prototype._updateNodeCount = function () {
    if (this.nodeCountEl) {
      this.nodeCountEl.textContent = this.graphNodes.length + " nodes \xB7 " + this.graphEdges.length + " edges";
    }
  };

  /* ---- Physics simulation ---- */

  GraphViz.prototype._startSim = function () {
    this.simStep = 0;
    if (!this.simRunning) {
      this.simRunning = true;
      this._tick();
    }
  };

  GraphViz.prototype._tick = function () {
    if (!this.simRunning) return;

    this._physicsTick();
    this._draw();
    this.simStep++;

    // Check convergence
    let maxV = 0;
    for (const n of this.graphNodes) {
      const v = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
      if (v > maxV) maxV = v;
    }

    if (this.simStep < MAX_STEPS && maxV > MIN_VELOCITY) {
      this.animFrameId = requestAnimationFrame(this._tick.bind(this));
    } else {
      this.simRunning = false;
      this._draw(); // Final frame
    }
  };

  GraphViz.prototype._physicsTick = function () {
    const nodes = this.graphNodes;
    const edges = this.graphEdges;
    const n = nodes.length;

    // Repulsion (all pairs)
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const a = nodes[i], b = nodes[j];
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 1) { dist = 1; dx = Math.random() - 0.5; dy = Math.random() - 0.5; }
        const force = REPULSION / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (!a.pinned) { a.vx -= fx; a.vy -= fy; }
        if (!b.pinned) { b.vx += fx; b.vy += fy; }
      }
    }

    // Attraction along edges (spring force)
    for (const e of edges) {
      const a = e.sourceNode, b = e.targetNode;
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 1) dist = 1;
      const force = dist * ATTRACTION;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      if (!a.pinned) { a.vx += fx; a.vy += fy; }
      if (!b.pinned) { b.vx -= fx; b.vy -= fy; }
    }

    // Center gravity — gentle pull toward canvas center
    const cx = this.canvasW / 2;
    const cy = this.canvasH / 2;
    for (const node of nodes) {
      if (node.pinned) continue;
      node.vx += (cx - node.x) * 0.0003;
      node.vy += (cy - node.y) * 0.0003;
    }

    // Apply velocity with damping
    for (const node of nodes) {
      if (node.pinned) continue;
      node.vx *= DAMPING;
      node.vy *= DAMPING;
      node.x += node.vx;
      node.y += node.vy;
    }
  };

  /* ---- Canvas rendering ---- */

  GraphViz.prototype._draw = function () {
    const ctx = this.ctx;
    const w = this.canvasW;
    const h = this.canvasH;

    ctx.clearRect(0, 0, w, h);
    ctx.save();

    // Apply camera transform
    ctx.translate(w / 2, h / 2);
    ctx.scale(this.scale, this.scale);
    ctx.translate(-w / 2 + this.offsetX, -h / 2 + this.offsetY);

    // Determine hovered node's direct connections for highlighting
    const hoveredNeighbors = new Set();
    if (this.hoveredNode) {
      hoveredNeighbors.add(this.hoveredNode.id);
      for (const e of this.graphEdges) {
        if (e.from === this.hoveredNode.id) hoveredNeighbors.add(e.to);
        if (e.to === this.hoveredNode.id) hoveredNeighbors.add(e.from);
      }
    }

    // Draw edges
    for (const e of this.graphEdges) {
      const style = EDGE_STYLES[e.type] || DEFAULT_EDGE;
      const a = e.sourceNode, b = e.targetNode;

      // Check if this edge is on highlighted path
      const onPath = this.highlightedEdges &&
        (this.highlightedEdges.has(e.from + "::" + e.to) || this.highlightedEdges.has(e.to + "::" + e.from));

      let alpha = 0.4;
      let lineWidth = style.width;
      let color = style.color;

      if (onPath) {
        alpha = 1;
        lineWidth = 3;
        color = "#facc15"; // gold for path
      } else if (this.hoveredNode) {
        if (hoveredNeighbors.has(e.from) && hoveredNeighbors.has(e.to)) {
          alpha = 0.9;
          lineWidth = style.width + 0.5;
        } else {
          alpha = 0.1;
        }
      }

      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.globalAlpha = alpha;
      ctx.lineWidth = lineWidth;
      ctx.setLineDash(style.dash);
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    ctx.globalAlpha = 1;

    // Draw nodes
    for (const node of this.graphNodes) {
      const isHovered = this.hoveredNode && this.hoveredNode.id === node.id;
      const isSelected = this.selectedNode && this.selectedNode.id === node.id;
      const isOnPath = this.highlightedPath && this.highlightedPath.has(node.id);
      const inHoverGroup = this.hoveredNode ? hoveredNeighbors.has(node.id) : true;
      const color = TYPE_COLORS[node.entity.type] || "#6b7280";

      ctx.globalAlpha = inHoverGroup ? 1 : 0.2;

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);

      // Fill
      if (node.isCenter) {
        // Gradient for center node
        const grad = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, node.radius);
        grad.addColorStop(0, "#fff");
        grad.addColorStop(1, color);
        ctx.fillStyle = grad;
      } else {
        ctx.fillStyle = color;
      }
      ctx.fill();

      // Stroke
      if (isSelected || isHovered || isOnPath) {
        ctx.strokeStyle = isOnPath ? "#facc15" : "#fff";
        ctx.lineWidth = isSelected ? 3 : 2;
        ctx.stroke();
      } else {
        ctx.strokeStyle = "rgba(255,255,255,0.3)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Emoji inside node (only if large enough)
      if (node.radius >= 12) {
        const emoji = TYPE_EMOJI[node.entity.type] || "";
        if (emoji) {
          ctx.font = Math.round(node.radius * 0.8) + "px sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillStyle = "#fff";
          ctx.fillText(emoji, node.x, node.y);
        }
      }

      // Label below node
      ctx.globalAlpha = inHoverGroup ? 0.9 : 0.15;
      const label = node.entity.name.length > 15
        ? node.entity.name.slice(0, 14) + "…"
        : node.entity.name;
      ctx.font = (isHovered || isSelected) ? "bold 11px sans-serif" : "10px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#e2e8f0";
      ctx.fillText(label, node.x, node.y + node.radius + 4);
    }

    ctx.globalAlpha = 1;
    ctx.restore();
  };

  /* ---- Hit testing ---- */

  GraphViz.prototype._screenToWorld = function (sx, sy) {
    const w = this.canvasW;
    const h = this.canvasH;
    const wx = (sx - w / 2) / this.scale + w / 2 - this.offsetX;
    const wy = (sy - h / 2) / this.scale + h / 2 - this.offsetY;
    return { x: wx, y: wy };
  };

  GraphViz.prototype._hitTest = function (sx, sy) {
    const { x, y } = this._screenToWorld(sx, sy);
    // Iterate in reverse so topmost drawn node wins
    for (let i = this.graphNodes.length - 1; i >= 0; i--) {
      const n = this.graphNodes[i];
      const dx = x - n.x, dy = y - n.y;
      if (dx * dx + dy * dy <= (n.radius + 4) * (n.radius + 4)) return n;
    }
    return null;
  };

  /* ---- Event binding ---- */

  GraphViz.prototype._bindEvents = function () {
    const self = this;
    const canvas = this.canvas;

    // --- Pointer / mouse ---
    let pointerDown = false;
    let pointerMoved = false;
    let lastPointer = { x: 0, y: 0 };
    let lastClickTime = 0;

    function getPos(e) {
      const rect = canvas.getBoundingClientRect();
      const t = e.touches ? e.touches[0] : e;
      return { x: t.clientX - rect.left, y: t.clientY - rect.top };
    }

    function onDown(e) {
      e.preventDefault();
      const pos = getPos(e);
      pointerDown = true;
      pointerMoved = false;
      lastPointer = pos;

      const hit = self._hitTest(pos.x, pos.y);
      if (hit) {
        self.dragNode = hit;
        hit.pinned = true;
        canvas.classList.add("dragging");
      } else {
        self.isPanning = true;
        self.panStart = { x: pos.x - self.offsetX * self.scale, y: pos.y - self.offsetY * self.scale };
        canvas.classList.add("dragging");
      }
    }

    function onMove(e) {
      const pos = getPos(e);

      if (self.dragNode) {
        e.preventDefault();
        pointerMoved = true;
        const world = self._screenToWorld(pos.x, pos.y);
        self.dragNode.x = world.x;
        self.dragNode.y = world.y;
        self.dragNode.vx = 0;
        self.dragNode.vy = 0;
        if (!self.simRunning) { self._draw(); }
      } else if (self.isPanning) {
        e.preventDefault();
        pointerMoved = true;
        self.offsetX = (pos.x - self.panStart.x) / self.scale;
        self.offsetY = (pos.y - self.panStart.y) / self.scale;
        if (!self.simRunning) { self._draw(); }
      } else {
        // Hover
        const hit = self._hitTest(pos.x, pos.y);
        if (hit !== self.hoveredNode) {
          self.hoveredNode = hit;
          canvas.style.cursor = hit ? "pointer" : "grab";
          if (!self.simRunning) { self._draw(); }
        }
      }
    }

    function onUp(e) {
      const pos = (e.changedTouches ? { x: e.changedTouches[0].clientX - canvas.getBoundingClientRect().left, y: e.changedTouches[0].clientY - canvas.getBoundingClientRect().top } : getPos(e));

      if (self.dragNode && !pointerMoved) {
        // It was a click, not a drag
        const now = Date.now();
        if (now - lastClickTime < 350) {
          // Double-click: re-center on this node
          self._recenter(self.dragNode.id);
        } else {
          // Single click: show info
          self._showInfo(self.dragNode);
          self.selectedNode = self.dragNode;
        }
        lastClickTime = now;
      }

      if (self.dragNode) {
        // Unpin unless it's the center node
        if (!self.dragNode.isCenter) self.dragNode.pinned = false;
        self.dragNode = null;
      }

      self.isPanning = false;
      pointerDown = false;
      canvas.classList.remove("dragging");
      if (!self.simRunning) { self._draw(); }
    }

    // Mouse events
    canvas.addEventListener("mousedown", onDown);
    canvas.addEventListener("mousemove", onMove);
    canvas.addEventListener("mouseup", onUp);
    canvas.addEventListener("mouseleave", function () {
      if (self.dragNode) {
        if (!self.dragNode.isCenter) self.dragNode.pinned = false;
        self.dragNode = null;
      }
      self.isPanning = false;
      self.hoveredNode = null;
      canvas.classList.remove("dragging");
      if (!self.simRunning) { self._draw(); }
    });

    // Touch events
    canvas.addEventListener("touchstart", onDown, { passive: false });
    canvas.addEventListener("touchmove", onMove, { passive: false });
    canvas.addEventListener("touchend", onUp);

    // Scroll to zoom
    canvas.addEventListener("wheel", function (e) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      const newScale = Math.max(0.2, Math.min(5, self.scale * delta));
      self.scale = newScale;
      if (!self.simRunning) { self._draw(); }
    }, { passive: false });

    // --- Controls ---

    // Search
    let searchDebounce = null;
    this.searchInput.addEventListener("input", function () {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(function () {
        self._onSearch(self.searchInput.value);
      }, 200);
    });
    this.searchInput.addEventListener("focus", function () {
      if (self.searchInput.value.length > 0) self._onSearch(self.searchInput.value);
    });
    document.addEventListener("click", function (e) {
      if (!self.searchResults.contains(e.target) && e.target !== self.searchInput) {
        self.searchResults.classList.remove("show");
      }
    });

    // Depth selector
    this.depthSelect.addEventListener("change", function () {
      self.hops = parseInt(self.depthSelect.value, 10);
      self._buildGraph(self.centerEntityId);
      self._startSim();
    });

    // Type filter checkboxes
    this.controlsPanel.querySelectorAll(".graph-type-cb").forEach(function (cb) {
      cb.addEventListener("change", function () {
        self._applyTypeFilter();
      });
    });

    // Reset button
    this.controlsPanel.querySelector(".graph-reset-btn").addEventListener("click", function () {
      self.typeFilter = null;
      self.controlsPanel.querySelectorAll(".graph-type-cb").forEach(function (cb) { cb.checked = true; });
      self.hops = 2;
      self.depthSelect.value = "2";
      self._buildGraph(self.centerEntityId);
      self._startSim();
    });

    // Fit-to-view button
    this.controlsPanel.querySelector(".graph-fit-btn").addEventListener("click", function () {
      self._fitToView();
    });

    // Resize
    window.addEventListener("resize", function () {
      self._resizeCanvas();
      if (!self.simRunning) { self._draw(); }
    });
  };

  /* ---- Controls logic ---- */

  GraphViz.prototype._applyTypeFilter = function () {
    var cbs = this.controlsPanel.querySelectorAll(".graph-type-cb");
    var allChecked = true;
    var filter = new Set();
    cbs.forEach(function (cb) {
      if (cb.checked) filter.add(cb.value);
      else allChecked = false;
    });
    this.typeFilter = allChecked ? null : filter;
    this._buildGraph(this.centerEntityId);
    this._startSim();
  };

  GraphViz.prototype._onSearch = function (query) {
    if (!query || query.length < 1) {
      this.searchResults.classList.remove("show");
      return;
    }
    var q = query.toLowerCase();
    var results = S().entities.filter(function (e) {
      return e.name.toLowerCase().includes(q);
    }).slice(0, 10);

    if (results.length === 0) {
      this.searchResults.classList.remove("show");
      return;
    }

    var html = "";
    var self = this;
    results.forEach(function (e) {
      var emoji = TYPE_EMOJI[e.type] || "";
      html += '<div class="graph-search-item" data-id="' + e.id + '">' + emoji + " " + e.name + "</div>";
    });
    this.searchResults.innerHTML = html;
    this.searchResults.classList.add("show");

    this.searchResults.querySelectorAll(".graph-search-item").forEach(function (el) {
      el.addEventListener("click", function () {
        var id = el.getAttribute("data-id");
        self.searchInput.value = "";
        self.searchResults.classList.remove("show");
        self._recenter(id);
      });
    });
  };

  GraphViz.prototype._recenter = function (entityId) {
    this.centerEntityId = entityId;
    this.selectedNode = null;
    this.infoPanel.classList.remove("show");
    this._buildGraph(entityId);
    this._startSim();
  };

  GraphViz.prototype._fitToView = function () {
    if (this.graphNodes.length === 0) return;
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (var i = 0; i < this.graphNodes.length; i++) {
      var n = this.graphNodes[i];
      if (n.x - n.radius < minX) minX = n.x - n.radius;
      if (n.y - n.radius < minY) minY = n.y - n.radius;
      if (n.x + n.radius > maxX) maxX = n.x + n.radius;
      if (n.y + n.radius > maxY) maxY = n.y + n.radius;
    }
    var gw = maxX - minX + 60;
    var gh = maxY - minY + 60;
    var sx = this.canvasW / gw;
    var sy = this.canvasH / gh;
    this.scale = Math.min(sx, sy, 2);
    var centerGX = (minX + maxX) / 2;
    var centerGY = (minY + maxY) / 2;
    this.offsetX = this.canvasW / 2 - centerGX;
    this.offsetY = this.canvasH / 2 - centerGY;
    if (!this.simRunning) this._draw();
  };

  /* ---- Info panel ---- */

  GraphViz.prototype._showInfo = function (node) {
    var e = node.entity;
    var meta = (S().TYPE_META || {})[e.type] || {};
    var emoji = TYPE_EMOJI[e.type] || meta.emoji || "";
    var deg = connectionCount(e.id, this.adj);
    var html =
      '<button class="gi-close">✕</button>' +
      "<h3>" + emoji + " " + e.name + "</h3>" +
      '<div class="gi-type">' + (meta.label || e.type) + "</div>" +
      '<div class="gi-summary">' + (e.summary || "") + "</div>" +
      '<div class="gi-connections">' + deg + " kết nối trong đồ thị</div>" +
      '<div class="gi-dblclick">Nhấp đúp để xem mở rộng</div>';
    this.infoPanel.innerHTML = html;
    this.infoPanel.classList.add("show");

    var self = this;
    this.infoPanel.querySelector(".gi-close").addEventListener("click", function () {
      self.infoPanel.classList.remove("show");
      self.selectedNode = null;
      if (!self.simRunning) self._draw();
    });
  };

  /* ---- Public methods ---- */

  GraphViz.prototype.expandNode = function (entityId) {
    this._addNeighbors(entityId);
  };

  GraphViz.prototype.highlightPath = function (fromId, toId) {
    var path = bfsPath(fromId, toId, this.adj);
    if (!path) {
      this.highlightedPath = null;
      this.highlightedEdges = null;
      if (!this.simRunning) this._draw();
      return null;
    }

    // Ensure all nodes on path are visible
    for (var i = 0; i < path.length; i++) {
      if (!this.nodeMap.has(path[i])) {
        this._addNeighbors(path[i]);
      }
    }

    this.highlightedPath = new Set(path);
    this.highlightedEdges = new Set();
    for (var j = 0; j < path.length - 1; j++) {
      this.highlightedEdges.add(path[j] + "::" + path[j + 1]);
    }

    if (!this.simRunning) this._draw();
    return path;
  };

  GraphViz.prototype.recenter = function (entityId) {
    this._recenter(entityId);
  };

  GraphViz.prototype.destroy = function () {
    if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
    this.simRunning = false;
    this.container.innerHTML = "";
  };

  /* ================================================================
   *  PUBLIC API (window-level)
   * ================================================================ */

  var currentInstance = null;

  /**
   * initGraph(containerId, centerEntityId)
   * Mount the knowledge graph into a container, centered on the given entity.
   */
  function initGraph(containerId, centerEntityId) {
    var container = document.getElementById(containerId);
    if (!container) {
      console.error("[graph] Container not found: " + containerId);
      return null;
    }
    if (!window.Store) {
      console.error("[graph] window.Store not available. Load store.js first.");
      return null;
    }

    // Destroy previous instance if any
    if (currentInstance) currentInstance.destroy();

    currentInstance = new GraphViz(container, centerEntityId);
    return currentInstance;
  }

  /**
   * expandNode(entityId) — add an entity's neighbors to the current view.
   */
  function expandNode(entityId) {
    if (!currentInstance) { console.warn("[graph] No graph instance. Call initGraph first."); return; }
    currentInstance.expandNode(entityId);
  }

  /**
   * highlightPath(fromId, toId) — highlight shortest path between two entities.
   * Returns the path array of IDs, or null if unreachable.
   */
  function highlightPath(fromId, toId) {
    if (!currentInstance) { console.warn("[graph] No graph instance. Call initGraph first."); return null; }
    return currentInstance.highlightPath(fromId, toId);
  }

  /**
   * getVisibleGraphPublic(entityId, hops) — extract subgraph data without rendering.
   * Returns { nodes: Set<id>, edges: [{from, to, type}] }
   */
  function getVisibleGraphPublic(entityId, hops) {
    if (!window.Store) { console.error("[graph] window.Store not available."); return null; }
    var adj = buildAdj();
    return getVisibleGraph(entityId, hops || 2, adj, null);
  }

  // Export to window
  window.initGraph = initGraph;
  window.expandNode = expandNode;
  window.highlightPath = highlightPath;
  window.getVisibleGraph = getVisibleGraphPublic;
})();
