import React from "react";
import { Loader2, Wand2 } from "lucide-react";
import ConsoleStatusPanel from "@/components/lore/console/ConsoleStatusPanel";

const dashBtn = "flex items-center gap-2 px-4 py-2.5 font-mono text-xs font-medium bg-pulse text-ink hover:opacity-90 disabled:opacity-30 disabled:pointer-events-none transition-opacity pixel-clip-sm";
const ghostBtn = "flex items-center gap-2 px-4 py-2.5 font-mono text-xs border border-white/10 text-platinum/60 hover:text-platinum hover:border-white/20 transition-colors pixel-clip-sm";

export default function RedesignPanel({ year, file, onFileChange, redesignState, onGenerate, onDownload, onBack }) {
  return (
    <div>
      <button onClick={onBack} className="flex items-center gap-2 font-mono text-xs border border-white/10 text-platinum/60 hover:text-platinum hover:border-white/20 px-3 py-2 mb-4 pixel-clip-sm">
        ← Back to report
      </button>
      <div className="bg-panel border border-white/5 p-5 pixel-clip">
        <div className="flex items-center gap-2 mb-1">
          <Wand2 className="w-3.5 h-3.5 text-pulse" />
          <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">Redesign a game</span>
        </div>
        <h2 className="font-pixel text-sm text-platinum mb-3">Upload a design doc → Lore redesigns it from the analysis</h2>
        <p className="font-mono text-xs text-platinum/40 mb-4">
          Applies the <b className="text-platinum">{year}</b> player-signal analysis and renders concept images of the modified game with OpenAI.
        </p>
        <div className="border border-dashed border-white/10 bg-ink p-4 flex items-center justify-between flex-wrap gap-3 mb-4 pixel-clip-sm">
          <p className="font-mono text-xs text-platinum/50">
            {file ? <>Selected: <b className="text-platinum">{file.name}</b></> : "No file selected — pick a game design PDF"}
          </p>
          <label className="font-mono text-[10px] font-medium uppercase tracking-wider border border-white/10 bg-panel px-3 py-2 cursor-pointer hover:border-white/20 pixel-clip-sm">
            Choose PDF
            <input type="file" accept="application/pdf" className="hidden" onChange={(e) => onFileChange(e.target.files[0] || null)} />
          </label>
        </div>
        <div className="flex justify-end">
          <button onClick={onGenerate} disabled={!file || redesignState.status === "loading"} className={dashBtn}>
            {redesignState.status === "loading" ? (<><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating…</>) : "Generate images with OpenAI"}
          </button>
        </div>

        {redesignState.status === "idle" && <ConsoleStatusPanel icon="🎮" title="No redesign yet" subtitle="Upload a PDF, then generate" />}
        {redesignState.status === "loading" && <ConsoleStatusPanel icon="🎮" blink title={`Redesigning ${file?.name || ""}…`} subtitle={`analysing → designing → rendering (30–90s) — ${redesignState.elapsed}s elapsed…`} />}
        {redesignState.status === "error" && <ConsoleStatusPanel icon="⚠" error title="Redesign failed" subtitle={redesignState.error} />}
        {redesignState.status === "done" && (
          <div className="mt-4">
            <div className="font-body font-bold text-lg border-l-4 border-pulse pl-4 mb-5 text-platinum">{redesignState.headline}</div>
            <div className="grid sm:grid-cols-2 gap-4">
              {(redesignState.modifications || []).map((m, i) => (
                <div key={i} className="bg-ink border border-white/10 overflow-hidden flex flex-col pixel-clip-sm">
                  {m.image_b64 ? (
                    <img src={`data:image/png;base64,${m.image_b64}`} alt={`feature ${i + 1}`} className="w-full block border-b border-white/10" />
                  ) : (
                    <div className="p-4 text-platinum/40 text-sm italic">image not generated</div>
                  )}
                  <div className="p-4">
                    <div className="font-mono text-sm font-bold text-pulse mb-1.5">{i + 1}. {m.change}</div>
                    <div className="font-mono text-[10px] text-platinum/40 mb-2">↳ signal: {m.finding}</div>
                    <div className="text-platinum/70 text-sm">{m.why}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-4">
              <button onClick={onDownload} className={ghostBtn}>Download report</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
