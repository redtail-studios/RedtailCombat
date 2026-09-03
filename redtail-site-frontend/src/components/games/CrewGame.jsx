import React, { useEffect, useRef, useState } from "react";
import GameShell from "@/components/games/GameShell";
import Roster from "@/components/games/Roster";
import CharacterSheet from "@/components/home/CharacterSheet";
import { createCrewFlight } from "@/lib/games/crew";
import { TEAM } from "@/lib/teamData";

export default function CrewGame({ onExit }) {
  const ref = useRef(null);
  const game = useRef(null);
  const [status, setStatus] = useState("ready");
  const [info, setInfo] = useState({ score: 0, collected: 0, total: TEAM.length });
  const [best, setBest] = useState(() => Number(localStorage.getItem("rt-crew-best") || 0));
  const [collected, setCollected] = useState(() => JSON.parse(localStorage.getItem("rt-crew-unlocked") || "[]"));
  const [open, setOpen] = useState(null);
  const [compact] = useState(() => window.innerWidth < 640);

  useEffect(() => {
    game.current = createCrewFlight(ref.current, TEAM, {
      onState: (s, i) => {
        setStatus(s); setInfo(i);
        setBest((b) => { const n = Math.max(b, i.score); localStorage.setItem("rt-crew-best", n); return n; });
      },
      onCollect: (m) => {
        setCollected((c) => {
          const n = c.includes(m.handle) ? c : [...c, m.handle];
          localStorage.setItem("rt-crew-unlocked", JSON.stringify(n));
          return n;
        });
        setOpen(m);
      },
    }, [...collected], { compact });
    return game.current.destroy;
  }, []);

  const openSheet = (it) => { game.current.pause(); setOpen(TEAM.find((m) => m.handle === it.key)); };
  const close = () => { setOpen(null); game.current.resume(); };

  return (
    <div>
      <GameShell
        title="TAKE OFF"
        hint={compact
          ? "Drag up and down to steer. Dodge the red noise (3 lives) and fly into the founders to open their cards. Coins keep scoring."
          : "Move the mouse (or drag / ↑ ↓) to steer. Cruise the city, dodge the red noise (3 lives), and fly into the four founders to open their cards. Gold coins and repeat crew pickups keep scoring — fly as long as you can."}
        status={status} info={info} best={best} collectLabel="CREW"
        aspect={compact ? "aspect-[3/4]" : "aspect-video"}
        onExit={onExit}
      >
        <canvas ref={ref} width={compact ? 480 : 960} height={compact ? 640 : 540} className="w-full h-full crisp touch-none" />
      </GameShell>
      <Roster
        lockedHint="fly to collect"
        onOpen={openSheet}
        items={TEAM.map((m) => ({ key: m.handle, tag: m.player, label: m.handle, sub: m.role, portrait: m.portrait, collected: collected.includes(m.handle) }))}
      />
      <CharacterSheet member={open} onClose={close} />
    </div>
  );
}