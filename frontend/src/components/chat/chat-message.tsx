"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { User, Bot, Loader2, Check, MessageSquare, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GenerationProgress } from "./generation-progress";
import type { ChatMessage as ChatMessageType, AskUserOption } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessageType;
  isLastAssistantMessage?: boolean;
  onOptionSelect?: (answer: string) => void;
}

export function ChatMessage({ message, isLastAssistantMessage, onOptionSelect }: ChatMessageProps) {
  const [selectedOptions, setSelectedOptions] = useState<Set<string>>(
    new Set()
  );
  const [customInput, setCustomInput] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);

  if (message.role === "user") {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary text-primary-foreground px-4 py-2.5">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center">
          <User className="h-4 w-4" />
        </div>
      </div>
    );
  }

  const hasOptions =
    message.askUser?.options && message.askUser.options.length > 0;
  const isMultiSelect = message.askUser?.options?.some(
    (o) => o.multi_select
  );
  const isAnswered = message.askUser?.answered;
  const hasToolCalls = message.toolCalls && message.toolCalls.length > 0;
  const isGenerationDone =
    !message.isStreaming && hasToolCalls && !message.askUser && isLastAssistantMessage;

  const handleSingleSelect = (option: AskUserOption) => {
    if (isAnswered || !onOptionSelect) return;
    onOptionSelect(option.label);
  };

  const handleMultiSubmit = () => {
    if (selectedOptions.size === 0 || !onOptionSelect) return;
    onOptionSelect(Array.from(selectedOptions).join(", "));
  };

  const toggleOption = (label: string) => {
    if (isAnswered) return;
    setSelectedOptions((prev) => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  };

  const handleCustomSubmit = () => {
    if (!customInput.trim() || !onOptionSelect) return;
    onOptionSelect(customInput.trim());
  };

  // Assistant message
  return (
    <div className="flex gap-3">
      <div className="shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        {/* Text content */}
        {message.content && (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}

        {/* Generation progress indicator (replaces verbose tool call list) */}
        {hasToolCalls && message.isStreaming && (
          <GenerationProgress
            toolCalls={message.toolCalls!}
            isStreaming={!!message.isStreaming}
          />
        )}

        {/* Generation complete indicator */}
        {isGenerationDone && (
          <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/30 px-4 py-2.5">
            <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 shrink-0" />
            <span className="text-sm font-medium text-green-700 dark:text-green-300">
              Your API is ready! You can start the containers below to test it.
            </span>
          </div>
        )}

        {/* Streaming indicator (when no content and no tools yet) */}
        {message.isStreaming &&
          !message.content &&
          (!message.toolCalls || message.toolCalls.length === 0) && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Thinking...</span>
            </div>
          )}

        {/* Ask user question with options */}
        {message.askUser && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30 p-4 space-y-3">
            <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
              {message.askUser.question}
            </p>

            {hasOptions && !isAnswered && (
              <div className="space-y-2">
                {message.askUser.options!.map((option) => (
                  <button
                    key={option.label}
                    onClick={() =>
                      isMultiSelect
                        ? toggleOption(option.label)
                        : handleSingleSelect(option)
                    }
                    className={`w-full text-left rounded-lg border px-3 py-2.5 text-sm transition-all hover:shadow-sm ${
                      selectedOptions.has(option.label)
                        ? "border-blue-500 bg-blue-100 dark:bg-blue-900/40 ring-1 ring-blue-500"
                        : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900 hover:border-blue-300 dark:hover:border-blue-600"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {isMultiSelect && (
                        <div
                          className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                            selectedOptions.has(option.label)
                              ? "bg-blue-500 border-blue-500"
                              : "border-gray-300 dark:border-gray-600"
                          }`}
                        >
                          {selectedOptions.has(option.label) && (
                            <Check className="h-3 w-3 text-white" />
                          )}
                        </div>
                      )}
                      <div className="flex-1">
                        <span className="font-medium text-gray-900 dark:text-gray-100">
                          {option.label}
                        </span>
                        {option.description && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {option.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </button>
                ))}

                {/* Multi-select confirm button */}
                {isMultiSelect && selectedOptions.size > 0 && (
                  <Button
                    onClick={handleMultiSubmit}
                    size="sm"
                    className="w-full"
                  >
                    Confirm selection ({selectedOptions.size})
                  </Button>
                )}

                {/* Custom answer toggle */}
                {!showCustomInput ? (
                  <button
                    onClick={() => setShowCustomInput(true)}
                    className="flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1"
                  >
                    <MessageSquare className="h-3 w-3" />
                    Type a custom answer instead
                  </button>
                ) : (
                  <div className="flex gap-2 mt-1">
                    <input
                      type="text"
                      value={customInput}
                      onChange={(e) => setCustomInput(e.target.value)}
                      onKeyDown={(e) =>
                        e.key === "Enter" && handleCustomSubmit()
                      }
                      placeholder="Type your answer..."
                      className="flex-1 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm"
                      autoFocus
                    />
                    <Button
                      onClick={handleCustomSubmit}
                      size="sm"
                      disabled={!customInput.trim()}
                    >
                      Send
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Answered state */}
            {isAnswered && (
              <div className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
                <Check className="h-3 w-3" />
                Answered
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
