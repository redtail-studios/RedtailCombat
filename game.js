// ================================================================
//  REDTAIL BATTLE  ·  iOS Edition
//  Controls: WASD / Arrows = Move   SPACE = Punch   X or K = Kick
//            ENTER = Start / Retry
// ================================================================

const canvas = document.getElementById('gameCanvas');
const ctx    = canvas.getContext('2d');

// iPhone 14 logical resolution
const VW = 390;
const VH = 844;
canvas.width  = VW;
canvas.height = VH;

// iOS system font stack
const FONT = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', Arial";

// Arena bounds (below status bar + HUD card, above controls strip)
const ARENA = { x: 10, y: 118, w: 370, h: 640 };

// Fighters are drawn at 72 % of the "design" size (portrait space)
const CS = 0.72;

// ── Colour palettes ──────────────────────────────────────────────
const PAL = {
  orange: { primary:'#e85c14', mid:'#c04010', dark:'#6a1e04', light:'#ff9a60',
            visor:'#00e8ff', glow:'rgba(255,130,40,0.7)', hitGlow:'#ff7030' },
  blue:   { primary:'#2878e0', mid:'#1a4fa8', dark:'#0a1e58', light:'#72aeff',
            visor:'#00ffc0', glow:'rgba(40,120,255,0.7)', hitGlow:'#50a0ff' },
};

// iOS system colours
const IOS = {
  green:  '#34C759',
  orange: '#FF9500',
  red:    '#FF3B30',
  blue:   '#007AFF',
};

// ================================================================
//  Helpers
// ================================================================
function rr(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y,       x + w, y + r,     r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h,   x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x,      y + h,  x, y + h - r,     r);
  ctx.lineTo(x,     y + r);
  ctx.arcTo(x,      y,      x + r, y,          r);
  ctx.closePath();
}

// ================================================================
//  Particles
// ================================================================
const particles = [];

function spawnHit(x, y, color, n = 18) {
  for (let i = 0; i < n; i++) {
    const a = Math.random() * Math.PI * 2;
    const s = 2.5 + Math.random() * 6;
    particles.push({ x, y, vx: Math.cos(a)*s, vy: Math.sin(a)*s - 2,
      life: 1, decay: 0.04 + Math.random() * 0.03,
      r: 2 + Math.random() * 4, color });
  }
}

function spawnDust(x, y) {
  for (let i = 0; i < 2; i++)
    particles.push({ x: x + (Math.random()-0.5)*16, y,
      vx: (Math.random()-0.5)*1.2, vy: -Math.random()*1.4,
      life: 1, decay: 0.07, r: 3 + Math.random()*4,
      color: 'rgba(160,210,100,0.45)' });
}

function updateParticles() {
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.x += p.vx; p.y += p.vy; p.vy += 0.22; p.vx *= 0.95;
    p.life -= p.decay;
    if (p.life <= 0) particles.splice(i, 1);
  }
}

function drawParticles() {
  particles.forEach(p => {
    ctx.save();
    ctx.globalAlpha = Math.max(0, p.life);
    ctx.shadowColor = p.color; ctx.shadowBlur = 7;
    ctx.fillStyle = p.color;
    ctx.beginPath(); ctx.arc(p.x, p.y, p.r * p.life, 0, Math.PI*2); ctx.fill();
    ctx.restore();
  });
}

// ================================================================
//  Screen Shake
// ================================================================
let shakeAmt = 0, shakeX = 0, shakeY = 0;

function triggerShake(v) { shakeAmt = Math.max(shakeAmt, v); }

function updateShake() {
  if (shakeAmt > 0.5) {
    shakeX = (Math.random()-0.5) * shakeAmt * 2;
    shakeY = (Math.random()-0.5) * shakeAmt * 2;
    shakeAmt *= 0.76;
  } else { shakeAmt = 0; shakeX = 0; shakeY = 0; }
}

