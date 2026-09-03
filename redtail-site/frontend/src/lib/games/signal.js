import { SHIP, INVADER_A, INVADER_B, drawSprite } from "./sprites";

const RED = { g: "#FF2E2E" };

export function createSignalStrike(canvas, stages, cb) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const PX = 3, SW = 9 * PX, SH = 6 * PX, IW = 10 * PX, IH = 8 * PX, SHIP_Y = H - 72, CAGE = 56, CAGE_HP = 3;
  const keys = {};
  let ship, invaders, shots, bombs, bursts, captive, dir, wave, score, lives, frame, started, dead, paused, complete, inv, collected, firing, lastShot, raf;

  const emit = (status) => cb.onState(status, { score, lives, collected: collected.length, total: stages.length });
  const spawnWave = () => {
    wave++; invaders = [];
    for (let r = 0; r < 2; r++) for (let c = 0; c < 6; c++) invaders.push({ x: 220 + c * 72, y: 100 + r * 44, r });
  };
  const reset = () => {
    ship = { x: W / 2 }; shots = []; bombs = []; bursts = []; captive = null; collected = [];
    dir = 1; wave = 0; score = 0; lives = 5; frame = 0; inv = 0; lastShot = 0; firing = false;
    started = dead = paused = complete = false;
    spawnWave(); emit("ready");
  };
  const start = () => {
    if (paused) return;
    if (dead || complete) return reset();
    if (!started) { started = true; emit("playing"); }
  };
  const pause = () => { if (started && !dead && !complete && !paused) { paused = true; emit("paused"); } };
  const resume = () => {
    if (!paused) return;
    paused = false;
    if (collected.length === stages.length) { complete = true; emit("complete"); } else emit("playing");
  };
  const fire = () => { if (frame - lastShot < 12) return; lastShot = frame; shots.push({ x: ship.x - 2, y: SHIP_Y - 8 }); };
  const hit = (s, x, y, w, h) => s.x < x + w && s.x + 4 > x && s.y < y + h && s.y + 10 > y;
  const burst = (x, y, c) => bursts.push({ x, y, t: 0, c });
  const hurt = () => {
    if (inv > 0) return;
    lives--; inv = 120;
    if (lives <= 0) { dead = true; emit("over"); } else emit("playing");
  };

  const update = () => {
    frame++;
    if (!started || dead || paused || complete) return;
    if (inv > 0) inv--;
    if (keys.ArrowLeft || keys.KeyA) ship.x -= 5;
    if (keys.ArrowRight || keys.KeyD) ship.x += 5;
    ship.x = Math.max(SW / 2, Math.min(W - SW / 2, ship.x));
    if (firing || keys.Space) fire();

    if (!captive && frame % 120 === 40) {
      const s = stages.find((st) => !collected.includes(st.n));
      if (s) captive = { n: s.n, name: s.name, x: 60 + Math.random() * (W - 120 - CAGE), y: 22, hp: CAGE_HP, vx: Math.random() < 0.5 ? -1 : 1 };
    }
    if (captive) { captive.x += captive.vx * 0.8; if (captive.x < 20 || captive.x > W - 20 - CAGE) captive.vx *= -1; }

    const sp = 0.35 + wave * 0.06;
    let edge = false;
    for (const i of invaders) { i.x += dir * sp; if (i.x < 20 || i.x + IW > W - 20) edge = true; }
    if (edge) { dir *= -1; for (const i of invaders) i.y += 8; }
    for (const i of invaders) {
      if (i.y + IH >= SHIP_Y) { hurt(); if (dead) return; spawnWave(); break; }
      if (Math.random() < 0.0006 + wave * 0.0002) bombs.push({ x: i.x + IW / 2 - 2, y: i.y + IH });
    }

    for (const s of shots) {
      s.y -= 9;
      if (s.y < -10) { s.done = true; continue; }
      for (const i of invaders) {
        if (!i.dead && hit(s, i.x, i.y, IW, IH)) { i.dead = true; s.done = true; score++; burst(i.x + IW / 2, i.y + IH / 2, "#FF2E2E"); emit("playing"); break; }
      }
      if (!s.done && captive && hit(s, captive.x, captive.y, CAGE, CAGE)) {
        s.done = true; captive.hp--; burst(s.x, s.y, "#B4FF39");
        if (captive.hp <= 0) {
          const st = stages.find((x) => x.n === captive.n);
          collected.push(captive.n); score += 25;
          burst(captive.x + CAGE / 2, captive.y + CAGE / 2, "#B4FF39");
          captive = null; paused = true; emit("paused");
          cb.onCollect(st);
          return;
        }
      }
    }
    invaders = invaders.filter((i) => !i.dead);
    shots = shots.filter((s) => !s.done);
    if (!invaders.length) spawnWave();

    for (const b of bombs) {
      b.y += 2.2;
      if (b.y > H) b.done = true;
      else if (b.x + 4 > ship.x - SW / 2 && b.x < ship.x + SW / 2 && b.y + 10 > SHIP_Y && b.y < SHIP_Y + SH) { b.done = true; hurt(); if (dead) return; }
    }
    bombs = bombs.filter((b) => !b.done);
    for (const b of bursts) b.t++;
    bursts = bursts.filter((b) => b.t < 14);
  };

  const draw = () => {
    ctx.fillStyle = "#0A0A0B"; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "rgba(226,226,226,0.35)";
    for (let i = 0; i < 60; i++) ctx.fillRect((i * 173) % W, ((i * 97 + frame * 0.4) % H), 2, 2);
    if (captive) {
      const { x, y, n, name, hp } = captive;
      ctx.fillStyle = "#B4FF39"; ctx.fillRect(x - 3, y - 3, CAGE + 6, CAGE + 6);
      ctx.fillStyle = "#15151A"; ctx.fillRect(x, y, CAGE, CAGE);
      ctx.fillStyle = "#B4FF39"; ctx.textAlign = "center";
      ctx.font = "14px 'Press Start 2P', monospace"; ctx.fillText(n, x + CAGE / 2, y + 26);
      ctx.fillStyle = "#E2E2E2"; ctx.font = "6px 'Press Start 2P', monospace"; ctx.fillText(name, x + CAGE / 2, y + 44);
      ctx.fillStyle = "#FF2E2E";
      for (let k = 0; k < hp; k++) { const j = ((frame * 5 + k * 11) % 3) - 1; ctx.fillRect(x + 8 + k * 18 + j, y - 8, 4, CAGE + 16); }
      ctx.fillRect(x - 8, y - 8, CAGE + 16, 4); ctx.fillRect(x - 8, y + CAGE + 4, CAGE + 16, 4);
    }
    for (const i of invaders) drawSprite(ctx, (i.r + Math.floor(frame / 20)) % 2 ? INVADER_B : INVADER_A, i.x, i.y, PX, RED);
    ctx.fillStyle = "#B4FF39"; for (const s of shots) ctx.fillRect(s.x, s.y, 4, 10);
    ctx.fillStyle = "#FF2E2E"; for (const b of bombs) ctx.fillRect(b.x, b.y, 4, 10);
    for (const b of bursts) {
      ctx.strokeStyle = b.c; ctx.globalAlpha = 1 - b.t / 14; ctx.lineWidth = 3;
      ctx.strokeRect(b.x - b.t * 2, b.y - b.t * 2, b.t * 4, b.t * 4);
    }
    ctx.globalAlpha = 1;
    if (!(inv > 0 && Math.floor(frame / 4) % 2)) drawSprite(ctx, SHIP, ship.x - SW / 2, SHIP_Y, PX);
    ctx.fillStyle = "#15151A"; ctx.fillRect(0, H - 20, W, 20);
    ctx.fillStyle = "#FF2E2E"; ctx.fillRect(0, H - 20, W, 3);
  };

  const loop = () => { update(); draw(); raf = requestAnimationFrame(loop); };
  const onMove = (e) => { ship.x = (e.offsetX / canvas.clientWidth) * W; };
  const onDown = () => { start(); firing = true; };
  const onUp = () => { firing = false; };
  const kd = (e) => { keys[e.code] = true; if (["Space", "ArrowLeft", "ArrowRight"].includes(e.code)) { e.preventDefault(); if (e.code === "Space") start(); } };
  const ku = (e) => { keys[e.code] = false; };
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerdown", onDown);
  canvas.addEventListener("pointerup", onUp);
  canvas.addEventListener("pointerleave", onUp);
  window.addEventListener("keydown", kd);
  window.addEventListener("keyup", ku);
  reset(); loop();

  return {
    pause, resume,
    destroy: () => {
      cancelAnimationFrame(raf);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("pointerleave", onUp);
      window.removeEventListener("keydown", kd);
      window.removeEventListener("keyup", ku);
    },
  };
}