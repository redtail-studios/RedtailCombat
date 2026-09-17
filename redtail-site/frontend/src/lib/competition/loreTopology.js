/*
 * Lore evidence topology renderer.
 * Adapted from the user-owned Lore prototype assets/topology.js (2026-09-17).
 * https://redtail-lore-lab.redtail-stud-2691.chatgpt.site/redtail-studios/v1/
 * Rendering geometry retained; all nodes and relationships now come from the saved game analysis.
 * Geometry is schematic. Only feature/comparable links encode relationships.
 */
export function createLoreTopology(canvas, { model, onSelect, onHover, colors = {}, variant = 'comparison' }) {
  if (!canvas || typeof canvas.getContext !== "function") {
    throw new TypeError("createLoreTopology requires a canvas element");
  }

  const ctx = canvas.getContext("2d", { alpha: false });
  if (!ctx) throw new Error("2D canvas is not available");

  const defaults = {
    background: "#05090b",
    backgroundLift: "#0a1717",
    glow: "#35d6a0",
    grid: "#66847a",
    wire: "#78958a",
    relation: "#b6d4c8",
    core: "#f2f5ec",
    feature: "#78efc0",
    comparable: "#d7b968",
    selected: "#ffe093",
    text: "#e6efe9",
    muted: "#789087",
  };

  let palette = Object.assign({}, defaults, colors || {});
  const featureNodes = model.features.map(node => ({ ...node, type: "feature" }));
  const comparableNodes = model.comparables.map(node => ({ ...node, type: "comparable" }));
  const coreNode = { ...model.core, type: "core" };
  const nodes = [coreNode, ...featureNodes, ...comparableNodes];
  const nodeById = new Map(nodes.map(node => [node.id, node]));
  featureNodes.forEach(feature => {
    feature.links = comparableNodes.filter(game => game.links.includes(feature.id)).map(game => game.id);
  });
  const coreEdges = featureNodes.map(feature => ({ from: coreNode.id, to: feature.id, type: "core" }));
  // No invented feature links for records whose shared traits cannot be extracted.
  comparableNodes.filter(game => variant === 'discovery' || !game.links.length).forEach(game => coreEdges.push({ from: coreNode.id, to: game.id, type: "core" }));
  const relationEdges = comparableNodes.flatMap(game => game.links.map(id => ({ from: id, to: game.id, type: "evidence" })));
  const scaffoldPairs = featureNodes.flatMap((a, i) => featureNodes.slice(i + 1).filter(b => a.p.some((v, axis) => v && b.p[axis] === 0)).map(b => [a.id, b.id]));

  const orbitSpecs = [
    { rx: 1.2, ry: 1.2, tiltX: 0.2, tiltY: 0.55, tiltZ: -0.16 },
    { rx: 1.62, ry: 1.62, tiltX: 1.06, tiltY: -0.12, tiltZ: 0.32 },
    { rx: 1.98, ry: 1.98, tiltX: 0.52, tiltY: 1.12, tiltZ: -0.45 },
  ];

  const reducedMotionQuery = typeof window !== "undefined" && window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)")
    : null;

  let reducedMotion = reducedMotionQuery ? reducedMotionQuery.matches : false;
  let motionRequested = false;
  let visible = true;
  let selectedId = null;
  let width = 580;
  let height = 350;
  let pixelRatio = 1;
  let rotationX = -0.32;
  let rotationY = 0.58;
  let rotationZ = -0.05;
  let projectedNodes = [];
  let animationFrame = 0;
  let lastTime = 0;
  let destroyed = false;
  let resizeObserver = null;
  let drag = null;
  let pointerMoved = false;
  let hoverId = null;

  canvas.setAttribute(
    "aria-label",
    variant === 'discovery' ? 'Rotating globe of trending Steam games. Drag to explore. The game list below provides keyboard access.' : `Interactive comparison map for ${model.core.label}. Drag to rotate; use the game buttons below for keyboard selection.`
  );
  canvas.style.touchAction = "pan-y";
  canvas.style.cursor = "grab";

  function effectiveMotion() {
    return motionRequested && !reducedMotion && visible;
  }

  function rotateLocal(point, rx, ry, rz) {
    let x = point[0];
    let y = point[1];
    let z = point[2];

    const cx = Math.cos(rx);
    const sx = Math.sin(rx);
    const cy = Math.cos(ry);
    const sy = Math.sin(ry);
    const cz = Math.cos(rz);
    const sz = Math.sin(rz);

    const y1 = y * cx - z * sx;
    const z1 = y * sx + z * cx;
    const x2 = x * cy + z1 * sy;
    const z2 = -x * sy + z1 * cy;
    const x3 = x2 * cz - y1 * sz;
    const y3 = x2 * sz + y1 * cz;
    return [x3, y3, z2];
  }

  function rotateScene(point) {
    return rotateLocal(point, rotationX, rotationY, rotationZ);
  }

  function project(point) {
    const rotated = rotateScene(point);
    const camera = 4.7;
    const perspective = camera / Math.max(2.35, camera - rotated[2]);
    const scale = Math.min(width * 0.86, height) * (width >= 600 ? 0.305 : 0.245);
    return {
      x: width * 0.5 + rotated[0] * scale * perspective,
      y: height * 0.5 + rotated[1] * scale * perspective,
      z: rotated[2],
      scale: perspective,
    };
  }

  function alphaStroke(color, alpha, lineWidth) {
    ctx.strokeStyle = color;
    ctx.globalAlpha = alpha;
    ctx.lineWidth = lineWidth;
  }

  function alphaFill(color, alpha) {
    ctx.fillStyle = color;
    ctx.globalAlpha = alpha;
  }

  function drawBackground() {
    const gradient = ctx.createRadialGradient(
      width * 0.5,
      height * 0.46,
      8,
      width * 0.5,
      height * 0.48,
      Math.max(width, height) * 0.72
    );
    gradient.addColorStop(0, palette.backgroundLift);
    gradient.addColorStop(0.58, palette.background);
    gradient.addColorStop(1, palette.background);
    ctx.globalAlpha = 1;
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    const glow = ctx.createRadialGradient(
      width * 0.5,
      height * 0.5,
      0,
      width * 0.5,
      height * 0.5,
      Math.min(width, height) * 0.44
    );
    glow.addColorStop(0, palette.glow);
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.globalAlpha = 0.075;
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, width, height);
    ctx.globalAlpha = 1;
  }

  function drawProjectedGrid() {
    ctx.save();
    for (let gx = -3.25; gx <= 3.25; gx += 0.32) {
      for (let gz = -3.25; gz <= 3.25; gz += 0.32) {
        const p = project([gx, 1.62, gz]);
        if (p.x < 0 || p.x > width || p.y < 0 || p.y > height) continue;
        const radial = Math.sqrt(gx * gx + gz * gz) / 4.6;
        const fade = Math.max(0, 1 - radial);
        alphaFill(palette.grid, 0.05 + fade * 0.1);
        ctx.beginPath();
        ctx.arc(p.x, p.y, Math.max(0.35, p.scale * 0.58), 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.restore();
  }

  function orbitPoint(spec, angle) {
    const local = [
      Math.cos(angle) * spec.rx,
      Math.sin(angle) * spec.ry,
      0,
    ];
    return rotateLocal(local, spec.tiltX, spec.tiltY, spec.tiltZ);
  }

  function drawOrbits(time) {
    orbitSpecs.forEach((spec, orbitIndex) => {
      ctx.save();
      ctx.setLineDash([1.5, 6 + orbitIndex * 1.5]);
      ctx.lineDashOffset = effectiveMotion() ? -(time * 0.006 + orbitIndex * 9) : 0;
      for (let i = 0; i < 96; i += 1) {
        const a0 = (i / 96) * Math.PI * 2;
        const a1 = ((i + 1) / 96) * Math.PI * 2;
        const world0 = orbitPoint(spec, a0);
        const world1 = orbitPoint(spec, a1);
        const p0 = project(world0);
        const p1 = project(world1);
        const depth = Math.max(-1.4, Math.min(1.4, (p0.z + p1.z) * 0.5));
        alphaStroke(palette.wire, 0.2 + (depth + 1.4) * 0.08, 0.65);
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p1.x, p1.y);
        ctx.stroke();
      }
      ctx.restore();
    });
  }

  function focusDirection() {
    if (!selectedId || selectedId === coreNode.id) return null;
    const selected = nodeById.get(selectedId);
    if (!selected) return null;

    let vector;
    if (selected.type === "feature") {
      vector = selected.p.slice();
    } else {
      vector = selected.links.reduce(
        (sum, featureId) => {
          const feature = nodeById.get(featureId);
          return feature
            ? [sum[0] + feature.p[0], sum[1] + feature.p[1], sum[2] + feature.p[2]]
            : sum;
        },
        [0, 0, 0]
      );
    }

    const length = Math.sqrt(
      vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2]
    );
    return length > 0.001
      ? [vector[0] / length, vector[1] / length, vector[2] / length]
      : null;
  }

  function structuralPoint(longitude, latitude, focus) {
    const cosLatitude = Math.cos(latitude);
    const normal = [
      cosLatitude * Math.cos(longitude),
      Math.sin(latitude),
      cosLatitude * Math.sin(longitude),
    ];
    const ridge =
      1 +
      Math.sin(longitude * 5 + latitude * 2) * 0.055 +
      Math.cos(latitude * 7 - longitude * 2) * 0.035;
    const point = [
      normal[0] * 1.18 * ridge,
      normal[1] * 0.94 * ridge,
      normal[2] * 1.08 * ridge,
    ];

    if (focus) {
      const alignment = Math.max(
        0,
        normal[0] * focus[0] + normal[1] * focus[1] + normal[2] * focus[2]
      );
      const deformation = Math.pow(alignment, 5) * 0.34;
      point[0] += focus[0] * deformation;
      point[1] += focus[1] * deformation;
      point[2] += focus[2] * deformation;
    }
    return point;
  }

  function drawMeshSegment(worldA, worldB, color, baseAlpha) {
    const a = project(worldA);
    const b = project(worldB);
    const depth = Math.max(-1.5, Math.min(1.5, (a.z + b.z) * 0.5));
    const alpha = Math.min(0.42, baseAlpha + (depth + 1.5) * 0.055);
    alphaStroke(color, alpha, 0.65);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  function drawStructuralMesh() {
    const focus = focusDirection();
    const meridians = variant === 'discovery' ? 12 : 24;
    const latitudeSamples = variant === 'discovery' ? 20 : 30;
    const parallelBands = variant === 'discovery' ? 8 : 13;
    const longitudeSamples = variant === 'discovery' ? 32 : 48;

    ctx.save();
    ctx.setLineDash([]);

    for (let meridian = 0; meridian < meridians; meridian += 1) {
      const longitude = (meridian / meridians) * Math.PI * 2;
      let previous = structuralPoint(longitude, -Math.PI * 0.5, focus);
      for (let sample = 1; sample <= latitudeSamples; sample += 1) {
        const latitude = -Math.PI * 0.5 + (sample / latitudeSamples) * Math.PI;
        const current = structuralPoint(longitude, latitude, focus);
        drawMeshSegment(previous, current, palette.wire, 0.1);
        previous = current;
      }
    }

    for (let band = 1; band < parallelBands; band += 1) {
      const latitude = -Math.PI * 0.5 + (band / parallelBands) * Math.PI;
      let previous = structuralPoint(0, latitude, focus);
      for (let sample = 1; sample <= longitudeSamples; sample += 1) {
        const longitude = (sample / longitudeSamples) * Math.PI * 2;
        const current = structuralPoint(longitude, latitude, focus);
        drawMeshSegment(previous, current, palette.muted, 0.085);
        previous = current;
      }
    }
    ctx.restore();
  }

  function projectedFor(id) {
    const entry = projectedNodes.find((item) => item.node.id === id);
    return entry ? entry.screen : null;
  }

  function selectionSet() {
    if (!selectedId || selectedId === coreNode.id) return null;
    const selected = nodeById.get(selectedId);
    const set = new Set([coreNode.id, selectedId]);
    if (!selected) return set;
    if (selected.type === "feature") {
      selected.links.forEach((id) => set.add(id));
    } else if (selected.type === "comparable") {
      selected.links.forEach((id) => set.add(id));
    }
    return set;
  }

  function edgeIsSelected(edge) {
    if (!selectedId || selectedId === coreNode.id) return false;
    return edge.from === selectedId || edge.to === selectedId;
  }

  function drawScaffold(activeSet) {
    ctx.save();
    ctx.setLineDash([2, 5]);
    scaffoldPairs.forEach(([from, to]) => {
      const a = projectedFor(from);
      const b = projectedFor(to);
      if (!a || !b) return;
      const dimmed = activeSet && (!activeSet.has(from) || !activeSet.has(to));
      alphaStroke(palette.wire, dimmed ? 0.27 : 0.40, 0.9);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    });
    ctx.restore();
  }

  function drawCoreEdges(activeSet) {
    ctx.save();
    ctx.setLineDash([]);
    coreEdges.forEach((edge) => {
      const a = projectedFor(edge.from);
      const b = projectedFor(edge.to);
      if (!a || !b) return;
      const active = !activeSet || activeSet.has(edge.to);
      alphaStroke(palette.wire, variant === 'discovery' ? (activeSet && active ? .55 : .1) : (active ? .78 : .52), variant === 'discovery' ? .7 : (active ? 1.5 : 1.1));
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    });
    ctx.restore();
  }

  function curveControl(a, b, edgeIndex) {
    const mx = (a.x + b.x) * 0.5;
    const my = (a.y + b.y) * 0.5;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const length = Math.max(1, Math.sqrt(dx * dx + dy * dy));
    const direction = edgeIndex % 2 === 0 ? 1 : -1;
    const bend = Math.min(15, length * 0.08) * direction;
    return {
      x: mx - (dy / length) * bend,
      y: my + (dx / length) * bend,
    };
  }

  function drawRelations(activeSet) {
    relationEdges.forEach((edge, index) => {
      const a = projectedFor(edge.from);
      const b = projectedFor(edge.to);
      if (!a || !b) return;
      const highlighted = edgeIsSelected(edge);
      const active = !activeSet || (activeSet.has(edge.from) && activeSet.has(edge.to));
      const control = curveControl(a, b, index);

      ctx.save();
      ctx.setLineDash([]);
      alphaStroke(
        highlighted ? palette.selected : palette.relation,
        highlighted ? 1 : variant === 'discovery' ? (active ? .42 : .22) : active ? .8 : .58,
        highlighted ? 2.6 : 1.45
      );
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.quadraticCurveTo(control.x, control.y, b.x, b.y);
      ctx.stroke();

      if (active) {
        const t = 0.5;
        const mt = 1 - t;
        const px = mt * mt * a.x + 2 * mt * t * control.x + t * t * b.x;
        const py = mt * mt * a.y + 2 * mt * t * control.y + t * t * b.y;
        alphaFill(highlighted ? palette.selected : palette.relation, highlighted ? 0.95 : 0.5);
        ctx.beginPath();
        ctx.arc(px, py, highlighted ? 1.8 : 1.1, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    });
  }

  function drawFocusOrbit(screen, time) {
    const phase = effectiveMotion() ? (time % 1450) / 1450 : 0.38;
    const radius = 10 + phase * 16;
    ctx.save();
    alphaStroke(palette.selected, (1 - phase) * 0.58, 0.9);
    ctx.beginPath();
    ctx.ellipse(screen.x, screen.y, radius, radius * 0.42, -0.32, 0, Math.PI * 2);
    ctx.stroke();
    alphaStroke(palette.selected, 0.42, 0.75);
    ctx.beginPath();
    ctx.ellipse(screen.x, screen.y, 10.5, 4.2, 0.68, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  function nodeAlpha(node, activeSet) {
    if (variant === 'discovery' && node.type !== 'core' && node.id !== selectedId) return Math.max(.3, Math.min(1, .6 + project(node.p).z * .32));
    if (!activeSet || activeSet.has(node.id)) return 1;
    return node.type === "core" ? 1 : 0.85;
  }

  function drawCore(screen, alpha) {
    ctx.save();
    const halo = ctx.createRadialGradient(screen.x, screen.y, 0, screen.x, screen.y, 28);
    halo.addColorStop(0, palette.core);
    halo.addColorStop(0.16, palette.glow);
    halo.addColorStop(1, "rgba(0,0,0,0)");
    ctx.globalAlpha = alpha * 0.38;
    ctx.fillStyle = halo;
    ctx.beginPath();
    ctx.arc(screen.x, screen.y, 28, 0, Math.PI * 2);
    ctx.fill();

    alphaStroke(palette.core, alpha * 0.78, 0.8);
    ctx.beginPath();
    ctx.arc(screen.x, screen.y, 9, 0, Math.PI * 2);
    ctx.stroke();
    alphaStroke(palette.glow, alpha * 0.7, 0.65);
    ctx.beginPath();
    ctx.arc(screen.x, screen.y, 13.5, 0, Math.PI * 2);
    ctx.stroke();
    alphaFill(palette.core, alpha);
    ctx.beginPath();
    ctx.arc(screen.x, screen.y, 3.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function drawFeature(screen, node, alpha, selected) {
    const radius = 5.3 * Math.max(0.84, screen.scale);
    ctx.save();
    if (selected) drawFocusOrbit(screen, performance.now());
    alphaStroke(selected ? palette.selected : palette.feature, alpha * 0.82, selected ? 1.3 : 0.85);
    ctx.beginPath();
    ctx.arc(screen.x, screen.y, radius + 2.3, 0, Math.PI * 2);
    ctx.stroke();
    alphaFill(selected ? palette.selected : palette.feature, alpha);
    ctx.beginPath();
    ctx.arc(screen.x, screen.y, selected ? radius * 0.72 : radius * 0.52, 0, Math.PI * 2);
    ctx.fill();

    alphaStroke(selected ? palette.selected : palette.feature, alpha * 0.5, 0.65);
    for (let i = 0; i < 4; i += 1) {
      const angle = i * Math.PI * 0.5;
      const inner = radius + 4.2;
      const outer = inner + 3.4;
      ctx.beginPath();
      ctx.moveTo(screen.x + Math.cos(angle) * inner, screen.y + Math.sin(angle) * inner);
      ctx.lineTo(screen.x + Math.cos(angle) * outer, screen.y + Math.sin(angle) * outer);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawComparable(screen, node, alpha, selected) {
    const radius = (selected ? 5.8 : 4.6) * Math.max(0.86, screen.scale);
    ctx.save();
    if (selected) drawFocusOrbit(screen, performance.now());
    ctx.translate(screen.x, screen.y);
    ctx.rotate(Math.PI * 0.25);
    alphaStroke(selected ? palette.selected : palette.comparable, alpha * 0.9, selected ? 1.25 : 0.8);
    ctx.strokeRect(-radius, -radius, radius * 2, radius * 2);
    alphaFill(selected ? palette.selected : palette.comparable, alpha * 0.9);
    ctx.fillRect(-1.45, -1.45, 2.9, 2.9);
    ctx.restore();
  }

  function intersects(a, b) {
    return !(
      a.x + a.w + 3 < b.x ||
      b.x + b.w + 3 < a.x ||
      a.y + a.h + 2 < b.y ||
      b.y + b.h + 2 < a.y
    );
  }

  function placeLabels(activeSet) {
    const occupied = [];
    projectedNodes.forEach(entry => { entry.labelBox = null; });
    const ordered = projectedNodes.slice().sort((a, b) => {
      const aPriority = a.node.id === selectedId ? 3 : a.node.type === "feature" ? 2 : 1;
      const bPriority = b.node.id === selectedId ? 3 : b.node.type === "feature" ? 2 : 1;
      return bPriority - aPriority || b.screen.z - a.screen.z;
    });

    ordered.forEach((entry) => {
      const node = entry.node;
      const screen = entry.screen;
      const active = !activeSet || activeSet.has(node.id);
      const alpha = nodeAlpha(node, activeSet);
      const isCore = node.type === "core";
      const isFeature = node.type === "feature";
      if (variant === "discovery" && !isCore && node.id !== selectedId && screen.z < (width < 520 ? .2 : -.15)) return;
      // Small screens show the selected relationship; controls retain every mechanic.
      if (width < 520 && isFeature && selectedId && !active) return;
      const fontSize = width < 520 ? (isCore ? 12 : 10) : (isCore ? 14 : 12);
      const weight = isCore || node.id === selectedId ? 500 : 400;
      ctx.font = `${weight} ${fontSize}px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`;
      const label = node.shortLabel || node.label;
      const textWidth = Math.ceil(ctx.measureText(label).width);
      const labelHeight = fontSize + 4;
      let sign = screen.x >= width * 0.5 ? 1 : -1;
      if (isCore) sign = 1;
      let x = sign > 0 ? screen.x + (isCore ? 15 : 10) : screen.x - textWidth - 10;
      let y = screen.y - labelHeight * 0.52;
      x = Math.max(7, Math.min(width - textWidth - 7, x));
      const labelMinY = 60;
      const labelMaxY = Math.max(labelMinY, height - labelHeight - 40);
      y = Math.max(labelMinY, Math.min(labelMaxY, y));

      let box = { x, y, w: textWidth, h: labelHeight };
      for (let attempt = 0; attempt < 7; attempt += 1) {
        if (!occupied.some((other) => intersects(box, other))) break;
        const direction = attempt % 2 === 0 ? 1 : -1;
        y += direction * (Math.floor(attempt / 2) + 1) * 8;
        y = Math.max(labelMinY, Math.min(labelMaxY, y));
        box = { x, y, w: textWidth, h: labelHeight };
      }
      if (variant === 'discovery') {
        const originY = Math.max(labelMinY, Math.min(labelMaxY, screen.y - labelHeight * .52));
        const offsets = [0, 18, -18, 36, -36, 54, -54, 72, -72, 90, -90];
        const available = offsets.map(offset => ({ x, y: Math.max(labelMinY, Math.min(labelMaxY, originY + offset)), w: textWidth, h: labelHeight })).find(candidate => !occupied.some(other => intersects(candidate, other)));
        if (!available && !isCore && node.id !== selectedId) return;
        if (available) { box = available; y = box.y; }
      }
      occupied.push(box);

      ctx.save();
      const selected = node.id === selectedId;
      const labelColor = selected
        ? palette.selected
        : isCore
          ? palette.core
          : isFeature
            ? palette.text
            : palette.comparable;
      alphaStroke(labelColor, alpha * (active ? 0.36 : 0.12), 0.55);
      ctx.beginPath();
      ctx.moveTo(screen.x + sign * 5, screen.y);
      ctx.lineTo(sign > 0 ? x - 3 : x + textWidth + 3, y + labelHeight * 0.48);
      ctx.stroke();

      ctx.shadowColor = palette.background;
      ctx.shadowBlur = 5;
      ctx.textBaseline = "top";
      alphaFill(labelColor, alpha);
      ctx.fillText(label, x, y);
      entry.labelBox = box;
      ctx.restore();
    });
  }

  function drawHud() {
    ctx.save();
    alphaStroke(palette.muted, 0.34, 0.6);
    ctx.beginPath();
    ctx.moveTo(12, 12);
    ctx.lineTo(29, 12);
    ctx.moveTo(12, 12);
    ctx.lineTo(12, 29);
    ctx.moveTo(width - 12, 12);
    ctx.lineTo(width - 29, 12);
    ctx.moveTo(width - 12, 12);
    ctx.lineTo(width - 12, 29);
    ctx.stroke();
    ctx.restore();
  }

  function render(time) {
    if (destroyed) return;
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    drawBackground();
    drawProjectedGrid();
    drawOrbits(time || 0);
    drawStructuralMesh();
    if (variant === 'discovery') {
      for (let i = 0; i < 600; i++) {
        const y = 1 - i / 599 * 2;
        const ring = Math.sqrt(1 - y * y);
        const angle = i * Math.PI * (3 - Math.sqrt(5));
        const point = project([Math.cos(angle) * ring * 1.18, y * .94, Math.sin(angle) * ring * 1.08]);
        alphaFill(palette.feature, point.z > 0 ? .16 + point.z * .23 : .055);
        ctx.beginPath(); ctx.arc(point.x, point.y, point.z > 0 ? 1 : .6, 0, Math.PI * 2); ctx.fill();
      }
    }

    projectedNodes = nodes.map((node) => ({ node, screen: project(node.p) }));
    const activeSet = selectionSet();

    drawScaffold(activeSet);
    drawCoreEdges(activeSet);
    drawRelations(activeSet);

    projectedNodes
      .slice()
      .sort((a, b) => a.screen.z - b.screen.z)
      .forEach((entry) => {
        const alpha = nodeAlpha(entry.node, activeSet);
        const selected = entry.node.id === selectedId;
        if (entry.node.type === "core") drawCore(entry.screen, alpha);
        else if (entry.node.type === "feature") drawFeature(entry.screen, entry.node, alpha, selected);
        else drawComparable(entry.screen, entry.node, alpha, selected);
      });

    placeLabels(activeSet);
    drawHud();
    ctx.globalAlpha = 1;
  }

  function nearestAt(x,y){
    const labelHit=projectedNodes.find(e=>e.labelBox&&x>=e.labelBox.x&&x<=e.labelBox.x+e.labelBox.w&&y>=e.labelBox.y&&y<=e.labelBox.y+e.labelBox.h);
    if(labelHit)return labelHit;
    return projectedNodes.filter(e=>Math.hypot(e.screen.x-x,e.screen.y-y)<=23).sort((a,b)=>Math.hypot(a.screen.x-x,a.screen.y-y)-Math.hypot(b.screen.x-x,b.screen.y-y))[0]||null;
  }

  function frame(time) {
    if (destroyed) return;
    if (variant === 'discovery' && lastTime && time - lastTime < 32) { animationFrame = effectiveMotion() ? requestAnimationFrame(frame) : 0; return; }
    const delta = lastTime ? Math.min(48, time - lastTime) : 16;
    lastTime = time;
    if (effectiveMotion() && !drag && !hoverId) rotationY += delta * 0.000055;
    render(time);
    animationFrame = effectiveMotion() ? requestAnimationFrame(frame) : 0;
  }

  function requestRender() {
    if (destroyed) return;
    if (effectiveMotion()) {
      if (!animationFrame) animationFrame = requestAnimationFrame(frame);
    } else {
      if (animationFrame) cancelAnimationFrame(animationFrame);
      animationFrame = 0;
      render(performance.now());
    }
  }

  function resize() {
    if (destroyed) return;
    const rect = canvas.getBoundingClientRect();
    const nextWidth = Math.max(1, Math.round(rect.width || 580));
    const nextHeight = Math.max(1, Math.round(rect.height || 350));
    const nextRatio = Math.min(2.25, Math.max(1, window.devicePixelRatio || 1));
    width = nextWidth;
    height = nextHeight;
    pixelRatio = nextRatio;
    const backingWidth = Math.round(width * pixelRatio);
    const backingHeight = Math.round(height * pixelRatio);
    if (canvas.width !== backingWidth || canvas.height !== backingHeight) {
      canvas.width = backingWidth;
      canvas.height = backingHeight;
    }
    requestRender();
  }

  function publicNode(node) {
    return Object.freeze({
      id: node.id,
      type: node.type,
      label: node.label,
      links: Object.freeze((node.links || featureNodes.map((feature) => feature.id)).slice()),
    });
  }

  function selectNearest(x, y) {
    const hit = nearestAt(x, y);
    if (!hit) return;
    selectedId = hit.node.id;
    requestRender();
    if (typeof onSelect === "function") onSelect(publicNode(hit.node));
  }

  function pointerPosition(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  }

  function onPointerDown(event) {
    if (destroyed || event.button !== 0) return;
    onPointerLeave();
    const point = pointerPosition(event);
    drag = {
      id: event.pointerId,
      x: point.x,
      y: point.y,
      startX: point.x,
      startY: point.y,
      rotationX,
      rotationY,
    };
    pointerMoved = false;
    canvas.setPointerCapture(event.pointerId);
    canvas.style.cursor = "grabbing";
  }

  function onPointerMove(event) {
    if (!drag || drag.id !== event.pointerId) {
      const point = pointerPosition(event);
      const hovering = nearestAt(point.x,point.y);
      canvas.style.cursor = hovering ? "pointer" : "grab";
      if(hovering&&hoverId!==hovering.node.id){hoverId=hovering.node.id;if(typeof onHover==='function')onHover(publicNode(hovering.node),point);}
      if(!hovering)onPointerLeave();
      return;
    }
    const point = pointerPosition(event);
    const dx = point.x - drag.x;
    const dy = point.y - drag.y;
    if (Math.abs(point.x - drag.startX) + Math.abs(point.y - drag.startY) > 4) {
      pointerMoved = true;
    }
    rotationY = drag.rotationY + dx * 0.008;
    rotationX = Math.max(-1.25, Math.min(1.25, drag.rotationX + dy * 0.006));
    requestRender();
  }

  function onPointerUp(event) {
    if (!drag || drag.id !== event.pointerId) return;
    const point = pointerPosition(event);
    try {
      canvas.releasePointerCapture(event.pointerId);
    } catch (_) {
      // Pointer capture may already be released if the pointer left the document.
    }
    drag = null;
    canvas.style.cursor = "grab";
    if (!pointerMoved) selectNearest(point.x, point.y);
    requestRender();
  }

  function onPointerCancel(event) {
    onPointerLeave();
    if (drag && drag.id === event.pointerId) {
      drag = null;
      canvas.style.cursor = "grab";
      requestRender();
    }
  }

  function onPointerLeave(){
    hoverId=null;
    if(typeof onHover==='function')onHover(null);
  }

  function onReducedMotionChange(event) {
    reducedMotion = event.matches;
    lastTime = 0;
    requestRender();
  }

  function setFocus(featureId) {
    if (featureId == null || featureId === "") {
      selectedId = null;
    } else {
      const node = nodeById.get(featureId);
      if (!node) {
        throw new RangeError(`Unknown comparison node: ${featureId}`);
      }
      selectedId = featureId;
    }
    requestRender();
  }

  function reset() {
    rotationX = -0.32; rotationY = 0.58; rotationZ = -0.05; selectedId = null; requestRender();
  }
  function rotate(dx, dy = 0) {
    rotationY += dx; rotationX = Math.max(-1.25, Math.min(1.25, rotationX + dy)); requestRender();
  }
  function setVisible(value) { visible = value; lastTime = 0; requestRender(); }

  function setAppearance(nextColors) {
    palette = Object.assign({}, palette, nextColors || {});
    requestRender();
  }

  function setMotion(enabled) {
    motionRequested = Boolean(enabled);
    lastTime = 0;
    requestRender();
  }

  function destroy() {
    if (destroyed) return;
    destroyed = true;
    if (animationFrame) cancelAnimationFrame(animationFrame);
    animationFrame = 0;
    canvas.removeEventListener("pointerdown", onPointerDown);
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerup", onPointerUp);
    canvas.removeEventListener("pointercancel", onPointerCancel);
    canvas.removeEventListener("pointerleave", onPointerLeave);
    canvas.removeEventListener("lostpointercapture", onPointerCancel);
    if (resizeObserver) resizeObserver.disconnect();
    else window.removeEventListener("resize", resize);
    if (reducedMotionQuery) {
      if (typeof reducedMotionQuery.removeEventListener === "function") {
        reducedMotionQuery.removeEventListener("change", onReducedMotionChange);
      } else if (typeof reducedMotionQuery.removeListener === "function") {
        reducedMotionQuery.removeListener(onReducedMotionChange);
      }
    }
  }

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerCancel);
  canvas.addEventListener("pointerleave", onPointerLeave);
  canvas.addEventListener("lostpointercapture", onPointerCancel);

  if (typeof ResizeObserver !== "undefined") {
    resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
  } else {
    window.addEventListener("resize", resize, { passive: true });
  }
  if (reducedMotionQuery) {
    if (typeof reducedMotionQuery.addEventListener === "function") {
      reducedMotionQuery.addEventListener("change", onReducedMotionChange);
    } else if (typeof reducedMotionQuery.addListener === "function") {
      reducedMotionQuery.addListener(onReducedMotionChange);
    }
  }

  resize();

  return Object.freeze({
    reset,
    rotate,
    setVisible,
    setFocus,
    setAppearance,
    setMotion,
    resize,
    destroy,
  });
}