// ================================================================
//  iOS Status Bar
// ================================================================
function drawStatusBar() {
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, VW, 54);

  // Dynamic Island  ─  black pill
  ctx.fillStyle = '#000';
  rr(VW/2 - 60, 11, 120, 34, 17); ctx.fill();

  // Time  (left, clear of the island)
  ctx.font = `bold 15px ${FONT}`;
  ctx.fillStyle = '#fff';
  ctx.textAlign = 'left';
  ctx.fillText('9:41', 26, 36);

  // Signal bars
  for (let i = 0; i < 4; i++) {
    const bh = 4 + i * 3.2;
    ctx.fillStyle = i < 3 ? '#fff' : 'rgba(255,255,255,0.38)';
    rr(305 + i * 5.5, 36 - bh, 4, bh, 1); ctx.fill();
  }

  // WiFi arcs
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.lineCap = 'round';
  for (let i = 0; i < 3; i++) {
    const r = 3.5 + i * 4;
    ctx.beginPath(); ctx.arc(330, 37, r, Math.PI*1.12, Math.PI*1.88); ctx.stroke();
  }
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.arc(330, 37, 1.5, 0, Math.PI*2); ctx.fill();

  // Battery
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5;
  rr(343, 28, 26, 14, 3); ctx.stroke();
  ctx.fillStyle = '#fff'; ctx.fillRect(370, 32, 3, 6);         // nub
  ctx.fillStyle = IOS.green;
  rr(345, 30, 18, 10, 2); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.55)';                    // gloss
  rr(345, 30, 18, 4, 2); ctx.fill();
}

// ================================================================
//  HUD Card  (frosted-glass, iOS style)
// ================================================================
function drawHUD(player, rival, timer) {
  const y0 = 54, HH = 64;

  // Card background
  ctx.fillStyle = 'rgba(18,18,20,0.94)';
  ctx.fillRect(0, y0, VW, HH);
  ctx.fillStyle = 'rgba(255,255,255,0.055)';
  ctx.fillRect(0, y0, VW, 1);
  ctx.fillStyle = 'rgba(255,255,255,0.04)';
  ctx.fillRect(0, y0 + HH - 1, VW, 1);

  const BW = 138, BH = 7, BY = y0 + 50;

  // ── YOU ──
  ctx.font = `600 11px ${FONT}`; ctx.fillStyle = '#FF9500';
  ctx.textAlign = 'left'; ctx.fillText('YOU', 16, y0 + 20);

  ctx.font = `bold 24px ${FONT}`; ctx.fillStyle = '#fff';
  ctx.fillText(Math.ceil(player.hp), 16, y0 + 44);

  // Player HP bar
  ctx.fillStyle = 'rgba(255,255,255,0.10)'; rr(16, BY, BW, BH, 4); ctx.fill();
  const pR   = Math.max(0, player.hp / player.maxHp);
  const pCol = pR > 0.5 ? IOS.green : pR > 0.25 ? IOS.orange : IOS.red;
  if (pR > 0.01) { ctx.fillStyle = pCol; rr(16, BY, BW * pR, BH, 4); ctx.fill(); }
  // Low HP pulse
  if (pR < 0.25) {
    ctx.save(); ctx.globalAlpha = 0.35 + 0.35*Math.sin(Date.now()/110);
    ctx.shadowColor = IOS.red; ctx.shadowBlur = 14;
    ctx.fillStyle = IOS.red; rr(16, BY, BW * pR, BH, 4); ctx.fill();
    ctx.restore();
  }

  // ── RIVAL ──
  ctx.font = `600 11px ${FONT}`; ctx.fillStyle = '#007AFF';
  ctx.textAlign = 'right'; ctx.fillText('RIVAL', VW - 16, y0 + 20);

  ctx.font = `bold 24px ${FONT}`; ctx.fillStyle = '#fff';
  ctx.fillText(Math.ceil(rival.hp), VW - 16, y0 + 44);

  const rx0  = VW - 16 - BW;
  const rR   = Math.max(0, rival.hp / rival.maxHp);
  const rFill = BW * rR;
  ctx.fillStyle = 'rgba(255,255,255,0.10)'; rr(rx0, BY, BW, BH, 4); ctx.fill();
  const rCol = rR > 0.5 ? IOS.green : rR > 0.25 ? IOS.orange : IOS.red;
  if (rR > 0.01) { ctx.fillStyle = rCol; rr(rx0 + BW - rFill, BY, rFill, BH, 4); ctx.fill(); }

  // Bar gloss
  ctx.fillStyle = 'rgba(255,255,255,0.12)';
  rr(16, BY, BW, BH/2, 2); ctx.fill();
  rr(rx0 + BW - rFill, BY, rFill, BH/2, 2); ctx.fill();

  // ── Timer (centre, iOS monospace) ──
  const mins = Math.floor(timer / 60);
  const secs = Math.ceil(timer % 60);
  const ts   = `${mins}:${String(secs).padStart(2,'0')}`;
  const urgent = timer <= 10;
  ctx.save();
  ctx.shadowColor = urgent ? IOS.red : '#ffd700'; ctx.shadowBlur = urgent ? 14 : 7;
  ctx.font = `bold 22px ${FONT}`; ctx.fillStyle = urgent ? IOS.red : '#ffd700';
  ctx.textAlign = 'center'; ctx.fillText(ts, VW/2, y0 + 42);
  ctx.restore();
  ctx.font = `10px ${FONT}`; ctx.fillStyle = 'rgba(255,255,255,0.28)';
  ctx.textAlign = 'center'; ctx.fillText('TIME', VW/2, y0 + 16);
}

