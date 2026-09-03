import React from "react";
import PixelFrame from "@/components/PixelFrame";
import PixelButton from "@/components/PixelButton";
import ConsoleStatusPanel from "@/components/lore/console/ConsoleStatusPanel";
import { Loader2 } from "lucide-react";

export default function RedesignStep({ year, file, onFileChange, redesignState, onGenerate, onDownload, onBack }) {
  return (
    <div>
      <button onClick={onBack} className="font-mono text-xs font-semibold uppercase tracking-wider border-2 border-white/20 bg-panel px-4 py-2 mb-5 hover:border-pulse">
        ← Back to report
      </button>
      <PixelFrame tone="red" inner="p-6 sm:p-8">
        <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-pulse mb-3">▸ Step 3 — Redesign a game</p>
        <h3 className="font-body font-bold text-lg text-platinum mb-1">Upload a game design doc → Lore redesigns it from the analysis</h3>
        <p className="text-platinum/70 mb-4">
          Upload any game's design document (PDF). Lore applies the <b className="text-platinum">{year}</b> player-signal analysis and renders concept images of the modified game with OpenAI.
        </p>
        <div className="border-2 border-dashed border-white/20 bg-ink p-5 flex items-center justify-between flex-wrap gap-3 mb-4">
          <p className="font-mono text-xs text-platinum/60">
            {file ? <>Selected: <b className="text-platinum">{file.name}</b></> : "No file selected — pick a game design PDF"}
          </p>
          <label className="font-mono text-xs font-semibold uppercase tracking-wider border-2 border-white/20 bg-panel px-4 py-2 cursor-pointer hover:border-pulse">
            Choose PDF
            <input type="file" accept="application/pdf" className="hidden" onChange={(e) => onFileChange(e.target.files[0] || null)} />
          </label>
        </div>
        <div className="flex justify-end">
          <PixelButton onClick={onGenerate} disabled={!file || redesignState.status === "loading"}>
            {redesignState.status === "loading" ? (<><Loader2 className="w-4 h-4 animate-spin" /> Generating…</>) : "✦ Generate images with OpenAI"}
          </PixelButton>
        </div>

        {(redesignState.status === "idle") && (
          <ConsoleStatusPanel icon="🎮" title="No redesign yet" subtitle="Upload a PDF, then generate" />
        )}
        {redesignState.status === "loading" && (
          <ConsoleStatusPanel icon="🎮" blink title={`Redesigning ${file?.name || ""}…`} subtitle={`analysing → designing → rendering (30–90s) — ${redesignState.elapsed}s elapsed…`} />
        )}
        {redesignState.status === "error" && (
          <ConsoleStatusPanel icon="⚠" error title="Redesign failed" subtitle={redesignState.error} />
        )}
        {redesignState.status === "done" && (
          <div className="mt-4">
            <div className="font-body font-bold text-lg border-l-4 border-pulse pl-4 mb-5">{redesignState.headline}</div>
            <div className="grid sm:grid-cols-2 gap-5">
              {(redesignState.modifications || []).map((m, i) => (
                <div key={i} className="bg-ink border-2 border-white/20 overflow-hidden flex flex-col">
                  {m.image_b64 ? (
                    <img src={`data:image/png;base64,${m.image_b64}`} alt={`feature ${i + 1}`} className="w-full block border-b-2 border-white/20" />
                  ) : (
                    <div className="p-4 text-platinum/50 text-sm italic">image not generated</div>
                  )}
                  <div className="p-4">
                    <div className="font-body font-bold text-pulse mb-1.5">{i + 1}. {m.change}</div>
                    <div className="font-mono text-xs text-platinum/60 mb-2">↳ signal: {m.finding}</div>
                    <div className="text-platinum/85 text-sm">{m.why}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-5">
              <PixelButton variant="ghost" onClick={onDownload} className="text-[10px]">⬇ Download report</PixelButton>
            </div>
          </div>
        )}
      </PixelFrame>
    </div>
  );
}
