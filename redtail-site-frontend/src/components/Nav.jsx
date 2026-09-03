import React from "react";
import { NavLink, Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { LOGO_URL } from "@/lib/teamData";

const LINKS = [
  { to: "/", label: "Humans" },
  { to: "/agents", label: "Agents" },
  { to: "/login", label: "Login" },
];

export default function Nav() {
  return (
    <header className="fixed top-0 inset-x-0 z-50 bg-ink/75 backdrop-blur-md border-b border-white/5">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-4 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-3 group" aria-label="Redtail home">
          <img src={LOGO_URL} alt="Redtail logo" className="h-9 w-9 sm:h-10 sm:w-10 object-contain drop-shadow-[0_0_12px_rgba(255,46,46,0.45)] transition-transform group-hover:-translate-y-0.5" />
          <span className="hidden sm:inline font-pixel text-xs sm:text-sm tracking-wider text-platinum">
            RED<span className="text-pulse">TAIL</span>
          </span>
        </Link>
        <nav className="flex items-center p-[2px] bg-white/10 pixel-clip-sm">
          <div className="flex bg-ink pixel-clip-sm">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "font-pixel text-[9px] sm:text-[10px] uppercase tracking-wider px-3 sm:px-5 py-3 transition-colors",
                    isActive ? "bg-pulse text-ink" : "text-platinum/70 hover:text-platinum hover:bg-white/5"
                  )
                }
              >
                {l.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </div>
    </header>
  );
}