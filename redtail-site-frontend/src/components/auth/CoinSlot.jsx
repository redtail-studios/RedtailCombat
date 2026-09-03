import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

// Attract screen → drop a coin → CRT power-on → reveal the cabinet.
export default function CoinSlot({ children }) {
  const [phase, setPhase] = useState(() => (sessionStorage.getItem("rt-credit") ? "on" : "attract"));

  useEffect(() => {
    if (phase !== "attract") return;
    const kd = (e) => { if (["Space", "Enter"].includes(e.code)) { e.preventDefault(); insert(); } };
    window.addEventListener("keydown", kd);
    return () => window.removeEventListener("keydown", kd);
  }, [phase]);

  const insert = () => {
    if (phase !== "attract") return;
    setPhase("drop");
    setTimeout(() => setPhase("boot"), 700);
    setTimeout(() => { sessionStorage.setItem("rt-credit", "1"); setPhase("on"); }, 1500);
  };

  if (phase === "on") return children;

  return (
    <button type="button" onClick={insert} className="relative w-full aspect-[4/5] max-h-[560px] bg-ink text-left cursor-pointer focus:outline-none" aria-label="Insert coin to continue">
      <AnimatePresence>
        {phase !== "boot" && (
          <motion.div key="attract" exit={{ opacity: 0 }} className="absolute inset-0 flex flex-col items-center justify-center gap-8 px-6 text-center">
            <p className="font-pixel text-[10px] tracking-[0.3em] text-platinum/50">CREDITS {phase === "drop" ? 1 : 0}</p>
            <h2 className="font-pixel text-xl sm:text-2xl leading-relaxed text-pulse text-glow-red animate-blink">INSERT COIN</h2>
            <div className="relative w-16 h-24">
              <div className="absolute inset-x-0 bottom-0 h-8 bg-panel border-2 border-white/15 pixel-clip-sm" />
              <div className="absolute left-1/2 -translate-x-1/2 bottom-3 w-9 h-2 bg-ink" />
              <AnimatePresence>
                {phase === "drop" && (
                  <motion.div key="coin" initial={{ y: -40, opacity: 1, rotate: 0 }} animate={{ y: 62, rotate: 180, scaleX: [1, 0.3, 1, 0.3] }} transition={{ duration: 0.65, ease: "easeIn" }} className="absolute left-1/2 -translate-x-1/2 top-0 w-8 h-8 rounded-full bg-[#FFC93C] border-4 border-[#B8860B]" />
                )}
              </AnimatePresence>
            </div>
            <p className="font-mono text-xs uppercase tracking-[0.25em] text-platinum/60">click or press space</p>
          </motion.div>
        )}
        {phase === "boot" && (
          <motion.div key="boot" initial={{ scaleY: 0.004, scaleX: 0.6, opacity: 1 }} animate={{ scaleY: [0.004, 0.004, 1], scaleX: [0.6, 1, 1], opacity: 1 }} transition={{ duration: 0.75, times: [0, 0.5, 1], ease: "easeOut" }} className="absolute inset-0 bg-platinum/90 mix-blend-screen" />
        )}
      </AnimatePresence>
    </button>
  );
}