// ================================================================
//  Controls Strip  (bottom, shows keyboard shortcuts)
// ================================================================
function drawControlsStrip() {
  const y0 = 760, h = 50;
  ctx.fillStyle = 'rgba(18,18,20,0.88)'; ctx.fillRect(0, y0, VW, h);
  ctx.fillStyle = 'rgba(255,255,255,0.05)'; ctx.fillRect(0, y0, VW, 1);

  const items = [['WASD', 'Move'], ['SPACE', 'Punch'], ['X / K', 'Kick']];
  const colW  = VW / 3;
  items.forEach(([k, v], i) => {
    const cx = i * colW + colW / 2;
    ctx.fillStyle = 'rgba(255,255,255,0.07)'; rr(cx - 32, y0 + 7, 64, 22, 8); ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = 1;
    rr(cx - 32, y0 + 7, 64, 22, 8); ctx.stroke();
    ctx.font = `bold 10px ${FONT}`; ctx.fillStyle = '#d0d0d0';
    ctx.textAlign = 'center'; ctx.fillText(k, cx, y0 + 22);
    ctx.font = `9px ${FONT}`; ctx.fillStyle = 'rgba(255,255,255,0.32)';
    ctx.fillText(v, cx, y0 + 37);
  });
}

// ================================================================
//  Home Indicator
// ================================================================
function drawHomeIndicator() {
  ctx.fillStyle = 'rgba(255,255,255,0.30)';
  rr(VW/2 - 67, VH - 16, 134, 5, 3); ctx.fill();
}

// ================================================================
//  Arena
// ================================================================
function drawArena() {
  const { x, y, w, h } = ARENA;

  // Grass
  const g = ctx.createLinearGradient(x, y, x, y + h);
  g.addColorStop(0,    '#1e4a0a'); g.addColorStop(0.3,  '#2d6814');
  g.addColorStop(0.5,  '#336e18'); g.addColorStop(0.7,  '#2d6814');
  g.addColorStop(1,    '#1e4a0a');
  ctx.fillStyle = g; ctx.fillRect(x, y, w, h);

  // Checkerboard tile tint
  const TS = 42;
  ctx.fillStyle = 'rgba(0,0,0,0.055)';
  for (let tx = x; tx < x+w; tx += TS)
    for (let ty = y; ty < y+h; ty += TS)
      if (((Math.floor((tx-x)/TS) + Math.floor((ty-y)/TS)) % 2) === 0)
        ctx.fillRect(tx, ty, Math.min(TS, x+w-tx), Math.min(TS, y+h-ty));

  // Centre circle
  const midY = y + h/2;
  ctx.save();
  ctx.strokeStyle = 'rgba(255,255,255,0.11)'; ctx.lineWidth = 2;
  ctx.shadowColor = 'rgba(255,255,180,0.35)'; ctx.shadowBlur = 7;
  ctx.beginPath(); ctx.arc(VW/2, midY, 46, 0, Math.PI*2); ctx.stroke();
  ctx.restore();

  // Centre horizontal line
  ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(x, midY); ctx.lineTo(x+w, midY); ctx.stroke();

  // Vignette
  const vig = ctx.createRadialGradient(VW/2, midY, 90, VW/2, midY, 340);
  vig.addColorStop(0, 'rgba(0,0,0,0)'); vig.addColorStop(1, 'rgba(0,0,0,0.5)');
  ctx.fillStyle = vig; ctx.fillRect(x, y, w, h);

  // Border
  ctx.strokeStyle = '#0d2206'; ctx.lineWidth = 3;
  ctx.strokeRect(x, y, w, h);

  // Bushes — corners + side midpoints (4 extra for tall portrait arena)
  [
    [x-6, y-6, 44], [x+w-38, y-6, 44],
    [x-6, y+h-38, 44], [x+w-38, y+h-38, 44],
    [x-6, midY-18, 32], [x+w-26, midY-18, 32],
    [x-6, y+h*0.25-16, 26], [x+w-20, y+h*0.25-16, 26],
    [x-6, y+h*0.75-16, 26], [x+w-20, y+h*0.75-16, 26],
  ].forEach(([bx, by, sz]) => drawBush(bx, by, sz));
}

