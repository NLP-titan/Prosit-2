"use client";

import { useState } from "react";
import { MessageCircleQuestion } from "lucide-react";
import { ChatMessage } from "@/lib/types";
import { Button } from "./ui/Button";

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
        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-[#D4F79A] text-black">
          <MessageCircleQuestion className="w-4 h-4" />
        </div>
        <div className="min-w-0 flex-1 bg-white border border-border rounded-2xl px-4 py-3 shadow-sm">
          <p className="text-sm text-text-primary mb-3">
            {msg.content}
          </p>

          <div className="flex flex-wrap gap-2 mb-2">
            {msg.options?.map((option, i) => (
              <Button
                key={i}
                type="button"
                size="sm"
                variant={msg.answered ? "ghost" : "secondary"}
                disabled={msg.answered}
                onClick={() => handleOptionClick(option)}
                className="text-xs rounded-full px-3 py-1.5"
              >
                {option}
              </Button>
            ))}
          </div>

          {!msg.answered && (
            <div className="flex gap-2 mt-3">
              <input
                value={customText}
                onChange={(e) => setCustomText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCustomSubmit();
                }}
                placeholder="Or type your own answer..."
                className="flex-1 bg-bg-secondary border border-border rounded-full px-3 py-1.5 text-xs focus:outline-none focus:border-accent"
              />
              <Button
                type="button"
                size="sm"
                variant="primary"
                disabled={!customText.trim()}
              >
                Send
              </Button>
            </div>
          )}

          {msg.answered && (
            <p className="text-xs text-text-muted mt-2">Answer recorded</p>
          )}
        </div>
      </div>
    </div>
  );
}
