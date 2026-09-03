import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, ChevronDown } from "lucide-react";
import PixelButton from "@/components/PixelButton";
import CrewGame from "@/components/games/CrewGame";
import CityBackdrop from "@/components/home/CityBackdrop";
import { useGameMode } from "@/lib/GameModeContext";
import { LOGO_URL } from "@/lib/teamData";

export default function Hero({ flying, onTakeOff, onExit }) {
  const { gameMode } = useGameMode();
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden scanlines bit-grid">
      {gameMode && !flying && <CityBackdrop />}
      <div className="absolute inset-0 bg-gradient-to-b from-ink/80 via-ink/30 to-ink" />
      <AnimatePresence mode="wait">
        {!flying ? (
          <motion.div
            key="hero"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 2.4, filter: "blur(12px)" }}
            transition={{ duration: 0.55, ease: [0.2, 0.8, 0.2, 1] }}
            className="relative z-10 text-center px-6 max-w-3xl pt-24 pb-16"
          >
            <img src={LOGO_URL} alt="Redtail" className="mx-auto h-20 w-20 sm:h-28 sm:w-28 object-contain drop-shadow-[0_0_28px_rgba(255,46,46,0.55)] animate-bob" />
            <h1 className="mt-8 font-pixel text-3xl sm:text-5xl md:text-6xl leading-tight text-platinum">
              RED<span className="text-pulse text-glow-red">TAIL</span>
            </h1>
            <p className="mt-5 font-mono text-xs sm:text-sm uppercase tracking-[0.35em] text-moss text-glow-moss">an ai-native game studio</p>
            <p className="mt-6 text-lg md:text-xl text-platinum/80 max-w-xl mx-auto">
              Our agents pick the games. Our humans ship them. Wanna see what we're cooking?
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-5">
              {gameMode ? (
                <PixelButton onClick={onTakeOff}><Play className="h-4 w-4 fill-current" /> Take off · meet the crew</PixelButton>
              ) : (
                <PixelButton variant="ghost" as="a" href="#team"><ChevronDown className="h-4 w-4" /> Meet the team</PixelButton>
              )}
            </div>
            <p className="mt-8 font-mono text-[11px] uppercase tracking-[0.25em] text-platinum/40">
              {gameMode ? "insert coin — steer, dodge, collect the crew" : "investor mode — text only"}
            </p>
          </motion.div>
        ) : (
          <motion.div
            key="game"
            initial={{ opacity: 0, scale: 0.55 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}
            className="relative z-10 w-full max-w-5xl px-4 pt-24 pb-12"
          >
            <CrewGame onExit={onExit} />
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}