function drawBush(bx, by, size) {
  const layers = [
    { r:size*0.55, c:'#132c06', ox:0,          oy:size*0.20 },
    { r:size*0.48, c:'#1c4a0e', ox:-size*0.20,  oy:0 },
    { r:size*0.48, c:'#1c4a0e', ox: size*0.20,  oy:0 },
    { r:size*0.40, c:'#266014', ox:0,           oy:-size*0.10 },
    { r:size*0.30, c:'#308020', ox: size*0.05,  oy:-size*0.26 },
    { r:size*0.22, c:'#3a9022', ox:-size*0.10,  oy:-size*0.34 },
  ];
  const cx = bx + size/2, cy = by + size/2;
  layers.forEach(l => {
    ctx.fillStyle = l.c; ctx.beginPath();
    ctx.arc(cx + l.ox, cy + l.oy, l.r, 0, Math.PI*2); ctx.fill();
  });
  ctx.fillStyle = 'rgba(255,255,255,0.055)';
  ctx.beginPath(); ctx.arc(cx - size*0.08, cy - size*0.30, size*0.18, 0, Math.PI*2); ctx.fill();
}

// ================================================================
//  Fighter sprite  (same design, scaled to CS for portrait)
// ================================================================
function drawFighter(cx, cy, scheme, attack, hitFlash) {
  const c = PAL[scheme];
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(CS, CS);   // scale sprite for portrait dimensions

  const flashing = hitFlash > 0 && Math.floor(hitFlash/3) % 2 === 0;
  if (flashing) ctx.globalAlpha = 0.25;

  // Shadow
  const sG = ctx.createRadialGradient(0, 54, 0, 0, 54, 44);
  sG.addColorStop(0, 'rgba(0,0,0,0.50)'); sG.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = sG; ctx.beginPath(); ctx.ellipse(0, 54, 44, 13, 0, 0, Math.PI*2); ctx.fill();

  // Boots
  ctx.fillStyle = '#1a1a1a';
  rr(-28, 38, 22, 16, 5); ctx.fill();
  rr(  6, 38, 22, 16, 5); ctx.fill();
  ctx.fillStyle = '#111';
  rr(-30, 50, 26, 7, 3); ctx.fill();
  rr(  4, 50, 26, 7, 3); ctx.fill();

  // Legs
  const mkLeg = (lx) => {
    const g = ctx.createLinearGradient(lx, 8, lx+20, 40);
    g.addColorStop(0, c.light); g.addColorStop(0.35, c.primary);
    g.addColorStop(0.7, c.mid); g.addColorStop(1, c.dark); return g;
  };

  if (attack === 'kick') {
    ctx.fillStyle = mkLeg(-24); rr(-24, 8, 18, 32, 5); ctx.fill();
    ctx.fillStyle = '#111'; rr(-26, 36, 22, 14, 4); ctx.fill();
    const kG = ctx.createLinearGradient(6, 8, 26, 72);
    kG.addColorStop(0, c.light); kG.addColorStop(0.4, c.primary); kG.addColorStop(1, c.dark);
    ctx.fillStyle = kG; rr(6, 8, 20, 60, 5); ctx.fill();
    ctx.fillStyle = '#1a1a1a'; rr(4, 62, 26, 12, 4); ctx.fill();
    ctx.save(); ctx.shadowColor = c.glow; ctx.shadowBlur = 22;
    ctx.fillStyle = c.primary; ctx.beginPath(); ctx.arc(16, 68, 13, 0, Math.PI*2); ctx.fill();
    ctx.restore();
  } else {
    ctx.fillStyle = mkLeg(-24); rr(-24, 8, 18, 32, 5); ctx.fill();
    ctx.fillStyle = mkLeg(6);   rr(  6, 8, 18, 32, 5); ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.09)';
    rr(-22, 20, 14, 8, 3); ctx.fill();
    rr(  8, 20, 14, 8, 3); ctx.fill();
  }

  // Torso
  const tG = ctx.createLinearGradient(-28, -28, 28, 16);
  tG.addColorStop(0, c.light); tG.addColorStop(0.25, c.primary);
  tG.addColorStop(0.65, c.mid); tG.addColorStop(1, c.dark);
  ctx.fillStyle = tG; rr(-28, -28, 56, 38, 9); ctx.fill();
  ctx.save(); ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = 1.5;
  rr(-28, -28, 56, 38, 9); ctx.stroke(); ctx.restore();
  ctx.fillStyle = c.dark; ctx.fillRect(-1.5, -24, 3, 30);

  // Chest core
  ctx.save(); ctx.shadowColor = c.visor; ctx.shadowBlur = 16;
  const cG = ctx.createRadialGradient(0, -12, 0, 0, -12, 10);
  cG.addColorStop(0, '#fff'); cG.addColorStop(0.4, c.visor); cG.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = cG; ctx.beginPath(); ctx.arc(0, -12, 10, 0, Math.PI*2); ctx.fill();
  ctx.restore();
  ctx.fillStyle = 'rgba(255,255,255,0.07)'; rr(-9, -24, 18, 10, 3); ctx.fill();

  // Pauldrons
  const mkSP = (sx) => {
    const g = ctx.createLinearGradient(sx-16, -30, sx+8, -8);
    g.addColorStop(0, c.light); g.addColorStop(0.45, c.primary); g.addColorStop(1, c.dark); return g;
  };
  ctx.fillStyle = mkSP(-36); ctx.beginPath(); ctx.ellipse(-37, -20, 16, 10, -0.3, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle = mkSP(36);  ctx.beginPath(); ctx.ellipse( 37, -20, 16, 10,  0.3, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.14)';
  ctx.beginPath(); ctx.ellipse(-37, -24, 11, 5, -0.3, 0, Math.PI); ctx.fill();
  ctx.beginPath(); ctx.ellipse( 37, -24, 11, 5,  0.3, 0, Math.PI); ctx.fill();

  // Arms
  const mkArm = (ax) => {
    const g = ctx.createLinearGradient(ax, -18, ax+14, 14);
    g.addColorStop(0, c.primary); g.addColorStop(0.5, c.mid); g.addColorStop(1, c.dark); return g;
  };

  if (attack === 'punch') {
    ctx.fillStyle = mkArm(-36); rr(-36, -18, 14, 28, 4); ctx.fill();
    const pG = ctx.createLinearGradient(22, -18, 36, 56);
    pG.addColorStop(0, c.light); pG.addColorStop(0.3, c.primary); pG.addColorStop(1, c.mid);
    ctx.fillStyle = pG; rr(22, -18, 14, 60, 5); ctx.fill();
    const fG = ctx.createRadialGradient(29, 40, 0, 29, 40, 18);
    fG.addColorStop(0, c.light); fG.addColorStop(0.5, c.primary); fG.addColorStop(1, c.dark);
    ctx.fillStyle = fG; rr(20, 38, 18, 14, 5); ctx.fill();
    ctx.save(); ctx.shadowColor = c.visor; ctx.shadowBlur = 26;
    ctx.fillStyle = c.visor; ctx.globalAlpha = 0.65;
    ctx.beginPath(); ctx.arc(29, 46, 10, 0, Math.PI*2); ctx.fill(); ctx.restore();
  } else {
    ctx.fillStyle = mkArm(-36); rr(-36, -18, 14, 28, 4); ctx.fill();
    ctx.fillStyle = mkArm(22);  rr( 22, -18, 14, 28, 4); ctx.fill();
  }

  // Helmet
  const hG = ctx.createLinearGradient(-22, -78, 22, -26);
  hG.addColorStop(0, c.light); hG.addColorStop(0.3, c.primary);
  hG.addColorStop(0.65, c.mid); hG.addColorStop(1, c.dark);
  ctx.fillStyle = hG; rr(-21, -76, 42, 50, 12); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.12)'; rr(-17, -74, 34, 18, 7); ctx.fill();
  const crG = ctx.createLinearGradient(-8, -86, 8, -72);
  crG.addColorStop(0, c.light); crG.addColorStop(1, c.mid);
  ctx.fillStyle = crG; rr(-7, -86, 14, 14, 4); ctx.fill();

  // Visor
  ctx.save(); ctx.shadowColor = c.visor; ctx.shadowBlur = 18;
  const vG = ctx.createLinearGradient(-16, -54, 16, -40);
  vG.addColorStop(0, c.visor); vG.addColorStop(0.5, '#fff'); vG.addColorStop(1, c.visor);
  ctx.fillStyle = vG; rr(-16, -54, 32, 14, 5); ctx.fill(); ctx.restore();
  ctx.fillStyle = 'rgba(255,255,255,0.42)'; rr(-14, -53, 28, 4, 2); ctx.fill();

  ctx.restore();
}

