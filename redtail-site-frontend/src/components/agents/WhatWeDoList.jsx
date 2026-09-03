import React from "react";

const ROWS = [
  ["sense", "agents scan forums, stores, reviews, creator content"],
  ["synthesize", "strategy agents turn signals into game concepts"],
  ["simulate", "prototype agents + AI-vs-AI playtests for balance"],
  ["build", "human PM-led team picks the strongest concept and ships it"],
  ["launch", "live-ops, marketing, continuous updates"],
  ["learn", "performance data retrains the engine for the next pick"],
];

export default function WhatWeDoList() {
  return (
    <ul className="font-mono text-base sm:text-lg divide-y divide-white/10 border-y border-white/10">
      {ROWS.map(([k, v]) => (
        <li key={k} className="grid sm:grid-cols-[180px_1fr] gap-1 sm:gap-6 py-3">
          <span className="text-moss">{k}</span>
          <span className="text-platinum/85">{v}</span>
        </li>
      ))}
    </ul>
  );
}