"use client";

import { ToolGroup } from "@/lib/types";
import { Loader2, CheckCircle2, ChevronDown, ChevronRight, Wrench } from "lucide-react";
import { useState } from "react";
import clsx from "clsx";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark, oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTheme } from "./ThemeProvider";

function getToolSummary(tool: string, args?: Record<string, unknown>): string {
  const path = args?.path as string | undefined;
  const cmd = args?.command as string | undefined;
  switch (tool) {
    case "write_file":
      return path ? `Writing ${path}` : "Writing file";
    case "edit_file":
      return path ? `Editing ${path}` : "Editing file";
    case "read_file":
      return path ? `Reading ${path}` : "Reading file";
    case "list_directory":
      return path ? `Listing ${path}` : "Listing directory";
    case "run_command":
      return cmd ? `Running: ${cmd.length > 50 ? cmd.slice(0, 50) + "..." : cmd}` : "Running command";
    case "git_commit":
      return "Committing changes";
    case "git_log":
      return "Checking git history";
    case "docker_compose_up":
      return "Building and starting containers";
    case "docker_compose_down":
      return "Stopping containers";
    case "docker_status":
      return "Checking container status";
    case "docker_logs":
      return "Reading container logs";
    case "scaffold_project":
      return "Scaffolding project";
    case "build_complete":
      return "Finalizing build";
    default:
      return tool;
  }
}

function getLanguageFromPath(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() || "";
  const map: Record<string, string> = {
    py: "python", ts: "typescript", js: "javascript", json: "json",
    yml: "yaml", yaml: "yaml", sql: "sql", md: "markdown", toml: "toml",
    ini: "ini", sh: "bash", txt: "text",
  };
  return map[ext] || "text";
}

interface Props {
  group: ToolGroup;
  showDetails: boolean;
}

export default function ToolActivity({ group, showDetails }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const { theme } = useTheme();
  const isOpen = showDetails || expanded;

  const runningStep = group.steps.find((s) => s.status === "running");
  const doneCount = group.steps.filter((s) => s.status === "done").length;
  const isActive = group.isActive;

  const summary = runningStep
    ? getToolSummary(runningStep.tool, runningStep.args) + "..."
    : `${doneCount} tool${doneCount !== 1 ? "s" : ""} executed`;

  const toggleStep = (index: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <div className="px-4 py-2">
      <button
        onClick={() => setExpanded(!isOpen)}
        className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors w-full text-left"
      >
        {isActive && runningStep ? (
          <Loader2 className="w-4 h-4 animate-spin text-accent shrink-0" />
        ) : (
          <Wrench className="w-4 h-4 text-text-muted shrink-0" />
        )}
        <span className="flex-1 font-mono text-xs">{summary}</span>
        {isOpen ? (
          <ChevronDown className="w-3.5 h-3.5 shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 shrink-0" />
        )}
      </button>

      {isOpen && (
        <div className="mt-1.5 ml-6 space-y-1">
          {group.steps.map((step, i) => {
            const stepLabel = getToolSummary(step.tool, step.args);
            const hasContent = (step.tool === "write_file" && !!step.args?.content) ||
              (step.tool === "edit_file" && !!step.args?.old_text);
            const isStepExpanded = expandedSteps.has(i);

            return (
              <div key={i} className="text-xs">
                <div className="flex items-start gap-2">
                  {step.status === "running" ? (
                    <Loader2 className="w-3 h-3 animate-spin text-accent mt-0.5 shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-3 h-3 text-emerald-500 mt-0.5 shrink-0" />
                  )}
                  <div className="min-w-0 flex-1">
                    <button
                      onClick={() => hasContent && toggleStep(i)}
                      className={clsx(
                        "font-mono text-left",
                        step.status === "running" ? "text-accent" : "text-text-secondary",
                        hasContent && "hover:text-text-primary cursor-pointer"
                      )}
                    >
                      {stepLabel}
                      {hasContent && (
                        <span className="text-text-muted ml-1">
                          {isStepExpanded ? "[-]" : "[+]"}
                        </span>
                      )}
                    </button>

                    {isStepExpanded && step.tool === "write_file" && !!step.args?.content && (
                      <div className="mt-1 rounded overflow-hidden border border-border">
                        <SyntaxHighlighter
                          language={getLanguageFromPath(step.args.path as string || "")}
                          style={theme === "dark" ? oneDark : oneLight}
                          customStyle={{
                            margin: 0,
                            padding: "8px",
                            fontSize: "10px",
                            maxHeight: "200px",
                            background: theme === "dark" ? "rgba(0,0,0,0.3)" : "rgba(0,0,0,0.02)",
                          }}
                          showLineNumbers
                          lineNumberStyle={{
                            color: theme === "dark" ? "#52525b" : "#a1a1aa",
                            fontSize: "9px",
                          }}
                        >
                          {(step.args.content as string).slice(0, 5000)}
                        </SyntaxHighlighter>
                      </div>
                    )}

                    {isStepExpanded && step.tool === "edit_file" && !!step.args?.old_text && (
                      <div className="mt-1 space-y-1">
                        <div className="rounded overflow-hidden border border-red-900/50">
                          <div className="text-[10px] text-red-400 px-2 py-0.5 bg-red-900/20">old</div>
                          <pre className="text-[10px] text-red-300/70 px-2 py-1 bg-red-900/10 overflow-x-auto max-h-24 whitespace-pre-wrap">
                            {(step.args.old_text as string).slice(0, 2000)}
                          </pre>
                        </div>
                        <div className="rounded overflow-hidden border border-emerald-900/50">
                          <div className="text-[10px] text-emerald-400 px-2 py-0.5 bg-emerald-900/20">new</div>
                          <pre className="text-[10px] text-emerald-300/70 px-2 py-1 bg-emerald-900/10 overflow-x-auto max-h-24 whitespace-pre-wrap">
                            {(step.args.new_text as string || "").slice(0, 2000)}
                          </pre>
                        </div>
                      </div>
                    )}

                    {!hasContent && step.result && (
                      <pre className="mt-0.5 text-text-muted bg-bg-secondary/50 rounded p-1.5 overflow-x-auto max-h-20 whitespace-pre-wrap text-[10px]">
                        {step.result.slice(0, 300)}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
