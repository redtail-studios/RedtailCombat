import { BIRD, drawSprite } from "./sprites";
import { LOGO_URL } from "@/lib/teamData";

export function createCrewFlight(canvas, members, cb, unlocked = [], opts = {}) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const compact = !!opts.compact;
  const PX = 3, BW = 48, BH = 48, SPEED = compact ? 2.0 : 2.6, TK = 60, FLOOR = 24, LIVES = 3;
  const DRONE_EVERY = compact ? 130 : 80, DRONE_MIN = compact ? 14 : 18, DRONE_VAR = compact ? 10 : 14;
  const keys = {};
  const logo = new Image(); logo.src = LOGO_URL;
  const imgs = members.map((m) => { const i = new Image(); i.crossOrigin = "anonymous"; i.src = m.portrait; return i; });
  const far = Array.from({ length: 30 }, (_, i) => ({ x: i * 70, w: 30 + ((i * 23) % 30), h: 40 + ((i * 31) % 90) }));
  const near = Array.from({ length: 24 }, (_, i) => ({ x: i * 90, w: 50 + ((i * 37) % 40), h: 60 + ((i * 53) % 140) }));
  let bird, target, drones, chips, tokens, trail, score, frame, started, paused, over, inv, lives, collected, raf;

  const emit = (status) => cb.onState(status, { score, lives, collected: collected.length, total: members.length });
  const reset = () => {
    bird = { x: W * 0.25, y: H / 2 }; target = H / 2;
    drones = []; chips = []; tokens = []; trail = []; collected = [];
    score = 0; frame = 0; inv = 0; lives = LIVES; started = paused = over = false;
    emit("ready");
  };
  const start = () => {
    if (paused) return;
    if (over) return reset();
    if (!started) { started = true; emit("playing"); }
  };
  const pause = () => { if (started && !over && !paused) { paused = true; emit("paused"); } };
  const resume = () => {
    if (!paused) return;
    paused = false;
    emit("playing");
  };
  const overlap = (x, y, w, h) => bird.x + BW > x && bird.x < x + w && bird.y + BH > y && bird.y < y + h;
  const nextMember = () => {
    const free = members.filter((m) => !tokens.some((t) => t.handle === m.handle));
    return free.find((m) => !collected.includes(m.handle) && !unlocked.includes(m.handle))
      || free.find((m) => !collected.includes(m.handle))
      || free[Math.floor(Math.random() * free.length)];
  };

  const update = () => {
    frame++;
    if (!started) { bird.y = H / 2 + Math.sin(frame / 14) * 10; return; }
    if (paused || over) return;
    if (inv > 0) inv--;
    if (keys.ArrowUp || keys.KeyW) target -= 6;
    if (keys.ArrowDown || keys.KeyS) target += 6;
    target = Math.max(10, Math.min(H - FLOOR - BH - 10, target));
    bird.y += (target - bird.y) * 0.1;
    trail.push({ x: bird.x + 4, y: bird.y + BH / 2 });
    if (trail.length > 14) trail.shift();
    for (const t of trail) t.x -= SPEED * 1.3;

    if (frame % DRONE_EVERY === 0) drones.push({ x: W + 20, y: 30 + Math.random() * (H - FLOOR - 90), t: Math.random() * 100, s: DRONE_MIN + Math.random() * DRONE_VAR });
    if (frame % 50 === 25) chips.push({ x: W, y: 40 + Math.random() * (H - FLOOR - 100) });
    if (frame % 160 === 60) {
      const m = nextMember();
      if (m) tokens.push({ handle: m.handle, idx: members.indexOf(m), x: W, y: 60 + Math.random() * (H - FLOOR - 180), t: 0 });
    }
    for (const d of drones) {
      d.x -= SPEED * 1.1; d.t++; d.y += Math.sin(d.t / 20) * 0.8;
      if (inv === 0 && overlap(d.x, d.y, d.s, d.s)) {
        inv = 60; lives--;
        if (lives <= 0) { over = true; emit("over"); return; }
        emit("playing");
      }
    }
    for (const c of chips) {
      c.x -= SPEED;
      if (!c.got && overlap(c.x, c.y, 14, 14)) { c.got = true; score++; emit("playing"); }
    }
    for (const t of tokens) {
      t.x -= SPEED; t.t++;
      if (overlap(t.x, t.y + Math.sin(t.t / 12) * 6, TK, TK)) {
        t.got = true; score += 10;
        if (collected.includes(t.handle)) { emit("playing"); continue; }
        collected.push(t.handle);
        if (!unlocked.includes(t.handle)) unlocked.push(t.handle);
        paused = true; emit("paused");
        cb.onCollect(members[t.idx]);
      }
    }
    drones = drones.filter((d) => d.x > -40);
    chips = chips.filter((c) => !c.got && c.x > -20);
    tokens = tokens.filter((t) => !t.got && t.x > -TK);
  };

  const skyline = (rows, span, k, color) => {
    ctx.fillStyle = color;
    const off = (frame * SPEED * k) % span;
    for (const b of rows) {
      const x = ((b.x - off) % span + span) % span - 100;
      ctx.fillRect(x, H - FLOOR - b.h, b.w, b.h);
    }
  };

  const draw = () => {
    ctx.fillStyle = "#0A0A0B"; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "rgba(226,226,226,0.3)";
    for (let i = 0; i < 50; i++) ctx.fillRect(((i * 173 - frame * 0.3) % W + W) % W, (i * 97) % (H - 150), 2, 2);
    skyline(far, 30 * 70, 0.15, "#101014");
    skyline(near, 24 * 90, 0.4, "#15151A");
    ctx.fillStyle = "rgba(255,46,46,0.35)";
    for (let i = 0; i < 40; i++) ctx.fillRect(((i * 61 - frame * SPEED * 0.4) % W + W) % W, H - FLOOR - 30 - ((i * 47) % 120), 3, 3);
    trail.forEach((t, i) => { ctx.fillStyle = `rgba(180,255,57,${(i / trail.length) * 0.5})`; ctx.fillRect(t.x, t.y, 4, 4); });
    ctx.fillStyle = "#FF2E2E";
    for (const d of drones) {
      const q = d.s / 2;
      for (let k = 0; k < 4; k++) {
        const jx = ((frame * 7 + k * 13) % 5) - 2, jy = ((frame * 11 + k * 17) % 5) - 2;
        ctx.fillRect(d.x + (k % 2) * q + jx, d.y + Math.floor(k / 2) * q + jy, q - 3, q - 3);
      }
    }
    for (const c of chips) {
      ctx.fillStyle = "#B8860B"; ctx.fillRect(c.x, c.y + 2, 14, 12);
      ctx.fillStyle = "#FFC93C"; ctx.fillRect(c.x, c.y, 14, 12);
      ctx.fillStyle = "#FFF1B8"; ctx.fillRect(c.x + 3, c.y + 2, 3, 3);
      ctx.fillStyle = "#B8860B"; ctx.fillRect(c.x + 5, c.y + 4, 4, 5);
    }
    for (const t of tokens) {
      const y = t.y + Math.sin(t.t / 12) * 6;
      ctx.fillStyle = "#B4FF39"; ctx.fillRect(t.x - 3, y - 3, TK + 6, TK + 6);
      ctx.fillStyle = "#15151A"; ctx.fillRect(t.x, y, TK, TK);
      const img = imgs[t.idx];
      ctx.imageSmoothingEnabled = false;
      if (img.complete && img.naturalWidth) ctx.drawImage(img, t.x, y, TK, TK);
      ctx.fillStyle = "#B4FF39"; ctx.font = "8px 'Press Start 2P', monospace"; ctx.textAlign = "center";
      ctx.fillText(members[t.idx].player, t.x + TK / 2, y + TK + 14);
    }
    ctx.fillStyle = "#15151A"; ctx.fillRect(0, H - FLOOR, W, FLOOR);
    ctx.fillStyle = "#FF2E2E"; ctx.fillRect(0, H - FLOOR, W, 3);
    if (!(inv > 0 && Math.floor(frame / 4) % 2)) {
      ctx.save();
      ctx.translate(bird.x + BW / 2, bird.y + BH / 2);
      ctx.rotate(started ? Math.max(-0.3, Math.min(0.3, (target - bird.y) * 0.01)) : 0);
      if (logo.complete && logo.naturalWidth) {
        const s = Math.min(BW / logo.naturalWidth, BH / logo.naturalHeight);
        const w = logo.naturalWidth * s, h = logo.naturalHeight * s;
        ctx.imageSmoothingEnabled = false;
        ctx.shadowColor = "rgba(255,46,46,0.7)"; ctx.shadowBlur = 10;
        ctx.drawImage(logo, -w / 2, -h / 2, w, h);
        ctx.shadowBlur = 0;
      } else {
        drawSprite(ctx, BIRD, -(24 * PX) / 2, -(13 * PX) / 2, PX);
      }
      ctx.restore();
    }
  };

  const loop = () => { update(); draw(); raf = requestAnimationFrame(loop); };
  const onMove = (e) => { target = (e.offsetY / canvas.clientHeight) * H - BH / 2; };
  const kd = (e) => {
    keys[e.code] = true;
    if (["Space", "ArrowUp", "ArrowDown"].includes(e.code)) { e.preventDefault(); start(); }
  };
  const ku = (e) => { keys[e.code] = false; };
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerdown", start);
  window.addEventListener("keydown", kd);
  window.addEventListener("keyup", ku);
  reset(); loop();

  return {
    pause, resume,
    destroy: () => {
      cancelAnimationFrame(raf);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerdown", start);
      window.removeEventListener("keydown", kd);
      window.removeEventListener("keyup", ku);
    },
  };
}