import React from "react";
import PixelFrame from "@/components/PixelFrame";
import { CONTACT_EMAIL } from "@/lib/teamData";

const JSON_TEXT = `{
  "name": "redtail",
  "type": "ai-native mobile game studio",
  "founded": 2026,
  "team_size": 4,
  "stage": "pre-seed",
  "titles_planned_18mo": "4-6",
  "contact": "${CONTACT_EMAIL}",
  "schema_org": "embedded in <head>"
}`;

export default function MachineReadable() {
  return (
    <section id="json" className="space-y-6 scroll-mt-32">
      <h2 className="font-pixel text-lg sm:text-2xl text-platinum"><span className="text-pulse">##</span>/machine-readable</h2>
      <PixelFrame tone="dim" inner="p-5 sm:p-6">
        <pre className="font-mono text-sm sm:text-base text-moss overflow-x-auto leading-relaxed">{JSON_TEXT}</pre>
      </PixelFrame>
      <PixelFrame tone="dim" inner="p-5 sm:p-6 font-mono text-sm sm:text-base space-y-2">
        <p><span className="text-pulse">$ </span>curl -sH "Accept: text/markdown" https://redtail-studios.com</p>
        <p className="text-platinum/60">200 OK · you're reading the response</p>
        <p><span className="text-pulse">$ </span>echo "we exist. say hi."</p>
        <p className="text-platinum/60">→ <a href={`mailto:${CONTACT_EMAIL}`} className="text-moss hover:underline underline-offset-4">mailto:{CONTACT_EMAIL}</a></p>
      </PixelFrame>
    </section>
  );
}