// ================================================================
//  Menu Screen  (iOS App Store launch feel)
// ================================================================
function drawMenu() {
  // Background
  const bg = ctx.createLinearGradient(0, 0, 0, VH);
  bg.addColorStop(0, '#09090c'); bg.addColorStop(0.5, '#0c0c10'); bg.addColorStop(1, '#080810');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, VW, VH);

  // Ambient colour wash
  const glow = ctx.createRadialGradient(VW/2, VH*0.4, 0, VW/2, VH*0.4, 220);
  glow.addColorStop(0, 'rgba(255,90,20,0.10)'); glow.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = glow; ctx.fillRect(0, 0, VW, VH);

  drawStatusBar();

  // Preview fighters
  drawFighter(VW/2 - 70, VH/2 + 30, 'orange', null, 0);
  drawFighter(VW/2 + 70, VH/2 + 30, 'blue',   null, 0);

  // VS
  ctx.font = `bold 18px ${FONT}`; ctx.fillStyle = 'rgba(255,255,255,0.22)';
  ctx.textAlign = 'center'; ctx.fillText('VS', VW/2, VH/2 + 52);

  // Title
  ctx.save(); ctx.shadowColor = '#e85c14'; ctx.shadowBlur = 28;
  ctx.font = `bold 62px ${FONT}`; ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center'; ctx.fillText('REDTAIL', VW/2, VH*0.22); ctx.restore();

  ctx.save(); ctx.shadowColor = '#2878e0'; ctx.shadowBlur = 18;
  ctx.font = `bold 36px ${FONT}`; ctx.fillStyle = '#e85c14';
  ctx.textAlign = 'center'; ctx.fillText('BATTLE', VW/2, VH*0.22 + 48); ctx.restore();

  // Subtitle
  ctx.font = `13px ${FONT}`; ctx.fillStyle = 'rgba(255,255,255,0.30)';
  ctx.textAlign = 'center'; ctx.fillText('1 vs 1 Arena Fighter', VW/2, VH*0.22 + 74);

  // START button (iOS primary style — orange, pill-shaped)
  const pulse  = 0.88 + 0.12 * Math.sin(Date.now() / 700);
  const btnW = 210, btnH = 56, btnX = VW/2 - btnW/2, btnY = VH*0.79;
  ctx.save();
  ctx.globalAlpha = pulse;
  const btnG = ctx.createLinearGradient(btnX, btnY, btnX, btnY + btnH);
  btnG.addColorStop(0, '#FF9500'); btnG.addColorStop(1, '#c86010');
  ctx.fillStyle = btnG; ctx.shadowColor = 'rgba(255,150,0,0.55)'; ctx.shadowBlur = 20;
  rr(btnX, btnY, btnW, btnH, 28); ctx.fill(); ctx.restore();
  // Button gloss
  ctx.fillStyle = 'rgba(255,255,255,0.18)'; rr(btnX+4, btnY+4, btnW-8, btnH/2-4, 20); ctx.fill();
  ctx.font = `bold 17px ${FONT}`; ctx.fillStyle = '#fff';
  ctx.textAlign = 'center'; ctx.fillText('ENTER  to  Start', VW/2, btnY + 34);

  // Controls hint
  ctx.font = `12px ${FONT}`; ctx.fillStyle = 'rgba(255,255,255,0.20)';
  ctx.textAlign = 'center'; ctx.fillText('WASD · SPACE: Punch · X: Kick', VW/2, VH*0.91);

  drawHomeIndicator();
}

