import React from "react";
import { Outlet } from "react-router-dom";
import { GameModeProvider } from "@/lib/GameModeContext";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import GameModeToggle from "@/components/GameModeToggle";

export default function Layout() {
  return (
    <GameModeProvider>
      <div className="min-h-screen bg-ink text-platinum font-body">
        <Nav />
        <main>
          <Outlet />
        </main>
        <Footer />
        <GameModeToggle />
      </div>
    </GameModeProvider>
  );
}