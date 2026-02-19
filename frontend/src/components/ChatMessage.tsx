"use client";

import { ChatMessage as ChatMessageType } from "@/lib/types";
import { User, Bot } from "lucide-react";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTheme } from "./ThemeProvider";

export default function ChatMessage({ msg }: { msg: ChatMessageType }) {
  // Tool groups and build summaries are handled by their own components
  if (msg.role === "tool_group" || msg.role === "build_summary") return null;

  const { theme } = useTheme();
  const isUser = msg.role === "user";

  return (
    <div className={clsx("flex items-start gap-3 px-4 py-3", isUser && "bg-bg-secondary/50")}>
      <div
        className={clsx(
          "w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-white",
          isUser ? "bg-blue-600" : "bg-emerald-600"
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div className={clsx(
        "min-w-0 max-w-none prose prose-sm prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-pre:my-2 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none",
        theme === "dark"
          ? "prose-invert prose-code:text-emerald-300 prose-code:bg-bg-secondary"
          : "prose-code:text-emerald-700 prose-code:bg-bg-tertiary"
      )}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        ) : (
          <>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
            {msg.isStreaming && <span className="animate-pulse text-emerald-400">|</span>}
          </>
        )}
      </div>
    </div>
  );
}
