import React, { useState } from "react";
import { Crosshair } from "lucide-react";
import SectionHeader from "@/components/SectionHeader";
import PixelButton from "@/components/PixelButton";
import SignalGame from "@/components/games/SignalGame";
import LoopStages from "@/components/agents/LoopStages";
import WhatWeDoList from "@/components/agents/WhatWeDoList";
import TeamTable from "@/components/agents/TeamTable";
import AboutBlock from "@/components/lore/AboutBlock";
import FaqBlock from "@/components/lore/FaqBlock";
import MachineReadable from "@/components/lore/MachineReadable";
import { useGameMode } from "@/lib/GameModeContext";

export default function Agents() {
  const { gameMode } = useGameMode();
  const [playing, setPlaying] = useState(false);

  return (
    <div className="pt-28 sm:pt-32 pb-24 bit-grid">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-20 sm:space-y-28">
        <section className="space-y-10">
          <SectionHeader
            tone="moss"
            eyebrow="the arsenal"
            title="THE AGENTS"
            sub="An AI-native mobile game studio. Agents pick the games. Humans ship them."
          />
          <p className="font-mono text-base sm:text-lg text-platinum/70 max-w-2xl -mt-4">
            Agents scan the noise of the internet — forums, store reviews, creator content — and catch the real signal. Play to free each stage of the loop from the noise.
          </p>
          {gameMode && !playing && (
            <PixelButton variant="moss" onClick={() => setPlaying(true)}>
              <Crosshair className="h-4 w-4" /> Free the signal
            </PixelButton>
          )}
          {gameMode && playing && (
            <div className="max-w-5xl">
              <SignalGame onExit={() => setPlaying(false)} />
            </div>
          )}
        </section>

        <section className="space-y-10">
          <SectionHeader
            eyebrow="/what-we-do"
            title="THE LOOP"
            sub="An end-to-end intelligence loop. Six stages. Agents do four of them. Humans do one. Everyone learns. Hover a chamber to scan it."
          />
          <LoopStages />
          <WhatWeDoList />
          <p className="font-mono text-sm text-platinum/60 max-w-2xl">
            thesis: <span className="text-moss">behavioral intelligence &gt; creative guessing</span>. We don't guess what people want to play — we measure it, prototype it, and let agents play it against each other before a human writes a line of production code.
          </p>
        </section>

        <div className="max-w-4xl space-y-20 sm:space-y-24">
          <AboutBlock />
          <TeamTable />
          <FaqBlock />
          <MachineReadable />
        </div>
      </div>
    </div>
  );
}