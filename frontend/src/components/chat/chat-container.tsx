"use client";

import { useCallback, useEffect, useRef } from "react";
import { ChatMessage } from "./chat-message";
import { ChatInput } from "./chat-input";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

interface ChatContainerProps {
  messages: ChatMessageType[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessageType[]>>;
  onSend: (message: string) => void;
  isLoading: boolean;
  isAgentWorking: boolean;
}

export function ChatContainer({
  messages,
  setMessages,
  onSend,
  isLoading,
  isAgentWorking,
}: ChatContainerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleOptionSelect = useCallback(
    (messageId: string, answer: string) => {
      // Mark the question as answered
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId && m.askUser
            ? { ...m, askUser: { ...m.askUser, answered: true } }
            : m
        )
      );
      // Send the answer as a regular message
      onSend(answer);
    },
    [setMessages, onSend]
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 min-h-0 overflow-y-auto px-4">
        <div className="space-y-4 py-4">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground py-20">
              <p className="text-lg font-medium">Welcome to BackendForge</p>
              <p className="text-sm mt-2">
                Describe the backend API you want to build, and I&apos;ll
                generate it for you.
              </p>
              <p className="text-xs mt-4 text-muted-foreground/60">
                Example: &quot;Build a todo API with title, description,
                completed status, and due date&quot;
              </p>
            </div>
          )}
          {messages.map((msg, idx) => {
            // Only show "ready" banner on the very last assistant message
            const isLastAssistant =
              msg.role === "assistant" &&
              !messages.slice(idx + 1).some((m) => m.role === "assistant");
            return (
              <ChatMessage
                key={msg.id}
                message={msg}
                isLastAssistantMessage={isLastAssistant}
                onOptionSelect={
                  msg.askUser && !msg.askUser.answered
                    ? (answer) => handleOptionSelect(msg.id, answer)
                    : undefined
                }
              />
            );
          })}
          <div ref={bottomRef} />
        </div>
      </div>
      <ChatInput
        onSend={onSend}
        disabled={isLoading || isAgentWorking}
        placeholder={
          isAgentWorking
            ? "Agent is working..."
            : "Describe what you want to build..."
        }
      />
    </div>
  );
}
