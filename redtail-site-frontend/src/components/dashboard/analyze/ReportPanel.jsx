import React from "react";
import { Sparkles, Loader2 } from "lucide-react";
import YearChips from "@/components/lore/console/YearChips";
import ToggleGroup from "@/components/lore/console/ToggleGroup";
import ConsoleStatusPanel from "@/components/lore/console/ConsoleStatusPanel";

const dashBtn = "flex items-center gap-2 px-4 py-2.5 font-mono text-xs font-medium bg-pulse text-ink hover:opacity-90 disabled:opacity-30 disabled:pointer-events-none transition-opacity pixel-clip-sm";
const ghostBtn = "flex items-center gap-2 px-4 py-2.5 font-mono text-xs border border-white/10 text-platinum/60 hover:text-platinum hover:border-white/20 transition-colors pixel-clip-sm";

export default function ReportPanel({
  availYears, activeTab, onTabChange,
  rMode, onModeChange, analyseSel, backSel, valSel, onToggleAnalyse, onToggleBack, onToggleVal,
  repMeta, repDisabled, reportState, onGenerateReport, onDownloadReport, onContinueToRedesign,
  gameFile, onGameFileChange, gameSel, onToggleGame, gameRepMeta, gameRepDisabled,
  gameReportState, onGenerateGameReport, onDownloadGameReport, onContinueToRedesignFromGame,
}) {
  return (
    <div className="bg-panel border border-white/5 p-5 pixel-clip">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="w-3.5 h-3.5 text-pulse" />
        <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">Intelligence report — live</span>
      </div>
      <h2 className="font-pixel text-sm text-platinum mb-4">Analyse the market, or analyse your own game</h2>

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
              <p className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 mb-2">Years to analyse</p>
              <YearChips years={availYears} selected={analyseSel} onToggle={onToggleAnalyse} />
            </div>
          ) : (
            <div>
              <p className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 mb-2">Backtest period</p>
              <YearChips years={availYears} selected={backSel} onToggle={onToggleBack} disabledYears={valSel} />
              <p className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 mb-2 mt-3">Validation period</p>
              <YearChips years={availYears} selected={valSel} onToggle={onToggleVal} disabledYears={backSel} />
            </div>
          )}
          <div className="flex items-center justify-between flex-wrap gap-3 mt-3 pt-3 border-t border-white/5">
            <p className="font-mono text-xs text-platinum/40">{repMeta}</p>
            <button onClick={onGenerateReport} disabled={repDisabled || reportState.status === "loading"} className={dashBtn}>
              {reportState.status === "loading" ? (<><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating…</>) : "Generate report"}
            </button>
          </div>

          {reportState.status === "idle" && <ConsoleStatusPanel icon="✦" title="No report yet" subtitle="Runs live via Claude — ~3–5 min" />}
          {reportState.status === "loading" && <ConsoleStatusPanel icon="✦" blink title={`Analysing ${reportState.label}…`} subtitle={`${reportState.elapsed}s elapsed…`} />}
          {reportState.status === "error" && <ConsoleStatusPanel icon="⚠" error title="Report failed" subtitle={reportState.error} />}
          {reportState.status === "done" && (
            <>
              <div className="border border-white/10 mt-4 pixel-clip-sm overflow-hidden">
                <iframe title="Report" srcDoc={reportState.html} className="w-full h-[600px] border-0 block bg-black" />
              </div>
              <div className="flex justify-end gap-3 mt-4">
                <button onClick={onDownloadReport} className={ghostBtn}>Download report</button>
                <button onClick={onContinueToRedesign} className={dashBtn}>Continue to redesign</button>
              </div>
            </>
          )}
        </div>
      ) : (
        <div>
          <p className="font-mono text-xs text-platinum/40 mb-4">Upload your game's design doc (PDF) and pick which years of market data to analyse it against.</p>
          <div className="border border-dashed border-white/10 bg-ink p-4 flex items-center justify-between flex-wrap gap-3 mb-4 pixel-clip-sm">
            <p className="font-mono text-xs text-platinum/50">
              {gameFile ? <>Selected: <b className="text-platinum">{gameFile.name}</b></> : "No file selected — pick a game design PDF"}
            </p>
            <label className="font-mono text-[10px] font-medium uppercase tracking-wider border border-white/10 bg-panel px-3 py-2 cursor-pointer hover:border-white/20 pixel-clip-sm">
              Choose PDF
              <input type="file" accept="application/pdf" className="hidden" onChange={(e) => onGameFileChange(e.target.files[0] || null)} />
            </label>
          </div>
          <p className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 mb-2">Years to analyse</p>
          <YearChips years={availYears} selected={gameSel} onToggle={onToggleGame} />
          <div className="flex items-center justify-between flex-wrap gap-3 mt-3 pt-3 border-t border-white/5">
            <p className="font-mono text-xs text-platinum/40">{gameRepMeta}</p>
            <button onClick={onGenerateGameReport} disabled={gameRepDisabled || gameReportState.status === "loading"} className={dashBtn}>
              {gameReportState.status === "loading" ? (<><Loader2 className="w-3.5 h-3.5 animate-spin" /> Analysing…</>) : "Analyse my game"}
            </button>
          </div>

          {gameReportState.status === "idle" && <ConsoleStatusPanel icon="🎮" title="No report yet" subtitle="Runs live via Claude — ~3–5 min" />}
          {gameReportState.status === "loading" && <ConsoleStatusPanel icon="🎮" blink title={`Analysing your game against ${gameReportState.label}…`} subtitle={`${gameReportState.elapsed}s elapsed…`} />}
          {gameReportState.status === "error" && <ConsoleStatusPanel icon="⚠" error title="Report failed" subtitle={gameReportState.error} />}
          {gameReportState.status === "done" && (
            <>
              <div className="border border-white/10 mt-4 pixel-clip-sm overflow-hidden">
                <iframe title="Game report" srcDoc={gameReportState.html} className="w-full h-[600px] border-0 block bg-black" />
              </div>
              <div className="flex justify-end gap-3 mt-4">
                <button onClick={onDownloadGameReport} className={ghostBtn}>Download report</button>
                <button onClick={onContinueToRedesignFromGame} className={dashBtn}>Continue to redesign</button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
