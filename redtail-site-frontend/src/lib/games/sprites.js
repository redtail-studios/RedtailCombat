// Redtail logo, line-art: three outlined feathers stepping down-right into a head with a dot eye and a flat belly.
export const BIRD = [
  "..rrrrrrrr..............",
  "..r.......rr............",
  "...r........r...........",
  "....rrrrrrrrrrrr........",
  "....r...........rr......",
  ".....r............r.....",
  "......rrrrrrrrrrrrrrr...",
  "......r.............rr..",
  ".......r..........r...r.",
  "........r.........r..r.r",
  ".........r........r....r",
  "..........r.......r....r",
  "...........rrrrrrrrrrrrr",
];

// Original "noise" sprites: glitched static blocks, not creatures.
export const INVADER_A = [
  "gg..gggg..",
  "..gggg..gg",
  "gggg..gggg",
  "g..gggggg.",
  ".gggg..ggg",
  "ggg.gggg..",
  "..gggg..gg",
  "gg..gg..g.",
];

export const INVADER_B = [
  "..gggg..gg",
  "gggg..gggg",
  "g..gggg..g",
  ".gggggggg.",
  "ggg..gg.gg",
  "..gggg..gg",
  "gg..gggg..",
  ".g..gg..gg",
];

export const SHIP = [
  "....r....",
  "...rrr...",
  "..rrrrr..",
  ".rrwwwrr.",
  "rrrrrrrrr",
  "r.rr.rr.r",
];

export const COLORS = { b: "#2B2B33", w: "#E2E2E2", k: "#FF2E2E", r: "#FF2E2E", g: "#B4FF39" };

export function drawSprite(ctx, rows, x, y, px, cols = COLORS) {
  for (let j = 0; j < rows.length; j++) {
    const row = rows[j];
    for (let i = 0; i < row.length; i++) {
      const c = row[i];
      if (c === ".") continue;
      ctx.fillStyle = cols[c];
      ctx.fillRect(Math.round(x + i * px), Math.round(y + j * px), px, px);
    }
  }
}