import React from 'react';
import { Info } from 'lucide-react';
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover';

// A small "i" icon for a dashboard card's header — click (not just hover, so
// it works on touch) to see a short explanation of what that card's numbers
// actually mean. Put it at the end of the header row (ml-auto).
export default function InfoTooltip({ children }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          onClick={(e) => e.stopPropagation()}
          aria-label="What does this mean?"
          className="ml-auto flex-shrink-0 w-4 h-4 flex items-center justify-center rounded-full text-platinum/30 border border-white/10 hover:text-platinum hover:border-white/30 transition-colors"
        >
          <Info className="w-2.5 h-2.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        sideOffset={6}
        className="w-72 bg-panel border border-white/15 text-platinum/70 font-mono text-[11px] leading-relaxed p-3 pixel-clip-sm shadow-xl rounded-none"
      >
        {children}
      </PopoverContent>
    </Popover>
  );
}
