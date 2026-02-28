"use client";

import { useRef, useEffect } from "react";
import { ChatMessage as ChatMessageType } from "@/lib/types";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import ToolActivity from "./ToolActivity";
import BuildSummary from "./BuildSummary";
import BuildProgress from "./BuildProgress";
import ThinkingIndicator from "./ThinkingIndicator";
import { Button } from "./ui/Button";

interface Props {
  messages: ChatMessageType[];
  onSend: (message: string) => void;
  onStop: () => void;
  isAgentWorking: boolean;
  showToolDetails: boolean;
}

export default function ChatPanel({ messages, onSend, onStop, isAgentWorking, showToolDetails }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Determine if we should show thinking indicator
  const lastMsg = messages[messages.length - 1];
  const hasActiveToolGroup = lastMsg?.role === "tool_group" && lastMsg.toolGroup?.isActive;
  const isStreaming = lastMsg?.role === "assistant" && lastMsg.isStreaming;
  const hasBuildProgress = messages.some(
    (m) => m.role === "build_progress" && m.buildTasks?.some((t) => t.status === "running")
  );
  const showThinking = isAgentWorking && !hasActiveToolGroup && !isStreaming && !hasBuildProgress;

  const handlePreset = (text: string) => {
    if (isAgentWorking) return;
    onSend(text);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full px-4 py-6">
            <div className="max-w-md text-center text-sm text-text-secondary">
              <p className="mb-4">
                Describe in plain English what backend you want. The agent will ask
                clarifying questions and then generate a complete FastAPI +
                PostgreSQL project.
              </p>
              <div className="flex flex-col gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  disabled={isAgentWorking}
                  onClick={() =>
                    handlePreset(
                      "I need a simple blog backend with users, posts, and comments. Users should be able to sign up, log in, and manage their own posts."
                    )
                  }
                >
                  Create a blog backend
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  disabled={isAgentWorking}
                  onClick={() =>
                    handlePreset(
                      "Create a small CRM backend for tracking leads and customers. I want companies, contacts, deals, and simple notes on each."
                    )
                  }
                >
                  Build a simple CRM
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  disabled={isAgentWorking}
                  onClick={() =>
                    handlePreset(
                      "I want an inventory backend for a small store. Track products, stock levels, suppliers, and basic purchase orders."
                    )
                  }
                >
                  Design an inventory backend
                </Button>
              </div>
            </div>
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
          if (msg.role === "build_progress") {
            return <BuildProgress key={msg.id} msg={msg} />;
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
