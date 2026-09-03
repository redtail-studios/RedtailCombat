import React from "react";
import { Image } from "@/components/ui/image";

export default function Roster({ items, onOpen, lockedHint }) {
  return (
    <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
      {items.map((it) =>
        it.collected ? (
          <button key={it.key} onClick={() => onOpen(it)} className="group text-left p-[2px] bg-moss pixel-clip-sm hover:bg-pulse transition-colors">
            <div className="bg-panel pixel-clip-sm flex items-center gap-2 p-2 h-full">
              {it.portrait ? (
                <Image src={it.portrait} alt={it.label} className="h-10 w-10 shrink-0 crisp" />
              ) : (
                <span className="h-10 w-10 shrink-0 bg-ink flex items-center justify-center font-pixel text-[10px] text-moss">{it.tag}</span>
              )}
              <div className="min-w-0">
                <p className="font-pixel text-[8px] text-platinum truncate">{it.label}</p>
                <p className="font-mono text-[10px] uppercase tracking-wider text-pulse truncate">{it.sub}</p>
              </div>
            </div>
          </button>
        ) : (
          <div key={it.key} className="p-[2px] bg-white/10 pixel-clip-sm">
            <div className="bg-panel/60 pixel-clip-sm flex items-center gap-2 p-2 h-full">
              <span className="h-10 w-10 shrink-0 bg-ink flex items-center justify-center font-pixel text-[10px] text-platinum/30">?</span>
              <div className="min-w-0">
                <p className="font-pixel text-[8px] text-platinum/40">{it.tag}</p>
                <p className="font-mono text-[10px] text-platinum/30 truncate">{lockedHint}</p>
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
}