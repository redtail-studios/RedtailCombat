import React, { createContext, useContext, useEffect, useState } from "react";

const Ctx = createContext({ gameMode: true, toggle: () => {} });

export function GameModeProvider({ children }) {
  const [gameMode, setGameMode] = useState(() => localStorage.getItem("rt-game-mode") !== "off");

  useEffect(() => {
    localStorage.setItem("rt-game-mode", gameMode ? "on" : "off");
    document.documentElement.classList.toggle("investor", !gameMode);
  }, [gameMode]);

  return (
    <Ctx.Provider value={{ gameMode, toggle: () => setGameMode((v) => !v) }}>
      {children}
    </Ctx.Provider>
  );
}

export const useGameMode = () => useContext(Ctx);