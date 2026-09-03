import React from "react";
import { useDashboardAuth } from "@/lib/DashboardAuthContext";
import { useLoreConsole, SCRAPE_YEARS } from "@/lib/useLoreConsole";
import SignInGate from "@/components/lore/console/SignInGate";
import DataSnapshotStep from "@/components/lore/console/DataSnapshotStep";
import ReportStep from "@/components/lore/console/ReportStep";
import RedesignStep from "@/components/lore/console/RedesignStep";
import Glossary from "@/components/lore/console/Glossary";

export default function LoreConsole() {
  const { isDashboardAuthenticated } = useDashboardAuth();
  return isDashboardAuthenticated ? <AuthedConsole /> : <SignInGate />;
}

function AuthedConsole() {
  const c = useLoreConsole();

  return c.view === "redesign" ? (
    <RedesignStep
      year={c.rdYear}
      file={c.redesignFile}
      onFileChange={c.setRedesignFile}
      redesignState={c.redesignState}
      onGenerate={c.genRedesign}
      onDownload={c.downloadRedesign}
      onBack={() => c.setView("console")}
    />
  ) : (
    <div className="space-y-8">
      <DataSnapshotStep
        scrapedAt={c.scrapedAt}
        yearsScraped={c.availYears}
        scrapeYears={SCRAPE_YEARS}
        scrapeYear={c.scrapeYear}
        onPickScrapeYear={c.setScrapeYear}
        platforms={c.platforms}
        scrapeStatus={c.scrapeStatus.platforms}
        scrapeMeta={c.scrapeMeta}
        scrapeRunning={c.scrapeStatus.status === "running"}
        scrapeStarting={c.scrapeStarting}
        onStartScrape={c.startScrape}
      />
      <ReportStep
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
        onContinueToRedesign={() => c.setView("redesign")}
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
      <Glossary />
    </div>
  );
}
