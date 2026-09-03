export function createPong(canvas) {
  const ctx = canvas.getContext("2d");
  const PH = 96, PW = 10;
  let W, H, raf, mouseY = null;
  const ball = { x: 0, y: 0, vx: 3.2, vy: 2.1 };
  const left = { y: 0 }, right = { y: 0 };

  const resize = () => {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
    ball.x = W / 2; ball.y = H / 2; left.y = right.y = H / 2 - PH / 2;
  };
  const follow = (p, target) => { p.y += (target - PH / 2 - p.y) * 0.08; p.y = Math.max(0, Math.min(H - PH, p.y)); };

  const step = () => {
    ball.x += ball.vx; ball.y += ball.vy;
    if (ball.y < 0 || ball.y > H) ball.vy *= -1;
    follow(left, mouseY ?? ball.y);
    follow(right, ball.y);
    const lx = 40, rx = W - 40 - PW;
    if (ball.vx < 0 && ball.x < lx + PW && ball.y > left.y && ball.y < left.y + PH) ball.vx *= -1.02;
    if (ball.vx > 0 && ball.x > rx && ball.y > right.y && ball.y < right.y + PH) ball.vx *= -1.02;
    if (ball.x < -20 || ball.x > W + 20) { ball.x = W / 2; ball.y = H / 2; ball.vx = Math.sign(ball.vx) * -3.2; }

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "rgba(226,226,226,0.5)";
    for (let y = 0; y < H; y += 28) ctx.fillRect(W / 2 - 2, y, 4, 14);
    ctx.fillStyle = "#E2E2E2";
    ctx.fillRect(lx, left.y, PW, PH);
    ctx.fillRect(rx, right.y, PW, PH);
    ctx.fillStyle = "#FF2E2E";
    ctx.fillRect(ball.x - 6, ball.y - 6, 12, 12);
    raf = requestAnimationFrame(step);
  };

  const onMove = (e) => { mouseY = e.clientY; };
  window.addEventListener("resize", resize);
  window.addEventListener("pointermove", onMove);
  resize(); step();

  return () => {
    cancelAnimationFrame(raf);
    window.removeEventListener("resize", resize);
    window.removeEventListener("pointermove", onMove);
  };
}