"use client";

import { useState, useEffect } from "react";
import { Sparkles, Loader2 } from "lucide-react";

const PHRASES = [
  "Thinking...",
  "Analyzing requirements...",
  "Planning next steps...",
  "Processing...",
  "Considering options...",
];

export default function ThinkingIndicator() {
  const [phraseIndex, setPhraseIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPhraseIndex((i) => (i + 1) % PHRASES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-white border border-border text-black">
        <Sparkles className="w-4 h-4 text-[#0E7A3D]" />
      </div>
      <div className="flex items-center gap-2 text-sm text-text-secondary">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        <span className="animate-pulse">{PHRASES[phraseIndex]}</span>
      </div>
    </div>
  );
}
