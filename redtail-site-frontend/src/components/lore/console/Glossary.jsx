import React from "react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import PixelFrame from "@/components/PixelFrame";

const TERMS = [
  { q: "Hits", a: `The number of scraped player-content items (Reddit posts, Steam/Google Play reviews, Hacker News comments, gaming-news text) that matched at least one keyword for that demand signal, for that year. E.g. a review saying "would love to play this with friends" counts as one hit for Co-op / Social Play.` },
  { q: "Signal score (X/10)", a: "Not the raw hit count — it's that signal's hits as a share of all scraped items that year, scaled relative to whichever signal had the most hits. The strongest signal that year caps out around 9.5/10; others scale down proportionally." },
  { q: "Sentiment (% positive / % negative)", a: "The share of scraped text with clearly positive or negative tone, based on automated sentiment scoring of each review, comment, or post. The remainder is neutral." },
  { q: "Fit badges — Strong Fit / Partial Fit / Miss / Avoided", a: "How well a game's current design serves a given demand signal. Strong Fit — the design clearly serves it. Partial Fit — served incompletely. Miss — not addressed at all. Avoided — a negative signal (like ad fatigue) the design correctly sidesteps." },
  { q: "Gap severity — Critical / Significant / Minor", a: "How urgent an exposed gap is. Critical — the top-ranked demand signal the game doesn't address. Significant — a real but lower-ranked gap. Minor — a smaller, lower-priority gap." },
  { q: "Quote citations — [Q7]", a: "A bracketed ID next to a quoted line means that quote is real, pulled directly from the scraped data — not written or paraphrased by Claude. Every claim in a report should be traceable back to a real [Qn] quote or a real number." },
  { q: "Mentions", a: `How many scraped items referenced a named competitor by name (e.g. "Genshin Impact", "Candy Crush"). Sentiment for a competitor is the positive/negative split within just those mentions.` },
  { q: "Data Coverage grade (A–F)", a: "Claude's judgment of how thin or solid the scraped sample is for that year — an A means a large, well-rounded sample across sources; a D or F means the sample is thin and findings should be treated as more directional than precise." },
  { q: "Backtest / Validation years", a: "When both are selected, the backtest years are analysed as if predicting the future at that time, then the validation years (what actually happened) are used to score how accurate those predictions turned out to be." },
];

export default function Glossary() {
  return (
    <PixelFrame tone="dim" inner="p-6 sm:p-8">
      <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-pulse mb-3">▸ Glossary — Report terms explained</p>
      <h3 className="font-body font-bold text-lg text-platinum mb-1">What do these terms mean?</h3>
      <p className="text-platinum/70 mb-2">Click a term to expand its explanation.</p>
      <Accordion type="single" collapsible className="border-t border-white/10">
        {TERMS.map((t, i) => (
          <AccordionItem key={i} value={`term-${i}`} className="border-white/10">
            <AccordionTrigger className="font-body font-bold text-base text-left hover:text-moss hover:no-underline py-4">
              {t.q}
            </AccordionTrigger>
            <AccordionContent className="text-platinum/70 text-sm pb-5">{t.a}</AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </PixelFrame>
  );
}
