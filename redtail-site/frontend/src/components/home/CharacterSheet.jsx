import React from "react";
import { Linkedin } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Image } from "@/components/ui/image";

export default function CharacterSheet({ member, onClose }) {
  return (
    <Sheet open={!!member} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="bg-ink border-l-2 border-pulse text-platinum w-full sm:max-w-md overflow-y-auto">
        {member && (
          <div className="space-y-6">
            <SheetHeader className="text-left space-y-2">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-moss">■ paused · {member.player} unlocked</p>
              <SheetTitle className="font-pixel text-xl text-platinum">{member.handle}</SheetTitle>
              <SheetDescription className="font-mono text-xs uppercase tracking-[0.2em] text-pulse">{member.name} · {member.role}</SheetDescription>
            </SheetHeader>
            <div className="p-[2px] bg-moss pixel-clip w-48">
              <Image src={member.portrait} alt={member.name} className="aspect-square w-full pixel-clip crisp" />
            </div>
            <div className="space-y-2">
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-platinum/50">lore</p>
              <p className="text-platinum/80">{member.bio}</p>
            </div>
            <a href={member.linkedin} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 font-pixel text-[10px] uppercase bg-panel px-4 py-3 pixel-clip-sm hover:bg-moss hover:text-ink transition-colors">
              <Linkedin className="h-4 w-4" /> linkedin ↗
            </a>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}