"use client";

import { ChatMessage, BuildTask } from "@/lib/types";
import { Sparkles, CheckCircle2, Circle, Loader2, ChevronRight } from "lucide-react";
import { useState } from "react";

// Map raw task types to high-level build steps
const STEP_ORDER = ["scaffold", "create_models", "create_routes", "docker_up"] as const;

const STEP_LABELS: Record<string, string> = {
  scaffold: "Set up project",
  create_models: "Create database models",
  create_routes: "Build API routes",
  docker_up: "Deploy and verify",
};

interface BuildStep {
  key: string;
  label: string;
  status: "pending" | "running" | "complete";
  taskIds: string[];
}

function groupTasksIntoSteps(tasks: BuildTask[]): BuildStep[] {
  const groups: Record<string, BuildTask[]> = {};

  for (const task of tasks) {
    const key = task.taskType || "other";
    if (!groups[key]) groups[key] = [];
    groups[key].push(task);
  }

  const steps: BuildStep[] = [];
  for (const key of STEP_ORDER) {
    const groupTasks = groups[key];
    if (!groupTasks) continue;
    const allComplete = groupTasks.every((t) => t.status === "complete");
    const anyRunning = groupTasks.some((t) => t.status === "running");
    steps.push({
      key,
      label: STEP_LABELS[key] || key,
      status: allComplete ? "complete" : anyRunning ? "running" : "pending",
      taskIds: groupTasks.map((t) => t.id),
    });
  }

  // Add any unknown types at the end
  for (const [key, groupTasks] of Object.entries(groups)) {
    if (STEP_ORDER.includes(key as typeof STEP_ORDER[number])) continue;
    const allComplete = groupTasks.every((t) => t.status === "complete");
    const anyRunning = groupTasks.some((t) => t.status === "running");
    steps.push({
      key,
      label: STEP_LABELS[key] || key,
      status: allComplete ? "complete" : anyRunning ? "running" : "pending",
      taskIds: groupTasks.map((t) => t.id),
    });
  }

  return steps;
}

// Get a plain-English description of what's happening right now
function getCurrentStepLabel(steps: BuildStep[]): string {
  const running = steps.find((s) => s.status === "running");
  if (running) return running.label;
  return "";
}

interface Props {
  msg: ChatMessage;
}

export default function BuildProgress({ msg }: Props) {
  const [expanded, setExpanded] = useState(false);
  const tasks = msg.buildTasks || [];
  const currentAction = msg.currentAction;
  const steps = groupTasksIntoSteps(tasks);
  const currentStepLabel = getCurrentStepLabel(steps);
  const allDone = steps.length > 0 && steps.every((s) => s.status === "complete");

  return (
    <div className="px-4 py-3 flex gap-3 justify-start">
      <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-bg-secondary text-text-primary">
        <Sparkles className="w-4 h-4 text-accent" />
      </div>
      <div className="flex-1 max-w-[80%] rounded-2xl border border-border bg-chat-ai-bg shadow-sm overflow-hidden rounded-tl-sm">
        {/* Dynamic header — current tool action + step description */}
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-bg-secondary/30 transition-colors"
        >
          {allDone ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
          ) : (
            <Loader2 className="w-4 h-4 animate-spin text-accent shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            {currentAction && !allDone ? (
              <>
                <p className="text-sm text-text-primary truncate">
                  {currentAction}
                </p>
                {currentStepLabel && (
                  <p className="text-xs text-text-muted mt-0.5">
                    {currentStepLabel}
                  </p>
                )}
              </>
            ) : allDone ? (
              <p className="text-sm text-text-primary">Build complete</p>
            ) : (
              <p className="text-sm text-text-secondary">
                {currentStepLabel || "Preparing build..."}
              </p>
            )}
          </div>
          <ChevronRight
            className={`w-4 h-4 text-text-muted shrink-0 transition-transform ${
              expanded ? "rotate-90" : ""
            }`}
          />
        </button>

        {/* Step checklist — collapsed by default */}
        {expanded && steps.length > 0 && (
          <div className="px-4 pb-3 space-y-2">
            {steps.map((step) => (
              <div key={step.key} className="flex items-center gap-2.5">
                {step.status === "complete" ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                ) : step.status === "running" ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-accent shrink-0" />
                ) : (
                  <Circle className="w-3.5 h-3.5 text-text-muted shrink-0" />
                )}
                <span
                  className={`text-xs ${
                    step.status === "pending"
                      ? "text-text-muted"
                      : step.status === "running"
                      ? "text-text-primary"
                      : "text-text-secondary"
                  }`}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
