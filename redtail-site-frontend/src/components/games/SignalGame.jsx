import React, { useEffect, useRef, useState } from "react";
import GameShell from "@/components/games/GameShell";
import Roster from "@/components/games/Roster";
import StageSheet from "@/components/agents/StageSheet";
import { createSignalStrike } from "@/lib/games/signal";
import { STAGES } from "@/lib/loopData";

export default function SignalGame({ onExit }) {
  const ref = useRef(null);
  const game = useRef(null);
  const [status, setStatus] = useState("ready");
  const [info, setInfo] = useState({ score: 0, lives: 3, collected: 0, total: STAGES.length });
  const [best, setBest] = useState(() => Number(localStorage.getItem("rt-signal-best") || 0));
  const [collected, setCollected] = useState([]);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    game.current = createSignalStrike(ref.current, STAGES, {
      onState: (s, i) => {
        setStatus(s); setInfo(i);
        if (s === "ready") setCollected([]);
        if (s === "over" || s === "complete") setBest((b) => { const n = Math.max(b, i.score); localStorage.setItem("rt-signal-best", n); return n; });
      },
      onCollect: (st) => { setCollected((c) => [...c, st.n]); setOpen(st); },
    });
    return game.current.destroy;
  }, []);

  const openSheet = (it) => { game.current.pause(); setOpen(STAGES.find((s) => s.n === it.key)); };
  const close = () => { setOpen(null); game.current.resume(); };

  return (
    <div>
      <GameShell title="FREE THE SIGNAL" hint="Move the mouse (or ← →) to steer. Hold click or space to fire. Shoot down the red static, and blast the red cage at the top three times to free each stage of the loop. 5 lives." status={status} info={info} best={best} collectLabel="LOOP" completeText="LOOP COMPLETE" onExit={onExit}>
        <canvas ref={ref} width={960} height={540} className="w-full h-full crisp touch-none" />
      </GameShell>
      <Roster
        lockedHint="shoot to free"
        onOpen={openSheet}
        items={STAGES.map((s) => ({ key: s.n, tag: s.n, label: s.name, sub: s.owner, collected: collected.includes(s.n) }))}
      />
      <StageSheet stage={open} onClose={close} />
    </div>
  );
}