import React from "react";
import { motion } from "framer-motion";

// Arcade cabinet bezel: marquee on top, CRT screen with scanlines, control deck below.
export default function Cabinet({ title, subtitle, children }) {
  return (
    <div className="p-[2px] bg-pulse pixel-clip shadow-[0_0_60px_rgba(255,46,46,0.25)]">
      <div className="bg-panel pixel-clip">
        <div className="px-6 py-4 bg-ink border-b-2 border-pulse/60 text-center">
          <h1 className="font-pixel text-base sm:text-xl leading-relaxed text-platinum text-glow-red">{title}</h1>
          {subtitle && <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.25em] text-moss">{subtitle}</p>}
        </div>
        <div className="p-3 sm:p-4 bg-[#1c1c22]">
          <motion.div initial={{ opacity: 0, filter: "brightness(3)" }} animate={{ opacity: 1, filter: "brightness(1)" }} transition={{ duration: 0.5 }} className="relative bg-ink border-2 border-white/10 scanlines overflow-hidden">
            <div className="flex items-center justify-between px-4 pt-3 font-pixel text-[8px] tracking-widest text-platinum/50">
              <span className="text-moss">PLAYER 1</span>
              <span>CREDITS 1</span>
            </div>
            <div className="p-5 sm:p-7">{children}</div>
          </motion.div>
        </div>
        <div className="flex items-center justify-center gap-6 px-6 py-4 bg-ink border-t-2 border-white/10">
          <span className="h-5 w-5 rounded-full bg-pulse shadow-[0_0_12px_rgba(255,46,46,0.7)]" />
          <span className="h-5 w-5 rounded-full bg-moss shadow-[0_0_12px_rgba(180,255,57,0.7)]" />
          <span className="h-5 w-5 rounded-full bg-ghost shadow-[0_0_12px_rgba(143,179,255,0.7)]" />
          <span className="ml-4 h-2 w-14 bg-white/10 pixel-clip-sm" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}