import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Terminal } from "lucide-react";
import { CONTACT_EMAIL } from "@/lib/teamData";

const JUMP = { "/about": "about", "/mission": "mission", "/faq": "faq", "/json": "json" };
const HELP = "/about · /mission · /faq · /json · /team · /agents · /invest · /jobs";

export default function CommandLine() {
  const [value, setValue] = useState("");
  const [log, setLog] = useState([{ cmd: "/help", out: HELP }]);
  const navigate = useNavigate();

  const run = (raw) => {
    const cmd = raw.trim().toLowerCase();
    let out = `unknown command "${cmd}" — try /help`;
    if (!cmd) return;
    if (JUMP[cmd]) { document.getElementById(JUMP[cmd])?.scrollIntoView({ behavior: "smooth" }); out = `jumping to ${cmd}`; }
    else if (cmd === "/help") out = HELP;
    else if (cmd === "/team" || cmd === "/humans") { out = "loading player select…"; setTimeout(() => navigate("/"), 300); }
    else if (cmd === "/agents") { out = "loading the arsenal…"; setTimeout(() => navigate("/agents"), 300); }
    else if (cmd === "/invest") { out = "opening a line to santi…"; window.location.href = `mailto:${CONTACT_EMAIL}?subject=Redtail%20-%20Investor%20Inbound`; }
    else if (cmd === "/jobs" || cmd === "/hiring") out = "closed founding team. we'll open to indie devs after a few titles ship.";
    setLog((l) => [...l.slice(-3), { cmd, out }]);
    setValue("");
  };

  return (
    <section className="p-[2px] bg-pulse pixel-clip">
      <div className="bg-ink pixel-clip p-5 sm:p-6 font-mono text-sm sm:text-base space-y-3">
        <p className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-pulse"><Terminal className="h-4 w-4" /> command line</p>
        {log.map((l, i) => (
          <div key={i} className="space-y-1">
            <p><span className="text-moss">redtail&gt;</span> {l.cmd}</p>
            <p className="text-platinum/70 pl-4">{l.out}</p>
          </div>
        ))}
        <form onSubmit={(e) => { e.preventDefault(); run(value); }} className="flex items-center gap-2 pt-2 border-t border-white/10">
          <span className="text-moss">redtail&gt;</span>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="type /help"
            aria-label="Command line"
            className="flex-1 bg-transparent outline-none text-platinum placeholder:text-platinum/30 caret-pulse"
          />
          <span className="w-2.5 h-5 bg-pulse animate-blink" aria-hidden />
        </form>
      </div>
    </section>
  );
}