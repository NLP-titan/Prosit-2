"use client";

import { useCallback, useRef, useState } from "react";
import {
  sendMessage,
  getStreamUrl,
  getChatHistory,
} from "@/lib/api-client";
import { connectSSE } from "@/lib/sse-client";
import type { ChatMessage, ToolCall } from "@/lib/types";

export function useChat(projectId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isAgentWorking, setIsAgentWorking] = useState(false);
  const sseRef = useRef<{ close: () => void } | null>(null);
  const currentAssistantIdRef = useRef<string>("");

  const loadHistory = useCallback(async () => {
    try {
      const history = await getChatHistory(projectId);
      const mapped: ChatMessage[] = [];

      for (const msg of history) {
        if (msg.role === "user") {
          mapped.push({
            id: msg.id,
            role: "user",
            content: msg.content,
            timestamp: new Date(msg.created_at),
          });
        } else if (msg.role === "assistant") {
          mapped.push({
            id: msg.id,
            role: "assistant",
            content: msg.content,
            toolCalls: msg.tool_calls
              ? msg.tool_calls.map((tc: any) => ({
                  id: tc.id,
                  name: tc.function?.name || "",
                  arguments: tc.function?.arguments || "",
                  status: "done" as const,
                }))
              : undefined,
            timestamp: new Date(msg.created_at),
          });
        }
      }

      setMessages(mapped);
    } catch (err) {
      console.error("Failed to load history:", err);
    }
  }, [projectId]);

  const send = useCallback(
    async (content: string) => {
      // Add user message immediately
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setIsAgentWorking(true);

      try {
        // Trigger the agent
        await sendMessage(projectId, content);

        // Create a placeholder assistant message
        const assistantId = `assistant-${Date.now()}`;
        currentAssistantIdRef.current = assistantId;

        const assistantMsg: ChatMessage = {
          id: assistantId,
          role: "assistant",
          content: "",
          toolCalls: [],
          isStreaming: true,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // Connect to SSE stream
        const streamUrl = getStreamUrl(projectId);
        sseRef.current = connectSSE(streamUrl, {
          onMessageStart: () => {},

          onTextDelta: (text) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === currentAssistantIdRef.current
                  ? { ...m, content: (m.content || "") + text }
                  : m
              )
            );
          },

          onToolStart: (data) => {
            const newToolCall: ToolCall = {
              id: data.id,
              name: data.name,
              arguments: data.arguments,
              status: "running",
            };
            setMessages((prev) =>
              prev.map((m) =>
                m.id === currentAssistantIdRef.current
                  ? {
                      ...m,
                      toolCalls: [...(m.toolCalls || []), newToolCall],
                    }
                  : m
              )
            );
          },

          onToolResult: (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === currentAssistantIdRef.current
                  ? {
                      ...m,
                      toolCalls: (m.toolCalls || []).map((tc) =>
                        tc.id === data.id
                          ? {
                              ...tc,
                              result: data.result,
                              is_error: data.is_error,
                              status: "done" as const,
                            }
                          : tc
                      ),
                    }
                  : m
              )
            );
          },

          onAskUser: (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === currentAssistantIdRef.current
                  ? {
                      ...m,
                      isStreaming: false,
                      askUser: {
                        question: data.question,
                        toolCallId: data.tool_call_id,
                        options: data.options,
                      },
                    }
                  : m
              )
            );
            setIsAgentWorking(false);
            setIsLoading(false);
          },

          onMessageEnd: () => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === currentAssistantIdRef.current
                  ? { ...m, isStreaming: false }
                  : m
              )
            );
            setIsAgentWorking(false);
            setIsLoading(false);
          },

          onError: (message) => {
            console.error("SSE error:", message);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === currentAssistantIdRef.current
                  ? {
                      ...m,
                      content: (m.content || "") + `\n\nError: ${message}`,
                      isStreaming: false,
                    }
                  : m
              )
            );
            setIsAgentWorking(false);
            setIsLoading(false);
          },
        });
      } catch (err) {
        console.error("Failed to send message:", err);
        setIsAgentWorking(false);
        setIsLoading(false);
      }
    },
    [projectId]
  );

  return {
    messages,
    setMessages,
    isLoading,
    isAgentWorking,
    sendMessage: send,
    loadHistory,
  };
}
