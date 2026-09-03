import React, { useEffect, useRef } from "react";
import { createPong } from "@/lib/games/pong";

export default function AmbientPong() {
  const ref = useRef(null);
  useEffect(() => createPong(ref.current), []);
  return (
    <canvas
      ref={ref}
      aria-hidden
      className="fixed inset-0 z-0 pointer-events-none opacity-[0.14] crisp"
    />
  );
}