import React from 'react';
import { useLoreConsole } from '@/lib/useLoreConsole';
import ReportPanel from '@/components/dashboard/analyze/ReportPanel';
import RedesignPanel from '@/components/dashboard/analyze/RedesignPanel';

export default function Analyze() {
  const c = useLoreConsole();

  return (
    <div className="px-6 py-6 max-w-5xl mx-auto">
      <h1 className="font-pixel text-base text-platinum mb-2">Analyse a game</h1>
      <p className="font-mono text-xs text-platinum/40 mb-6">
        Real market analysis, live via Claude — pick years or upload your game, then redesign it from the findings.
      </p>

      {c.view === 'redesign' ? (
        <RedesignPanel
          year={c.rdYear}
          file={c.redesignFile}
          onFileChange={c.setRedesignFile}
          redesignState={c.redesignState}
          onGenerate={c.genRedesign}
          onDownload={c.downloadRedesign}
          onBack={() => c.setView('console')}
        />
      ) : (
        <ReportPanel
          availYears={c.availYears}
          activeTab={c.activeTab}
          onTabChange={c.setActiveTab}
          rMode={c.rMode}
          onModeChange={c.setRMode}
          analyseSel={c.analyseSel}
          backSel={c.backSel}
          valSel={c.valSel}
          onToggleAnalyse={c.onToggleAnalyse}
          onToggleBack={c.onToggleBack}
          onToggleVal={c.onToggleVal}
          repMeta={c.repMeta}
          repDisabled={c.repDisabled}
          reportState={c.reportState}
          onGenerateReport={c.genReport}
          onDownloadReport={c.downloadReport}
          onContinueToRedesign={() => c.setView('redesign')}
          gameFile={c.gameFile}
          onGameFileChange={c.setGameFile}
          gameSel={c.gameSel}
          onToggleGame={c.onToggleGame}
          gameRepMeta={c.gameRepMeta}
          gameRepDisabled={c.gameRepDisabled}
          gameReportState={c.gameReportState}
          onGenerateGameReport={c.genGameReport}
          onDownloadGameReport={c.downloadGameReport}
          onContinueToRedesignFromGame={c.goRedesignFromGame}
        />
      )}
    </div>
  );
}
