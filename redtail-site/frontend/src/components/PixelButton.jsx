import React from "react";
import { cn } from "@/lib/utils";

export default function PixelButton({ children, variant = "primary", className, as: Comp = "button", ...props }) {
  const base = "group relative inline-flex items-center gap-3 font-pixel text-[11px] md:text-xs uppercase tracking-wider px-6 py-4 pixel-clip transition-transform duration-150 active:translate-y-[2px] select-none";
  const styles = {
    primary: "bg-pulse text-ink hover:bg-[#ff4747]",
    ghost: "bg-panel text-platinum hover:bg-[#1f1f26] border border-white/10",
    moss: "bg-moss text-ink hover:bg-[#c4ff5c]",
  };
  return (
    <span className={cn("relative inline-block", className)}>
      <span className="absolute inset-0 translate-x-[4px] translate-y-[4px] bg-ink/60 pixel-clip" aria-hidden />
      <span className={cn("absolute inset-0 translate-x-[4px] translate-y-[4px] pixel-clip", variant === "primary" ? "bg-[#7a0f0f]" : variant === "moss" ? "bg-[#5a8a12]" : "bg-[#2B2B33]")} aria-hidden />
      <Comp className={cn(base, styles[variant], "relative")} {...props}>
        {children}
      </Comp>
    </span>
  );
}