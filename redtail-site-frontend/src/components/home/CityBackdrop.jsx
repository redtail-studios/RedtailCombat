import React from "react";
import { Image } from "@/components/ui/image";
import { CITY_URL } from "@/lib/teamData";

// Neon signs in the skyline, as (x%, y%, radius px). Each group flickers on its own rhythm.
const SIGNS = {
  buzz: [[6, 42, 90], [19, 44, 60], [92, 54, 55], [50, 62, 100]],
  neon: [[22, 40, 55], [10, 63, 55], [80, 43, 45], [4, 48, 55]],
  flicker: [[17, 60, 40], [88, 47, 40], [30, 46, 45]],
};

const maskFor = (signs) =>
  signs.map(([x, y, r]) => `radial-gradient(circle ${r}px at ${x}% ${y}%, #000 35%, transparent 100%)`).join(",");

function LitLayer({ signs, anim, delay }) {
  const mask = maskFor(signs);
  return (
    <div
      className={`absolute inset-0 ${anim}`}
      style={{ animationDelay: delay, mixBlendMode: "screen", WebkitMaskImage: mask, maskImage: mask, willChange: "opacity" }}
    >
      <Image src={CITY_URL} alt="" className="absolute inset-0 w-full h-full brightness-150 saturate-150" />
    </div>
  );
}

export default function CityBackdrop() {
  return (
    <div className="absolute inset-0">
      <Image src={CITY_URL} alt="" className="absolute inset-0 w-full h-full opacity-50" />
      {/* the signs themselves, switched on */}
      <LitLayer signs={SIGNS.buzz} anim="animate-buzz" delay="0s" />
      <LitLayer signs={SIGNS.neon} anim="animate-neon" delay="1.7s" />
      <LitLayer signs={SIGNS.flicker} anim="animate-flicker" delay="0.6s" />
      {/* soft bloom bleeding off each sign */}
      <div className="absolute inset-0 pointer-events-none">
        {[...SIGNS.buzz, ...SIGNS.neon].map(([x, y, r], i) => (
          <span
            key={i}
            className={`absolute -translate-x-1/2 -translate-y-1/2 ${i % 2 ? "animate-neon" : "animate-buzz"}`}
            style={{
              left: `${x}%`, top: `${y}%`, width: r * 3, height: r * 2,
              animationDelay: `${(i * 0.9) % 4}s`, willChange: "opacity",
              background: `radial-gradient(ellipse at center, rgba(${i % 3 === 0 ? "255,46,46" : i % 3 === 1 ? "180,255,57" : "143,179,255"},0.28) 0%, transparent 70%)`,
            }}
          />
        ))}
      </div>
    </div>
  );
}