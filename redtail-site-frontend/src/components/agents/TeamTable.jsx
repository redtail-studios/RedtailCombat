import React from "react";
import { Image } from "@/components/ui/image";
import { TEAM } from "@/lib/teamData";

export default function TeamTable() {
  return (
    <section id="team" className="space-y-6 scroll-mt-32">
      <h2 className="font-pixel text-lg sm:text-2xl text-platinum"><span className="text-pulse">##</span>/team</h2>
      <div className="font-mono text-base sm:text-lg divide-y divide-white/10 border-y border-white/10">
        <div className="hidden sm:grid grid-cols-[48px_140px_180px_1fr] gap-6 py-3 text-platinum/50 text-sm uppercase tracking-[0.2em]">
          <span /><span>handle</span><span>role</span><span>bio</span>
        </div>
        {TEAM.map((m) => (
          <div key={m.handle} className="grid grid-cols-[48px_1fr] sm:grid-cols-[48px_140px_180px_1fr] gap-3 sm:gap-6 py-3 items-center">
            <Image src={m.portrait} alt={m.name} className="h-12 w-12 crisp pixel-clip-sm" />
            <div className="sm:contents">
              <span className="text-moss block">{m.handle}</span>
              <span className="text-platinum/85 block">{m.role}</span>
              <span className="text-platinum/85 block">
                {m.bio.split(".")[0]} · <a href={m.linkedin} target="_blank" rel="noreferrer" className="text-pulse hover:text-moss hover:underline underline-offset-4">linkedin↗</a>
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}