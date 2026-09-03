import React from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";

export default function StageSheet({ stage, onClose }) {
  return (
    <Sheet open={!!stage} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="bg-ink border-l-2 border-moss text-platinum w-full sm:max-w-md overflow-y-auto">
        {stage && (
          <div className="space-y-6">
            <SheetHeader className="text-left space-y-2">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-moss">■ paused · stage {stage.n}</p>
              <SheetTitle className="font-pixel text-xl text-platinum">{stage.name}</SheetTitle>
              <SheetDescription className="font-mono text-xs uppercase tracking-[0.2em] text-pulse">owner: {stage.owner}</SheetDescription>
            </SheetHeader>
            <div className="p-[2px] bg-white/10 pixel-clip">
              <div className="bg-panel pixel-clip aspect-[4/3] flex items-center justify-center">
                <stage.Icon className="h-20 w-20 text-moss" />
              </div>
            </div>
            <dl className="space-y-2 font-mono text-sm">
              <div><dt className="inline text-moss uppercase text-xs tracking-[0.2em]">in · </dt><dd className="inline text-platinum/80">{stage.input}</dd></div>
              <div><dt className="inline text-moss uppercase text-xs tracking-[0.2em]">out · </dt><dd className="inline text-platinum/80">{stage.output}</dd></div>
            </dl>
            <div className="space-y-2">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-platinum/50">lore</p>
              <p className="text-platinum/80">{stage.lore}</p>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}