import React, { useRef, useState } from 'react';
import { Bird, Send, Loader2 } from 'lucide-react';
import { useDashboardAuth } from '@/lib/DashboardAuthContext';

const SUGGESTIONS = [
  "What's the biggest story right now?",
  'Any negative sentiment I should know about?',
  'Summarize today\'s news in 3 bullets',
];

export default function AskLore() {
  const { dashboardPassword } = useDashboardAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const scrollRef = useRef(null);

  const ask = async (question) => {
    const q = question.trim();
    if (!q || loading) return;
    setError('');
    setInput('');
    setMessages((m) => [...m, { role: 'user', text: q }]);
    setLoading(true);
    try {
      const r = await fetch('/api/lore/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, password: dashboardPassword }),
      });
      const d = await r.json();
      if (!r.ok || d.error) throw new Error(d.error || 'Something went wrong');
      setMessages((m) => [...m, { role: 'lore', text: d.answer }]);
    } catch (e) {
      setError(e.message || 'Ask Lore failed');
    } finally {
      setLoading(false);
      setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }), 50);
    }
  };

  return (
    <div className="bg-panel border border-white/5 p-4 pixel-clip-sm flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3">
        <Bird className="w-3.5 h-3.5 text-pulse" />
        <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">Ask Lore</span>
      </div>
      <p className="font-mono text-xs text-platinum/40 mb-3">
        Your co-pilot — answers grounded only in the real news on this page.
      </p>

      <div ref={scrollRef} className="flex-1 min-h-[220px] max-h-[360px] overflow-y-auto space-y-3 mb-3 pr-1">
        {messages.length === 0 && !loading && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="font-mono text-[10px] px-2.5 py-1.5 border border-white/10 text-platinum/50 hover:text-platinum hover:border-white/20 transition-colors pixel-clip-sm text-left"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className={`font-mono text-xs px-3 py-2 max-w-[85%] whitespace-pre-wrap pixel-clip-sm ${
                m.role === 'user' ? 'bg-pulse/10 text-platinum border border-pulse/20' : 'bg-ink text-platinum/80 border border-white/10'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 font-mono text-xs text-platinum/40">
            <Loader2 className="w-3 h-3 animate-spin" /> Lore is thinking…
          </div>
        )}
      </div>

      {error && <p className="font-mono text-xs text-pulse mb-2">{error}</p>}

      <form
        onSubmit={(e) => { e.preventDefault(); ask(input); }}
        className="flex items-center gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about the news…"
          className="flex-1 h-10 px-3 font-mono text-xs bg-ink border border-white/15 text-platinum placeholder:text-platinum/30 outline-none focus:border-pulse/40"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="h-10 w-10 flex items-center justify-center bg-pulse text-ink hover:opacity-90 disabled:opacity-30 transition-opacity pixel-clip-sm flex-shrink-0"
          aria-label="Send"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
}
