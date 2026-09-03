import React from "react";
import { cn } from "@/lib/utils";

export default function YearChips({ years, selected, onToggle, disabledYears = [] }) {
  return (
    <div className="flex flex-wrap gap-2 mb-2">
      {years.map((y) => {
        const isSel = selected.includes(y);
        const isDis = disabledYears.includes(y);
        return (
          <button
            key={y}
            type="button"
            disabled={isDis}
            onClick={() => onToggle(y)}
            className={cn(
              "font-mono text-sm font-semibold border-2 px-4 py-2 transition-transform",
              isSel ? "bg-pulse text-ink border-pulse" : "bg-panel text-platinum border-white/20 hover:-translate-y-0.5",
              isDis && "opacity-30 cursor-not-allowed hover:translate-y-0"
            )}
          >
            {y}
          </button>
        );
      })}
    </div>
  );
}
