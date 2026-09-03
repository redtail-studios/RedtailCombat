import React from "react";
import { Link } from "react-router-dom";
import { Mail } from "lucide-react";
import { CONTACT_EMAIL, LOGO_URL } from "@/lib/teamData";

export default function Footer() {
  return (
    <footer className="relative border-t border-white/10 bg-ink">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-12 grid gap-10 md:grid-cols-3">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <img src={LOGO_URL} alt="Redtail logo" className="h-8 w-8 object-contain" />
            <span className="font-pixel text-xs text-platinum">RED<span className="text-pulse">TAIL</span></span>
          </div>
          <p className="text-platinum/60 text-sm">an ai-native game studio<br />ithaca, ny · cornell johnson '27</p>
        </div>
        <div className="space-y-2 text-sm">
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-pulse mb-3">levels</p>
          <Link to="/" className="block text-platinum/70 hover:text-moss">/humans</Link>
          <Link to="/agents" className="block text-platinum/70 hover:text-moss">/agents</Link>
          <Link to="/lore" className="block text-platinum/70 hover:text-moss">/lore</Link>
        </div>
        <div className="space-y-2 text-sm">
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-pulse mb-3">say hi</p>
          <a href={`mailto:${CONTACT_EMAIL}`} className="inline-flex items-center gap-2 text-platinum/70 hover:text-moss">
            <Mail className="h-4 w-4" /> {CONTACT_EMAIL}
          </a>
          <p className="text-platinum/40 text-xs pt-4">v7.0 · view-source:agent · 200 OK</p>
        </div>
      </div>
    </footer>
  );
}