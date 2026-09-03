import React from 'react';

export default function DashboardPlaceholder({ title, description }) {
  return (
    <div className="px-6 py-6 max-w-5xl mx-auto">
      <h1 className="font-pixel text-base text-platinum mb-2">{title}</h1>
      <p className="font-mono text-xs text-platinum/40 mb-6">{description || 'This section is coming soon.'}</p>
      <div className="border-2 border-dashed border-white/10 flex flex-col items-center justify-center py-20 text-center pixel-clip-sm">
        <p className="font-mono text-xs text-platinum/30">Nothing here yet — check back later.</p>
      </div>
    </div>
  );
}
