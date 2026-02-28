"use client";

import { useRef, useEffect } from "react";
import { ChatMessage as ChatMessageType } from "@/lib/types";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import ToolActivity from "./ToolActivity";
import BuildSummary from "./BuildSummary";
import AskUserPrompt from "./AskUserPrompt";
import ThinkingIndicator from "./ThinkingIndicator";

interface Props {
  messages: ChatMessageType[];
  onSend: (message: string) => void;
  onStop: () => void;
  isAgentWorking: boolean;
  showToolDetails: boolean;
  onAnswerAskUser?: (messageId: string, answer: string) => void;
}

export default function ChatPanel({ messages, onSend, onStop, isAgentWorking, showToolDetails, onAnswerAskUser }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Determine if we should show thinking indicator
  const lastMsg = messages[messages.length - 1];
  const hasActiveToolGroup = lastMsg?.role === "tool_group" && lastMsg.toolGroup?.isActive;
  const isStreaming = lastMsg?.role === "assistant" && lastMsg.isStreaming;
  const showThinking = isAgentWorking && !hasActiveToolGroup && !isStreaming;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-text-muted text-sm px-8 text-center">
            Describe the backend API you want to build. The agent will ask clarifying questions, then generate a complete FastAPI + PostgreSQL project.
          </div>
        )}
        {messages.map((msg) => {
          if (msg.role === "tool_group" && msg.toolGroup) {
            return (
              <ToolActivity
                key={msg.id}
                group={msg.toolGroup}
                showDetails={showToolDetails}
              />
            );
          }
          if (msg.role === "build_summary") {
            return (
              <BuildSummary
                key={msg.id}
                swaggerUrl={msg.swaggerUrl || ""}
                apiUrl={msg.apiUrl || ""}
              />
            );
          }
          if (msg.role === "ask_user") {
            return (
              <AskUserPrompt
                key={msg.id}
                msg={msg}
                onAnswer={(answer) => onAnswerAskUser?.(msg.id, answer)}
              />
            );
          }
          return <ChatMessage key={msg.id} msg={msg} />;
        })}
        {showThinking && <ThinkingIndicator />}
        <div ref={bottomRef} />
      </div>

      <ChatInput
        onSend={onSend}
        onStop={onStop}
        disabled={isAgentWorking}
        isAgentWorking={isAgentWorking}
      />
    </div>
  );
}
