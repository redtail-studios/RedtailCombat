import { useEffect, useRef, useState } from "react";

// A single genre-evidence check occasionally needs a silent retry against a
// fresh AI response (a new PDF layout artifact, a paraphrase that doesn't
// verify) before the analysis can complete — invisible to the customer by
// design. Rotating, upbeat process copy fills that wait with something that
// feels like real progress instead of a bare "N seconds elapsed" counter,
// and never hints that anything needed fixing.
const GAME_ANALYSIS_LINES = [
  "Reading through your design document…",
  "Mapping your mechanics to the current market…",
  "This has real personality — comparing it to nearby genres…",
  "Lining up your five closest competitors…",
  "Weighing what makes your take different…",
  "Cross-checking every claim against your own document…",
  "Sizing up where your game could find its audience…",
  "Nearly there — assembling your report…",
];

export function useAnalysisFlavor(active, lines = GAME_ANALYSIS_LINES, intervalMs = 3200) {
  const [index, setIndex] = useState(0);
  const wasActive = useRef(false);
  useEffect(() => {
    if (!active) { wasActive.current = false; return; }
    if (!wasActive.current) { setIndex(0); wasActive.current = true; }
    const id = setInterval(() => setIndex(i => (i + 1) % lines.length), intervalMs);
    return () => clearInterval(id);
  }, [active, lines, intervalMs]);
  return lines[index];
}
