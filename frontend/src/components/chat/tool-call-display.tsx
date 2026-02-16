"use client";

import { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  ChevronRight,
  FileText,
  Terminal,
  Search,
  GitCommit,
  Loader2,
  Check,
  AlertCircle,
} from "lucide-react";
import type { ToolCall } from "@/lib/types";

const toolIcons: Record<string, React.ElementType> = {
  read_file: FileText,
  write_file: FileText,
  edit_file: FileText,
  run_command: Terminal,
  list_directory: Search,
  search_codebase: Search,
  git_commit: GitCommit,
};

export function ToolCallDisplay({ toolCall }: { toolCall: ToolCall }) {
  const [open, setOpen] = useState(false);
  const Icon = toolIcons[toolCall.name] || Terminal;

  let parsedArgs: Record<string, any> = {};
  try {
    parsedArgs = JSON.parse(toolCall.arguments);
  } catch {}

  const summary = getToolSummary(toolCall.name, parsedArgs);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex items-center gap-2 w-full text-left text-xs px-3 py-1.5 rounded-md bg-muted/50 hover:bg-muted transition-colors">
        <ChevronRight
          className={`h-3 w-3 shrink-0 transition-transform ${
            open ? "rotate-90" : ""
          }`}
        />
        <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span className="font-medium text-muted-foreground">
          {toolCall.name}
        </span>
        <span className="text-muted-foreground truncate flex-1">
          {summary}
        </span>
        {toolCall.status === "running" ? (
          <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
        ) : toolCall.is_error ? (
          <AlertCircle className="h-3 w-3 text-red-500" />
        ) : (
          <Check className="h-3 w-3 text-green-500" />
        )}
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-1">
        <div className="text-xs rounded-md bg-muted/30 p-3 space-y-2 overflow-hidden">
          <div>
            <span className="font-semibold text-muted-foreground">Args: </span>
            <pre className="mt-1 whitespace-pre-wrap break-all text-[11px] max-h-[200px] overflow-auto">
              {JSON.stringify(parsedArgs, null, 2)}
            </pre>
          </div>
          {toolCall.result && (
            <div>
              <span className="font-semibold text-muted-foreground">
                Result:{" "}
              </span>
              <pre className="mt-1 whitespace-pre-wrap break-all text-[11px] max-h-[300px] overflow-auto">
                {toolCall.result}
              </pre>
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function getToolSummary(
  name: string,
  args: Record<string, any>
): string {
  switch (name) {
    case "read_file":
      return args.path || "";
    case "write_file":
      return args.path || "";
    case "edit_file":
      return args.path || "";
    case "run_command":
      return args.command || "";
    case "list_directory":
      return args.path || ".";
    case "search_codebase":
      return `"${args.pattern || ""}"`;
    case "git_commit":
      return args.message || "";
    case "ask_user":
      return args.question?.substring(0, 60) || "";
    default:
      return "";
  }
}
