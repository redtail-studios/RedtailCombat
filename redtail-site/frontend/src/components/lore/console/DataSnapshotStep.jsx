import React from "react";
import PixelFrame from "@/components/PixelFrame";
import PixelButton from "@/components/PixelButton";
import YearChips from "@/components/lore/console/YearChips";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const TICK_TONE = {
  done: "bg-moss text-ink",
  running: "bg-[#f2b441] text-ink animate-spin",
  error: "bg-pulse text-white",
  idle: "bg-white/10 text-platinum/40",
};

function tickGlyph(state) {
  if (state === "done") return "✓";
  if (state === "error") return "!";
  if (state === "running") return "⟳";
  if (state === "empty") return "–";
  return "·";
}

export default function DataSnapshotStep({
  scrapedAt, yearsScraped, scrapeYears, scrapeYear, onPickScrapeYear,
  platforms, scrapeStatus, scrapeMeta, scrapeRunning, scrapeStarting, onStartScrape,
}) {
  return (
    <PixelFrame tone="dim" inner="p-6 sm:p-8">
      <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-pulse mb-3">▸ Step 1 — Data snapshot</p>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-2">
        <h3 className="font-body font-bold text-lg text-platinum">Collected market data</h3>
        <p className="font-mono text-xs uppercase tracking-wider text-platinum/60">
          Last scraped <b className="text-moss">{scrapedAt || "—"}</b>
        </p>
      </div>
      <p className="text-platinum/70 mb-4">
        Scraped sources are cached with a 1-week freshness window for the current year — stale or missing sources get re-scraped in the background. Analysis below runs on this snapshot.
      </p>
      <p className="font-mono text-xs uppercase tracking-wider text-platinum/60 mb-4">
        {yearsScraped.length ? <>Scraped from <b className="text-moss">{yearsScraped.join(", ")}</b></> : "No scraped data yet"}
      </p>

      <div className="border-t border-white/10 pt-4">
        <div className="mb-2">
          <YearChips years={scrapeYears} selected={[scrapeYear]} onToggle={onPickScrapeYear} />
        </div>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <p className="font-mono text-xs uppercase tracking-wider text-platinum/60">{scrapeMeta}</p>
          <PixelButton variant="ghost" onClick={onStartScrape} disabled={scrapeRunning || scrapeStarting} className="text-[10px]">
            {(scrapeRunning || scrapeStarting) ? (<><Loader2 className="w-3.5 h-3.5 animate-spin" /> Scraping…</>) : "⟳ Scrape now"}
          </PixelButton>
        </div>
        {platforms.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-4">
            {platforms.map((p) => {
              const state = scrapeStatus[p.id] || "idle";
              return (
                <div key={p.id} className="flex items-center gap-2.5 bg-ink border border-white/10 px-3 py-2.5">
                  <span className={cn("w-5 h-5 rounded-full flex items-center justify-center text-xs font-black flex-shrink-0", TICK_TONE[state] || TICK_TONE.idle)}>
                    {tickGlyph(state)}
                  </span>
                  <span className="font-mono text-xs font-semibold text-platinum">{p.icon ? `${p.icon} ` : ""}{p.name}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </PixelFrame>
  );
}