// ================================================================
//  Game Over  (iOS modal / alert sheet)
// ================================================================
function drawGameOver() {
  ctx.fillStyle = 'rgba(0,0,0,0.72)'; ctx.fillRect(0, 0, VW, VH);

  const cW = 330, cH = 220, cX = VW/2 - cW/2, cY = VH/2 - cH/2;
  ctx.fillStyle = 'rgba(26,26,28,0.97)'; rr(cX, cY, cW, cH, 22); ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.08)'; ctx.lineWidth = 1;
  rr(cX, cY, cW, cH, 22); ctx.stroke();
  // Card gloss
  ctx.fillStyle = 'rgba(255,255,255,0.04)'; rr(cX+2, cY+2, cW-4, cH/3, 20); ctx.fill();

  const isWin = winner === 'player';

  // Trophy / skull  ─  use text emoji for clean rendering
  ctx.font = `52px ${FONT}`; ctx.textAlign = 'center';
  ctx.fillText(isWin ? '🏆' : '💀', VW/2, cY + 72);

  // Result text
  ctx.save();
  ctx.shadowColor = isWin ? '#ffd700' : IOS.red; ctx.shadowBlur = 18;
  ctx.font = `bold 30px ${FONT}`; ctx.fillStyle = isWin ? '#ffd700' : IOS.red;
  ctx.textAlign = 'center'; ctx.fillText(isWin ? 'Victory!' : 'Defeated', VW/2, cY + 116);
  ctx.restore();

  // Play Again button
  const bW = 240, bH = 50, bX = VW/2 - bW/2, bY = cY + 142;
  ctx.fillStyle = isWin ? IOS.green : IOS.blue;
  ctx.shadowColor = isWin ? 'rgba(52,199,89,0.4)' : 'rgba(0,122,255,0.4)';
  ctx.shadowBlur = 14;
  rr(bX, bY, bW, bH, 25); ctx.fill();
  ctx.shadowBlur = 0;
  ctx.fillStyle = 'rgba(255,255,255,0.16)'; rr(bX+4, bY+4, bW-8, bH/2-4, 18); ctx.fill();
  ctx.font = `bold 15px ${FONT}`; ctx.fillStyle = '#fff';
  ctx.textAlign = 'center'; ctx.fillText('Play Again  (ENTER)', VW/2, bY + 30);
}

