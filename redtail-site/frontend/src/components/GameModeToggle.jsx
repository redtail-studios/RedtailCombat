import React from "react";
import { Gamepad2 } from "lucide-react";
import { useGameMode } from "@/lib/GameModeContext";
import { cn } from "@/lib/utils";

export default function GameModeToggle() {
  const { gameMode, toggle } = useGameMode();
  return (
    <button
      onClick={toggle}
      aria-pressed={gameMode}
      title={gameMode ? "Switch to Investor Mode (text only)" : "Switch Game Mode on"}
      className="fixed bottom-4 right-4 z-50 p-[2px] bg-white/15 pixel-clip-sm"
    >
      <span className="flex items-center gap-3 bg-ink px-3 py-2 pixel-clip-sm font-pixel text-[9px] uppercase tracking-wider text-platinum">
        <Gamepad2 className={cn("h-4 w-4", gameMode ? "text-moss" : "text-platinum/40")} />
        Game Mode
        <span className={cn("px-2 py-1", gameMode ? "bg-moss text-ink" : "bg-white/10 text-platinum/60")}>
          {gameMode ? "ON" : "OFF"}
        </span>
      </span>
    </button>
  );
}