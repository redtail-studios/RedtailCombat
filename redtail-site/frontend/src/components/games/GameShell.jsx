import React from "react";
import { X } from "lucide-react";

export default function GameShell({ title, hint, status, info, best, collectLabel = "CREW", completeText = "COMPLETE", aspect = "aspect-video", onExit, children }) {
  const overlay = status === "ready" || status === "over" || status === "complete";
  return (
    <div className="p-[2px] bg-pulse pixel-clip shadow-[0_0_40px_rgba(255,46,46,0.25)]">
      <div className={`relative w-full ${aspect} bg-ink pixel-clip overflow-hidden cursor-crosshair scanlines`}>
        {children}
        <div className="absolute top-0 inset-x-0 flex items-center justify-between px-3 sm:px-4 py-2 sm:py-3 font-pixel text-[8px] sm:text-[10px] text-platinum pointer-events-none">
          <span className="text-pulse">{title}</span>
          <span className="text-right">
            SCORE {info.score} · BEST {best}
            {info.lives != null && <> · LIVES {info.lives}</>}
            {info.total != null && <> · <span className="text-moss">{collectLabel} {info.collected}/{info.total}</span></>}
          </span>
        </div>
        <button
          onClick={onExit}
          className="absolute bottom-2 right-2 z-10 inline-flex items-center gap-1 bg-panel/90 px-2 py-1.5 font-pixel text-[8px] text-platinum hover:bg-pulse hover:text-ink pixel-clip-sm"
        >
          EXIT <X className="h-3 w-3" />
        </button>
        {overlay && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-center px-6 pointer-events-none bg-ink/40">
            {status === "over" ? (
              <>
                <p className="font-pixel text-base sm:text-2xl text-pulse text-glow-red">GAME OVER</p>
                <p className="font-mono text-xs sm:text-sm text-platinum/80">score {info.score} · click or press space to retry</p>
              </>
            ) : status === "complete" ? (
              <>
                <p className="font-pixel text-base sm:text-2xl text-moss text-glow-moss">{completeText}</p>
                <p className="font-mono text-xs sm:text-sm text-platinum/80">score {info.score} · tap a slot below to revisit · click to play again</p>
              </>
            ) : (
              <>
                <p className="font-pixel text-sm sm:text-xl text-platinum animate-blink">CLICK TO START</p>
                <p className="font-mono text-xs sm:text-sm text-platinum/70 max-w-md">{hint}</p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}