// ================================================================
//  Fighter class
// ================================================================
class Fighter {
  constructor(x, y, isPlayer) {
    this.x = x; this.y = y; this.w = 55; this.h = 80;
    this.speed    = isPlayer ? 4.0 : 1.8;
    this.hp = 100; this.maxHp = 100;
    this.isPlayer = isPlayer;
    this.attacking = null; this.attackTimer = 0; this.attackCooldown = 0;
    this.hitFlash = 0; this.aiTimer = 0; this.dustTimer = 0;
  }

  get cx() { return this.x + this.w / 2; }
  get cy() { return this.y + this.h / 2; }

  tryAttack(type) {
    if (this.attackCooldown > 0) return false;
    this.attacking = type;
    this.attackTimer = type === 'punch' ? 20 : 24;
    const base = type === 'punch' ? 38 : 56;
    this.attackCooldown = this.isPlayer ? base : base * 2.2;
    return true;
  }

  get attackRange()  { return this.attacking === 'punch' ? 75 : 95; }
  get attackDamage() {
    const base = this.attacking === 'punch' ? 8 : 15;
    return this.isPlayer ? base : Math.floor(base * 0.55);
  }

  distanceTo(o) { return Math.hypot(this.cx - o.cx, this.cy - o.cy); }
  isHitting(o)  { return !!this.attacking && this.distanceTo(o) < this.attackRange; }

  takeDamage(n) { this.hp = Math.max(0, this.hp - n); this.hitFlash = 20; }

  updateAI(player) {
    this.aiTimer--;
    const d = this.distanceTo(player);
    if (d < 105 && this.attackCooldown <= 0) {
      if (Math.random() > 0.28) this.tryAttack(Math.random() < 0.55 ? 'punch' : 'kick');
      this.aiTimer = 55 + Math.random() * 40;
    } else if (this.aiTimer <= 0) {
      const back = d < 75 && Math.random() < 0.12;
      const sign = back ? -1 : 1;
      const dx = sign * (player.cx - this.cx), dy = sign * (player.cy - this.cy);
      const len = Math.hypot(dx, dy) || 1;
      this.x += (dx/len) * this.speed; this.y += (dy/len) * this.speed;
      this.aiTimer = 3;
    }
  }

  clamp() {
    this.x = Math.max(ARENA.x, Math.min(ARENA.x + ARENA.w - this.w, this.x));
    this.y = Math.max(ARENA.y, Math.min(ARENA.y + ARENA.h - this.h, this.y));
  }

  update(other, moving) {
    if (this.attackTimer > 0) this.attackTimer--; else this.attacking = null;
    if (this.attackCooldown > 0) this.attackCooldown--;
    if (this.hitFlash > 0)       this.hitFlash--;
    if (!this.isPlayer) this.updateAI(other);
    if (moving && this.isPlayer) {
      if (--this.dustTimer <= 0) { spawnDust(this.cx, this.y + this.h - 15); this.dustTimer = 9; }
    }
    this.clamp();
  }

  draw() {
    drawFighter(this.cx, this.cy, this.isPlayer ? 'orange' : 'blue', this.attacking, this.hitFlash);
  }
}

// ================================================================
//  Input
// ================================================================
const keys = { up:false, down:false, left:false, right:false, punch:false, kick:false };

