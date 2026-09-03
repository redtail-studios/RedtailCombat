import React from "react";
import PixelFrame from "@/components/PixelFrame";
import PixelButton from "@/components/PixelButton";
import YearChips from "@/components/lore/console/YearChips";
import ToggleGroup from "@/components/lore/console/ToggleGroup";
import ConsoleStatusPanel from "@/components/lore/console/ConsoleStatusPanel";
import { Loader2 } from "lucide-react";

export default function ReportStep({
  availYears, activeTab, onTabChange,
  rMode, onModeChange, analyseSel, backSel, valSel, onToggleAnalyse, onToggleBack, onToggleVal,
  repMeta, repDisabled, reportState, onGenerateReport, onDownloadReport, onContinueToRedesign,
  gameFile, onGameFileChange, gameSel, onToggleGame, gameRepMeta, gameRepDisabled,
  gameReportState, onGenerateGameReport, onDownloadGameReport, onContinueToRedesignFromGame,
}) {
  return (
    <PixelFrame tone="dim" inner="p-6 sm:p-8">
      <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-pulse mb-3">▸ Step 2 — Intelligence report (live)</p>
      <h3 className="font-body font-bold text-lg text-platinum mb-1">Analyse the market, or analyse your own game</h3>
      <p className="text-platinum/70 mb-4">
        Claude reads the snapshot and writes a fresh report, live — either a general market-gap report, or your own game analysed against the same data.
      </p>

      <ToggleGroup
        options={[{ value: "market", label: "Market report" }, { value: "game", label: "Analyse your game" }]}
        value={activeTab}
        onChange={onTabChange}
      />

      {activeTab === "market" ? (
        <div>
          <ToggleGroup
            options={[{ value: "analyse", label: "Analyse years" }, { value: "backtest", label: "Backtest + validate" }]}
            value={rMode}
            onChange={onModeChange}
          />
          {rMode === "analyse" ? (
            <div>
              <p className="font-mono text-xs font-bold uppercase tracking-wider text-platinum/60 mb-2">Years to analyse</p>
              <YearChips years={availYears} selected={analyseSel} onToggle={onToggleAnalyse} />
            </div>
          ) : (
            <div>
              <p className="font-mono text-xs font-bold uppercase tracking-wider text-platinum/60 mb-2">
                Backtest period <span className="text-pulse/80 text-[10px] border border-pulse/40 rounded-full px-2 py-0.5 ml-1">historical signals</span>
              </p>
              <YearChips years={availYears} selected={backSel} onToggle={onToggleBack} disabledYears={valSel} />
              <p className="font-mono text-xs font-bold uppercase tracking-wider text-platinum/60 mb-2 mt-3">
                Validation period <span className="text-pulse/80 text-[10px] border border-pulse/40 rounded-full px-2 py-0.5 ml-1">what actually happened</span>
              </p>
              <YearChips years={availYears} selected={valSel} onToggle={onToggleVal} disabledYears={backSel} />
            </div>
          )}
          <div className="flex items-center justify-between flex-wrap gap-3 mt-3">
            <p className="font-mono text-xs uppercase tracking-wider text-platinum/60">{repMeta}</p>
            <PixelButton onClick={onGenerateReport} disabled={repDisabled || reportState.status === "loading"} className="text-[10px]">
              {reportState.status === "loading" ? (<><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating…</>) : "✦ Generate report"}
            </PixelButton>
          </div>

          {reportState.status === "idle" && (
            <ConsoleStatusPanel icon="✦" title="No report yet" subtitle="Runs live via Claude — ~3–5 min" />
          )}
          {reportState.status === "loading" && (
            <ConsoleStatusPanel icon="✦" blink title={`Lore is analysing ${reportState.label}…`} subtitle={`${reportState.elapsed}s elapsed…`} />
          )}
          {reportState.status === "error" && (
            <ConsoleStatusPanel icon="⚠" error title="Report failed" subtitle={reportState.error} />
          )}
          {reportState.status === "done" && (
            <>
              <div className="border-2 border-white/20 mt-4">
                <iframe title="Report" srcDoc={reportState.html} className="w-full h-[860px] border-0 block bg-black" />
              </div>
              <div className="flex justify-end gap-3 mt-4">
                <PixelButton variant="ghost" onClick={onDownloadReport} className="text-[10px]">⬇ Download report</PixelButton>
                <PixelButton onClick={onContinueToRedesign} className="text-[10px]">Continue to redesign ▸</PixelButton>
              </div>
            </>
          )}
        </div>
      ) : (
        <div>
          <p className="text-platinum/70 mb-4">Upload your game's design doc (PDF) and pick which years of market data to analyse it against.</p>
          <div className="border-2 border-dashed border-white/20 bg-ink p-5 flex items-center justify-between flex-wrap gap-3 mb-4">
            <p className="font-mono text-xs text-platinum/60">
              {gameFile ? <>Selected: <b className="text-platinum">{gameFile.name}</b></> : "No file selected — pick a game design PDF"}
            </p>
            <label className="font-mono text-xs font-semibold uppercase tracking-wider border-2 border-white/20 bg-panel px-4 py-2 cursor-pointer hover:border-pulse">
              Choose PDF
              <input type="file" accept="application/pdf" className="hidden" onChange={(e) => onGameFileChange(e.target.files[0] || null)} />
            </label>
          </div>
          <p className="font-mono text-xs font-bold uppercase tracking-wider text-platinum/60 mb-2">Years to analyse</p>
          <YearChips years={availYears} selected={gameSel} onToggle={onToggleGame} />
          <div className="flex items-center justify-between flex-wrap gap-3 mt-3">
            <p className="font-mono text-xs uppercase tracking-wider text-platinum/60">{gameRepMeta}</p>
            <PixelButton onClick={onGenerateGameReport} disabled={gameRepDisabled || gameReportState.status === "loading"} className="text-[10px]">
              {gameReportState.status === "loading" ? (<><Loader2 className="w-3.5 h-3.5 animate-spin" /> Analysing…</>) : "✦ Analyse my game"}
            </PixelButton>
          </div>

          {gameReportState.status === "idle" && (
            <ConsoleStatusPanel icon="🎮" title="No report yet" subtitle="Runs live via Claude — ~3–5 min" />
          )}
          {gameReportState.status === "loading" && (
            <ConsoleStatusPanel icon="🎮" blink title={`Lore is analysing your game against ${gameReportState.label}…`} subtitle={`${gameReportState.elapsed}s elapsed…`} />
          )}
          {gameReportState.status === "error" && (
            <ConsoleStatusPanel icon="⚠" error title="Report failed" subtitle={gameReportState.error} />
          )}
          {gameReportState.status === "done" && (
            <>
              <div className="border-2 border-white/20 mt-4">
                <iframe title="Game report" srcDoc={gameReportState.html} className="w-full h-[860px] border-0 block bg-black" />
              </div>
              <div className="flex justify-end gap-3 mt-4">
                <PixelButton variant="ghost" onClick={onDownloadGameReport} className="text-[10px]">⬇ Download report</PixelButton>
                <PixelButton onClick={onContinueToRedesignFromGame} className="text-[10px]">Continue to redesign ▸</PixelButton>
              </div>
            </>
          )}
        </div>
      )}
    </PixelFrame>
  );
}
