import React from "react";
import PixelFrame from "@/components/PixelFrame";
import { STAGES } from "@/lib/loopData";

export default function LoopStages() {
  return (
    <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {STAGES.map(({ n, name, Icon, owner, input, output }) => (
        <PixelFrame key={n} tone="dim" className="group hover:bg-moss transition-colors" inner="relative p-6 overflow-hidden min-h-[220px]">
          <span className="absolute inset-x-0 h-[2px] bg-moss/80 opacity-0 group-hover:opacity-100 animate-scan pointer-events-none" />
          <div className="flex items-start justify-between">
            <Icon className="h-7 w-7 text-pulse group-hover:text-moss transition-colors" />
            <span className="font-pixel text-[10px] text-platinum/40">{n}</span>
          </div>
          <p className="mt-6 font-pixel text-sm text-platinum">{name}</p>
          <p className="mt-2 font-mono text-xs uppercase tracking-[0.2em] text-pulse">owner: {owner}</p>
          <dl className="mt-4 space-y-1 font-mono text-xs text-platinum/70 md:opacity-0 md:translate-y-2 md:group-hover:opacity-100 md:group-hover:translate-y-0 transition-all duration-300">
            <div><dt className="inline text-moss">in </dt><dd className="inline">{input}</dd></div>
            <div><dt className="inline text-moss">out </dt><dd className="inline">{output}</dd></div>
          </dl>
        </PixelFrame>
      ))}
    </div>
  );
}