import React from "react";
import { cn } from "@/lib/utils";

export default function ToggleGroup({ options, value, onChange, className }) {
  return (
    <div className={cn("inline-flex border-2 border-white/20 overflow-hidden mb-4", className)}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={cn(
            "font-mono text-xs font-semibold uppercase tracking-wider px-4 py-2.5 transition-colors",
            value === o.value ? "bg-platinum text-ink" : "bg-panel text-platinum/70 hover:text-platinum"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
