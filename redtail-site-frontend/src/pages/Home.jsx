import React, { useState } from "react";
import Hero from "@/components/home/Hero";
import TeamText from "@/components/home/TeamText";
import { useGameMode } from "@/lib/GameModeContext";

export default function Home() {
  const { gameMode } = useGameMode();
  const [flying, setFlying] = useState(false);
  return (
    <div>
      <Hero flying={flying} onTakeOff={() => setFlying(true)} onExit={() => setFlying(false)} />
      {!gameMode && <TeamText />}
    </div>
  );
}