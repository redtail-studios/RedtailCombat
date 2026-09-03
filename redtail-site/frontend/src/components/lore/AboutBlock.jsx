import React from "react";
import { CONTACT_EMAIL } from "@/lib/teamData";

const ROWS = [
  ["type", "AI-native mobile game studio"],
  ["thesis", "behavioral intelligence > creative guessing"],
  ["stage", "pre-seed (open)"],
  ["location", "Ithaca, NY · Cornell Johnson MBA '27"],
  ["titles_planned_18mo", "4–6"],
  ["first_launch", "in flight"],
];

export default function AboutBlock() {
  return (
    <section id="about" className="space-y-6 scroll-mt-32">
      <h2 className="font-pixel text-lg sm:text-2xl text-platinum"><span className="text-pulse">##</span>/about</h2>
      <dl className="font-mono text-base sm:text-lg divide-y divide-white/10 border-y border-white/10">
        {ROWS.map(([k, v]) => (
          <div key={k} className="grid sm:grid-cols-[220px_1fr] gap-1 sm:gap-6 py-3">
            <dt className="text-moss">{k}</dt>
            <dd className="text-platinum/85">{v}</dd>
          </div>
        ))}
        <div className="grid sm:grid-cols-[220px_1fr] gap-1 sm:gap-6 py-3">
          <dt className="text-moss">contact</dt>
          <dd><a href={`mailto:${CONTACT_EMAIL}`} className="text-pulse hover:text-moss underline-offset-4 hover:underline">{CONTACT_EMAIL}</a></dd>
        </div>
      </dl>
    </section>
  );
}