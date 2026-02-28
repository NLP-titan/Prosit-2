"use client";

import { useState } from "react";
import { ChatMessage as ChatMessageType } from "@/lib/types";
import { User, Sparkles } from "lucide-react";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTheme } from "./ThemeProvider";
import { Button } from "./ui/Button";

interface Props {
  msg: ChatMessageType;
  onAnswerAskUser?: (messageId: string, answer: string) => void;
}

export default function ChatMessage({ msg, onAnswerAskUser }: Props) {
  const [customText, setCustomText] = useState("");

  // Tool groups and build summaries are handled by their own components
  if (msg.role === "tool_group" || msg.role === "build_summary") return null;

  const { theme } = useTheme();
  const isUser = msg.role === "user";
  const hasOptions = msg.options && msg.options.length > 0;

  const handleOptionClick = (option: string) => {
    if (msg.answered) return;
    onAnswerAskUser?.(msg.id, option);
  };

  const handleCustomSubmit = () => {
    const trimmed = customText.trim();
    if (!trimmed || msg.answered) return;
    onAnswerAskUser?.(msg.id, trimmed);
    setCustomText("");
  };

  return (
    <div
      className={clsx(
        "px-4 py-3 flex gap-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-bg-secondary text-text-primary">
          <Sparkles className="w-4 h-4 text-accent" />
        </div>
      )}
      <div
        className={clsx(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-chat-user-bg text-chat-user-text rounded-tr-sm"
            : "bg-chat-ai-bg border border-border text-text-primary rounded-tl-sm shadow-sm"
        )}
      >
        <div
          className={clsx(
            "min-w-0 max-w-none prose prose-sm prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-pre:my-2 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none",
            theme === "dark"
              ? "prose-invert prose-code:text-emerald-300 prose-code:bg-bg-secondary"
              : "prose-code:text-emerald-700 prose-code:bg-bg-tertiary"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{msg.content}</p>
          ) : (
            <>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
              {msg.isStreaming && (
                <span className="animate-pulse text-emerald-400">|</span>
              )}
            </>
          )}
        </div>

        {/* Inline ask_user options */}
        {hasOptions && (
          <div className="mt-3 pt-3 border-t border-border/50">
            <div className="flex flex-wrap gap-2 mb-2">
              {msg.options!.map((option, i) => (
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
                  onClick={handleCustomSubmit}
                >
                  Send
                </Button>
              </div>
            )}

            {msg.answered && (
              <p className="text-xs text-text-muted mt-2">Answer recorded</p>
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-text-primary text-bg-primary">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}
