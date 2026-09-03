import React from "react";
import { cn } from "@/lib/utils";

export default function SectionHeader({ eyebrow, title, sub, tone = "red", className }) {
  return (
    <div className={cn("space-y-4", className)}>
      <p className={cn("font-mono text-xs uppercase tracking-[0.3em]", tone === "moss" ? "text-moss" : "text-pulse")}>
        <span className="mr-2">■</span>{eyebrow}
      </p>
      <h2 className="font-pixel text-xl sm:text-2xl md:text-3xl leading-[1.5] text-platinum">{title}</h2>
      {sub && <p className="max-w-2xl text-platinum/70 text-base md:text-lg">{sub}</p>}
    </div>
  );
}