document.addEventListener('keydown', e => {
  switch (e.key) {
    case 'ArrowUp':    case 'w': case 'W': keys.up    = true; e.preventDefault(); break;
    case 'ArrowDown':  case 's': case 'S': keys.down  = true; e.preventDefault(); break;
    case 'ArrowLeft':  case 'a': case 'A': keys.left  = true; e.preventDefault(); break;
    case 'ArrowRight': case 'd': case 'D': keys.right = true; e.preventDefault(); break;
    case ' ':
      if (gameState === 'playing') keys.punch = true;
      e.preventDefault(); break;
    case 'x': case 'X': case 'k': case 'K': keys.kick = true; break;
    case 'Enter':
      if (gameState !== 'playing') startGame();
      e.preventDefault(); break;
  }
});
document.addEventListener('keyup', e => {
  switch (e.key) {
    case 'ArrowUp':    case 'w': case 'W': keys.up    = false; break;
    case 'ArrowDown':  case 's': case 'S': keys.down  = false; break;
    case 'ArrowLeft':  case 'a': case 'A': keys.left  = false; break;
    case 'ArrowRight': case 'd': case 'D': keys.right = false; break;
    case ' ': keys.punch = false; break;
    case 'x': case 'X': case 'k': case 'K': keys.kick = false; break;
  }
});

// ================================================================
//  Game state
// ================================================================
let gameState = 'menu';
let player, rival, timer, winner;
let pHitUsed = false, rHitUsed = false;

function startGame() {
  player   = new Fighter(VW/2 - 27, ARENA.y + ARENA.h - 110, true);
  rival    = new Fighter(VW/2 - 27, ARENA.y + 28, false);
  timer    = 90; winner = null;
  pHitUsed = rHitUsed = false;
  particles.length = 0;
  gameState = 'playing';
}

// ================================================================
//  Update
// ================================================================
let lastTs = 0, timerAcc = 0;

function update(dt) {
  if (gameState !== 'playing') return;
  const moving = keys.up || keys.down || keys.left || keys.right;
  if (keys.up)    player.y -= player.speed;
  if (keys.down)  player.y += player.speed;
  if (keys.left)  player.x -= player.speed;
  if (keys.right) player.x += player.speed;
  if (keys.punch) player.tryAttack('punch');
  if (keys.kick)  player.tryAttack('kick');

  player.update(rival, moving);
  rival.update(player, false);
  updateParticles();
  updateShake();

  if (player.isHitting(rival)) {
    if (!pHitUsed) {
      rival.takeDamage(player.attackDamage);
      spawnHit(rival.cx, rival.cy - 20, PAL.orange.hitGlow, 20);
      triggerShake(player.attacking === 'kick' ? 9 : 5);
      pHitUsed = true;
    }
  } else { pHitUsed = false; }

  if (rival.isHitting(player)) {
    if (!rHitUsed) {
      player.takeDamage(rival.attackDamage);
      spawnHit(player.cx, player.cy - 20, PAL.blue.hitGlow, 14);
      triggerShake(rival.attacking === 'kick' ? 6 : 3);
      rHitUsed = true;
    }
  } else { rHitUsed = false; }

  timerAcc += dt;
  if (timerAcc >= 1000) { timer = Math.max(0, timer - 1); timerAcc -= 1000; }

  if (rival.hp  <= 0) { gameState = 'gameover'; winner = 'player'; }
  else if (player.hp <= 0) { gameState = 'gameover'; winner = 'rival'; }
  else if (timer <= 0) { gameState = 'gameover'; winner = player.hp >= rival.hp ? 'player' : 'rival'; }
}

// ================================================================
//  Render
// ================================================================
function render() {
  ctx.clearRect(0, 0, VW, VH);

  if (gameState === 'menu') { drawMenu(); return; }

  // Background
  ctx.fillStyle = '#080808'; ctx.fillRect(0, 0, VW, VH);

  ctx.save();
  ctx.translate(shakeX, shakeY);

  drawArena();
  [player, rival].sort((a, b) => a.cy - b.cy).forEach(f => f.draw());
  drawParticles();

  ctx.restore();

  drawStatusBar();
  drawHUD(player, rival, timer);
  drawControlsStrip();
  drawHomeIndicator();

  if (gameState === 'gameover') drawGameOver();
}

// ================================================================
//  Scale iPhone frame to fit the browser window
// ================================================================
function scalePhone() {
  const frame = document.getElementById('iphone');
  if (!frame) return;
  const s = Math.min(
    (window.innerHeight * 0.97) / 882,
    (window.innerWidth  * 0.97) / 410,
    1.20   // allow slight upscale on large monitors
  );
  frame.style.transform = `scale(${s})`;
}
window.addEventListener('resize', scalePhone);
scalePhone();

// ================================================================
//  Game loop
// ================================================================
function loop(ts) {
  const dt = Math.min(ts - lastTs, 50);
  lastTs = ts;
  update(dt);
  render();
  requestAnimationFrame(loop);
}
requestAnimationFrame(ts => { lastTs = ts; requestAnimationFrame(loop); });
