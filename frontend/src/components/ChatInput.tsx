"use client";

import { useState, useRef, useEffect, KeyboardEvent, ChangeEvent } from "react";
import { Send, Square } from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  onStop?: () => void;
  disabled: boolean;
  isAgentWorking: boolean;
}

export default function ChatInput({ onSend, onStop, disabled, isAgentWorking }: Props) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    const newHeight = Math.min(Math.max(ta.scrollHeight, 44), 200);
    ta.style.height = `${newHeight}px`;
  }, [text]);

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
      return;
    }

    // Auto-continue lists on Shift+Enter or just Enter (we handle Enter above for send)
    if (e.key === "Enter" && e.shiftKey) {
      const ta = e.currentTarget;
      const { selectionStart } = ta;
      const before = text.slice(0, selectionStart);
      const after = text.slice(selectionStart);

      // Find the current line
      const lastNewline = before.lastIndexOf("\n");
      const currentLine = before.slice(lastNewline + 1);

      // Check for numbered list: "1. ", "2. ", etc.
      const numMatch = currentLine.match(/^(\s*)(\d+)\.\s/);
      if (numMatch) {
        const indent = numMatch[1];
        const nextNum = parseInt(numMatch[2]) + 1;
        // If current line is just the number (empty item), remove it instead
        if (currentLine.trim() === `${numMatch[2]}.`) {
          e.preventDefault();
          setText(before.slice(0, lastNewline + 1) + after);
          return;
        }
        e.preventDefault();
        const insertion = `\n${indent}${nextNum}. `;
        setText(before + insertion + after);
        // Set cursor position after React re-render
        setTimeout(() => {
          ta.selectionStart = ta.selectionEnd = selectionStart + insertion.length;
        }, 0);
        return;
      }

      // Check for bullet list: "- ", "* "
      const bulletMatch = currentLine.match(/^(\s*)([-*])\s/);
      if (bulletMatch) {
        const indent = bulletMatch[1];
        const bullet = bulletMatch[2];
        if (currentLine.trim() === bullet) {
          e.preventDefault();
          setText(before.slice(0, lastNewline + 1) + after);
          return;
        }
        e.preventDefault();
        const insertion = `\n${indent}${bullet} `;
        setText(before + insertion + after);
        setTimeout(() => {
          ta.selectionStart = ta.selectionEnd = selectionStart + insertion.length;
        }, 0);
        return;
      }
    }
  }

  return (
    <div className="border-t border-border p-4">
      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Agent is working..." : "Describe your API..."}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-bg-secondary border border-border rounded-lg px-3 py-2.5 text-sm resize-none focus:outline-none focus:border-accent disabled:opacity-50 overflow-y-auto"
          style={{ minHeight: "44px", maxHeight: "200px" }}
        />
        {isAgentWorking ? (
          <button
            onClick={onStop}
            className="px-3 py-2.5 bg-red-600 hover:bg-red-700 rounded-lg transition-colors shrink-0 text-white"
            title="Stop agent"
          >
            <Square className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={disabled || !text.trim()}
            className="px-3 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 rounded-lg transition-colors shrink-0 text-white"
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
