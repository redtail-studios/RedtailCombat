import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import AmbientPong from "@/components/games/AmbientPong";
import CoinSlot from "@/components/auth/CoinSlot";
import Cabinet from "@/components/auth/Cabinet";
import { LOGO_URL } from "@/lib/teamData";

export default function AuthLayout({ icon: Icon, title, subtitle, footer, children }) {
  const gameMode = localStorage.getItem("rt-game-mode") !== "off";
  return (
    <div className="relative min-h-screen flex items-center justify-center bg-ink text-platinum font-body px-4 py-20 bit-grid scanlines">
      {gameMode && <AmbientPong />}
      <header className="fixed top-0 inset-x-0 z-20 bg-ink/75 backdrop-blur-md border-b border-white/5">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-4 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3" aria-label="Redtail home">
            <img src={LOGO_URL} alt="Redtail logo" className="h-9 w-9 sm:h-10 sm:w-10 object-contain drop-shadow-[0_0_12px_rgba(255,46,46,0.45)]" />
            <span className="hidden sm:inline font-pixel text-xs sm:text-sm tracking-wider">RED<span className="text-pulse">TAIL</span></span>
          </Link>
          <Link to="/" className="font-pixel text-[9px] sm:text-[10px] uppercase tracking-wider px-4 py-3 text-platinum/70 hover:text-platinum hover:bg-white/5 inline-flex items-center gap-2">
            <ArrowLeft className="h-3 w-3" /> exit to arcade
          </Link>
        </div>
      </header>
      <div className="relative z-10 w-full max-w-md">
        <p className="text-center mb-6 font-mono text-xs uppercase tracking-[0.3em] text-pulse">
          <Icon className="inline h-3.5 w-3.5 mr-2 -mt-0.5" aria-hidden="true" />arcade cabinet · 1 credit per play
        </p>
        <CoinSlot>
          <Cabinet title={title} subtitle={subtitle}>{children}</Cabinet>
        </CoinSlot>
        {footer && <p className="text-center text-sm text-platinum/60 mt-6 font-mono">{footer}</p>}
      </div>
    </div>
  );
}