"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import type { ToolCall } from "@/lib/types";

// Dynamic phrases that cycle during generation — inspired by Claude Code
const PROGRESS_PHRASES = [
  "Thinking through the architecture",
  "Designing your database models",
  "Crafting the API endpoints",
  "Writing clean, production code",
  "Setting up data validation",
  "Wiring up the routes",
  "Connecting all the pieces",
  "Making sure everything fits",
  "Adding the finishing touches",
  "Almost there",
];

// Map tool names to user-friendly activity labels
function getToolActivity(name: string, args: Record<string, any>): string {
  switch (name) {
    case "write_file":
      return `Creating ${simplifyPath(args.path)}`;
    case "edit_file":
      return `Updating ${simplifyPath(args.path)}`;
    case "read_file":
      return `Reading ${simplifyPath(args.path)}`;
    case "run_command":
      return "Running a command";
    case "list_directory":
      return "Exploring project files";
    case "search_codebase":
      return "Searching the codebase";
    case "git_commit":
      return "Saving progress";
    default:
      return "Working";
  }
}

function simplifyPath(path?: string): string {
  if (!path) return "a file";
  const parts = path.split("/");
  return parts[parts.length - 1] || path;
}

interface GenerationProgressProps {
  toolCalls: ToolCall[];
  isStreaming: boolean;
}

export function GenerationProgress({
  toolCalls,
  isStreaming,
}: GenerationProgressProps) {
  const [phraseIndex, setPhraseIndex] = useState(0);

  // Cycle through phrases every 3 seconds
  useEffect(() => {
    if (!isStreaming) return;
    const interval = setInterval(() => {
      setPhraseIndex((prev) => (prev + 1) % PROGRESS_PHRASES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [isStreaming]);

  if (toolCalls.length === 0) return null;

  const runningTools = toolCalls.filter((tc) => tc.status === "running");
  const completedCount = toolCalls.filter((tc) => tc.status === "done").length;

  // Get the latest activity
  let currentActivity: string;
  if (runningTools.length > 0) {
    const latest = runningTools[runningTools.length - 1];
    let args: Record<string, any> = {};
    try {
      args = JSON.parse(latest.arguments);
    } catch {}
    currentActivity = getToolActivity(latest.name, args);
  } else {
    currentActivity = PROGRESS_PHRASES[phraseIndex];
  }

  return (
    <div className="rounded-lg border border-border/50 bg-muted/20 px-4 py-3 space-y-2">
      {/* Main progress line */}
      <div className="flex items-center gap-2.5">
        {isStreaming ? (
          <Loader2 className="h-4 w-4 animate-spin text-primary shrink-0" />
        ) : (
          <Sparkles className="h-4 w-4 text-primary shrink-0" />
        )}
        <span className="text-sm font-medium text-foreground animate-in fade-in duration-300">
          {currentActivity}...
        </span>
      </div>

      {/* Step counter */}
      {completedCount > 0 && (
        <div className="flex items-center gap-2 ml-6.5">
          <div className="flex gap-0.5">
            {toolCalls.slice(-8).map((tc, i) => (
              <div
                key={tc.id || i}
                className={`w-1.5 h-1.5 rounded-full transition-colors ${
                  tc.status === "done"
                    ? tc.is_error
                      ? "bg-red-400"
                      : "bg-primary"
                    : "bg-muted-foreground/30 animate-pulse"
                }`}
              />
            ))}
          </div>
          <span className="text-xs text-muted-foreground">
            {completedCount} step{completedCount !== 1 ? "s" : ""} completed
          </span>
        </div>
      )}
    </div>
  );
}
