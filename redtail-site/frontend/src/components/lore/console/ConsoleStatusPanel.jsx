import React from "react";
import { cn } from "@/lib/utils";

export default function ConsoleStatusPanel({ icon, title, subtitle, error = false, blink = false }) {
  return (
    <div className={cn("border-2 border-dashed p-8 text-center mt-4", error ? "border-pulse bg-pulse/5" : "border-white/20 bg-panel")}>
      <div className={cn("text-2xl", blink && "animate-pulse")}>{icon}</div>
      <div className={cn("font-body font-semibold mt-2", error ? "text-pulse" : "text-platinum")}>{title}</div>
      {subtitle && <div className="font-mono text-xs text-platinum/60 mt-1">{subtitle}</div>}
    </div>
  );
}
