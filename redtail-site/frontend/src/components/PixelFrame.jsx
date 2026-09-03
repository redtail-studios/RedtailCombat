import React from "react";
import { cn } from "@/lib/utils";

export default function PixelFrame({ children, className, tone = "dim", inner }) {
  const border = { dim: "bg-white/10", red: "bg-pulse", moss: "bg-moss" }[tone];
  return (
    <div className={cn("p-[2px] pixel-clip", border, className)}>
      <div className={cn("bg-panel pixel-clip h-full", inner)}>{children}</div>
    </div>
  );
}