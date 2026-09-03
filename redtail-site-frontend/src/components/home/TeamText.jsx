import React from "react";
import { Linkedin } from "lucide-react";
import SectionHeader from "@/components/SectionHeader";
import PixelFrame from "@/components/PixelFrame";
import { Image } from "@/components/ui/image";
import { TEAM } from "@/lib/teamData";

export default function TeamText() {
  return (
    <section id="team" className="relative py-24 sm:py-32 border-t border-white/10">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <SectionHeader eyebrow="the team" title="THE HUMANS" sub="Four founders, one PM-led build team. Agents do the scanning; these are the people who pick the winner and ship it." />
        <div className="mt-12 grid gap-5 sm:grid-cols-2">
          {TEAM.map((m) => (
            <PixelFrame key={m.handle} inner="p-6 space-y-3">
              <Image src={m.portrait} alt={m.name} className="h-20 w-20 crisp" />
              <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-moss">{m.player}</p>
              <p className="font-pixel text-sm text-platinum">{m.name}</p>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-pulse">{m.role}</p>
              <p className="text-platinum/80">{m.bio}</p>
              <a href={m.linkedin} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 font-mono text-xs text-platinum/70 hover:text-moss">
                <Linkedin className="h-4 w-4" /> linkedin ↗
              </a>
            </PixelFrame>
          ))}
        </div>
        <div className="mt-10 grid gap-4 sm:grid-cols-3 font-mono text-sm text-platinum/60">
          <p><span className="text-pulse">stage</span> · pre-seed (open)</p>
          <p><span className="text-pulse">location</span> · Ithaca, NY · Cornell Johnson MBA '27</p>
          <p><span className="text-pulse">titles_planned_18mo</span> · 4–6</p>
        </div>
      </div>
    </section>
  );
}