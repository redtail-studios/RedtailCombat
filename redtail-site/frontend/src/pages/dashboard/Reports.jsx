import React, { useState } from 'react';
import { FileText, Download, Eye, X } from 'lucide-react';
import { useLoreReports } from '@/lib/LoreReportsContext';
import { downloadHtml, slug } from '@/lib/loreReportUtils';

export default function Reports() {
  const { reports } = useLoreReports();
  const [viewing, setViewing] = useState(null);

  return (
    <div className="px-6 py-6 max-w-5xl mx-auto">
      <h1 className="font-pixel text-base text-platinum mb-2">Reports</h1>
      <p className="font-mono text-xs text-platinum/40 mb-6">
        Live Lore reports generated from /lore — market reports and per-game analyses land here.
      </p>

      {reports.length === 0 ? (
        <div className="border-2 border-dashed border-white/10 flex flex-col items-center justify-center py-20 text-center pixel-clip-sm">
          <FileText className="w-5 h-5 text-platinum/20 mb-3" />
          <p className="font-mono text-xs text-platinum/30">No reports yet — generate one from the Lore console.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <div key={r.id} className="flex items-center justify-between gap-4 bg-panel border border-white/5 p-4 pixel-clip-sm flex-wrap">
              <div className="min-w-0">
                <div className="font-mono text-sm text-platinum truncate">
                  {r.type === 'game' ? `Game analysis — ${r.gameName || 'uploaded game'}` : 'Market report'}
                </div>
                <div className="font-mono text-[10px] text-platinum/40 mt-1">
                  {r.label} · {new Date(r.createdAt).toLocaleString()}
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => setViewing(r)}
                  className="flex items-center gap-1.5 px-3 py-2 font-mono text-[10px] border border-white/10 text-platinum/60 hover:text-platinum hover:border-white/20 transition-colors pixel-clip-sm"
                >
                  <Eye className="w-3 h-3" /> View
                </button>
                <button
                  onClick={() => downloadHtml(r.html, `lore-${r.type}-report-${slug(r.gameName || r.label)}.html`)}
                  className="flex items-center gap-1.5 px-3 py-2 font-mono text-[10px] border border-white/10 text-platinum/60 hover:text-platinum hover:border-white/20 transition-colors pixel-clip-sm"
                >
                  <Download className="w-3 h-3" /> Download
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {viewing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-6" onClick={() => setViewing(null)}>
          <div className="bg-panel border border-white/10 w-full max-w-4xl h-[85vh] flex flex-col pixel-clip" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 flex-shrink-0">
              <span className="font-mono text-xs text-platinum/60">
                {viewing.type === 'game' ? `Game analysis — ${viewing.gameName || 'uploaded game'}` : 'Market report'}
              </span>
              <button onClick={() => setViewing(null)} className="text-platinum/40 hover:text-platinum">
                <X className="w-4 h-4" />
              </button>
            </div>
            <iframe title="Report" srcDoc={viewing.html} className="flex-1 w-full border-0 bg-black" />
          </div>
        </div>
      )}
    </div>
  );
}
