"use client";

import { ChatMessage } from "@/lib/types";
import { Sparkles, CheckCircle2, Circle, Loader2 } from "lucide-react";

interface Props {
  msg: ChatMessage;
}

export default function BuildProgress({ msg }: Props) {
  const tasks = msg.buildTasks || [];
  const currentAction = msg.currentAction;
  const hasRunning = tasks.some((t) => t.status === "running");

  return (
    <div className="px-4 py-3 flex gap-3 justify-start">
      <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-bg-secondary text-text-primary">
        <Sparkles className="w-4 h-4 text-accent" />
      </div>
      <div className="flex-1 max-w-[80%] rounded-2xl border border-border bg-chat-ai-bg shadow-sm overflow-hidden rounded-tl-sm">
        {/* Current action header */}
        {(hasRunning && currentAction) && (
          <div className="px-4 py-3 border-b border-border flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-accent shrink-0" />
            <span className="text-sm font-mono text-accent truncate">
              {currentAction}
            </span>
          </div>
        )}

        {/* Task checklist */}
        {tasks.length > 0 && (
          <div className="px-4 py-3 space-y-2.5">
            {tasks.map((task) => (
              <div key={task.id} className="flex items-center gap-2.5">
                {task.status === "complete" ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                ) : task.status === "running" ? (
                  <Loader2 className="w-4 h-4 animate-spin text-accent shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-text-muted shrink-0" />
                )}
                <span
                  className={`text-sm ${
                    task.status === "pending"
                      ? "text-text-muted"
                      : task.status === "running"
                      ? "text-text-primary font-medium"
                      : "text-text-secondary"
                  }`}
                >
                  {task.description}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Empty state before tasks arrive */}
        {tasks.length === 0 && (
          <div className="px-4 py-3 flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-accent shrink-0" />
            <span className="text-sm text-text-secondary">
              Preparing build...
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
