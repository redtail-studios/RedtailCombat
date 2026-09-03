import React from "react";
import SectionHeader from "@/components/SectionHeader";
import AmbientPong from "@/components/games/AmbientPong";
import AboutBlock from "@/components/lore/AboutBlock";
import MissionBlock from "@/components/lore/MissionBlock";
import FaqBlock from "@/components/lore/FaqBlock";
import MachineReadable from "@/components/lore/MachineReadable";
import CommandLine from "@/components/lore/CommandLine";
import LoreConsole from "@/components/lore/console/LoreConsole";
import { useGameMode } from "@/lib/GameModeContext";

export default function Lore() {
  const { gameMode } = useGameMode();
  return (
    <div className="relative pt-28 sm:pt-32 pb-24">
      {gameMode && <AmbientPong />}
      <div className="relative z-10 mx-auto max-w-4xl px-4 sm:px-6 space-y-20 sm:space-y-24">
        <SectionHeader
          eyebrow="the terminal"
          title="THE LORE"
          sub="200 OK · agent-friendly · view-source:redtail.md. Everything an investor, a hire, or a scraper needs — in plain text. Move your mouse to play the wall."
        />
        <AboutBlock />
        <MissionBlock />
        <section className="space-y-6 scroll-mt-32">
          <h2 className="font-pixel text-lg sm:text-2xl text-platinum"><span className="text-pulse">##</span>/console</h2>
          <LoreConsole />
        </section>
        <FaqBlock />
        <MachineReadable />
        <CommandLine />
      </div>
    </div>
  );
}