import React from "react";

export default function MissionBlock() {
  return (
    <section id="mission" className="space-y-6 scroll-mt-32">
      <h2 className="font-pixel text-lg sm:text-2xl text-platinum"><span className="text-pulse">##</span>/mission</h2>
      <div className="space-y-5 text-lg sm:text-xl leading-relaxed text-platinum/85 max-w-3xl">
        <p>
          Most studios guess. They bet a year of creative work on a hunch, then find out at launch whether the market agrees.
        </p>
        <p>
          Redtail inverts the loop. Our agents read what players actually do — what they rage-quit, what they replay, what they beg for in reviews — and turn that behavior into concepts, prototypes and AI-vs-AI playtests before a human commits.
        </p>
        <p className="text-moss">
          Then a small, PM-led human team picks the strongest one and ships it. Four to six titles in eighteen months. Every launch retrains the engine.
        </p>
      </div>
    </section>
  );
}