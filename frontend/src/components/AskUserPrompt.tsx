"use client";

import { useState } from "react";
import { MessageCircleQuestion } from "lucide-react";
import { ChatMessage } from "@/lib/types";

interface Props {
  msg: ChatMessage;
  onAnswer: (text: string) => void;
}

export default function AskUserPrompt({ msg, onAnswer }: Props) {
  const [customText, setCustomText] = useState("");

  const handleOptionClick = (option: string) => {
    if (msg.answered) return;
    onAnswer(option);
  };

  const handleCustomSubmit = () => {
    const trimmed = customText.trim();
    if (!trimmed || msg.answered) return;
    onAnswer(trimmed);
    setCustomText("");
  };

  return (
    <div className="px-4 py-3">
      <div className="flex items-start gap-3">
        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-amber-600 text-white">
          <MessageCircleQuestion className="w-4 h-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-text-primary mb-3">{msg.content}</p>

          <div className="flex flex-wrap gap-2 mb-2">
            {msg.options?.map((option, i) => (
              <button
                key={i}
                onClick={() => handleOptionClick(option)}
                disabled={msg.answered}
                className={
                  msg.answered
                    ? "px-3 py-1.5 text-xs rounded-lg border border-border text-text-muted cursor-default"
                    : "px-3 py-1.5 text-xs rounded-lg border border-border text-text-primary hover:bg-bg-hover hover:border-text-muted transition-colors cursor-pointer"
                }
              >
                {option}
              </button>
            ))}
          </div>

          {!msg.answered && (
            <div className="flex gap-2 mt-2">
              <input
                value={customText}
                onChange={(e) => setCustomText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCustomSubmit();
                }}
                placeholder="Or type a custom answer..."
                className="flex-1 bg-bg-secondary border border-border rounded px-2 py-1.5 text-xs focus:outline-none focus:border-accent"
              />
              <button
                onClick={handleCustomSubmit}
                disabled={!customText.trim()}
                className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded transition-colors text-white"
              >
                Send
              </button>
            </div>
          )}

          {msg.answered && (
            <p className="text-xs text-text-muted mt-1">Answered</p>
          )}
        </div>
      </div>
    </div>
  );
}
