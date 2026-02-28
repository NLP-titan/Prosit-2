"use client";

import { Check, Clock } from "lucide-react";

interface Props {
  projectState: string;
  isAgentWorking: boolean;
}

type StepStatus = "complete" | "loading" | "pending";

const STEPS = [
  "Analyze requirements",
  "Design database structure",
  "Create application actions",
  "Publish securely to cloud",
] as const;

function computeStatuses(
  projectState: string,
  isAgentWorking: boolean
): StepStatus[] {
  switch (projectState) {
    case "created":
      return [isAgentWorking ? "loading" : "pending", "pending", "pending", "pending"];
    case "scaffolded":
      return ["complete", "loading", "pending", "pending"];
    case "building":
    case "generating":
      return ["complete", "complete", "loading", "pending"];
    case "running":
      return ["complete", "complete", "complete", "complete"];
    case "error":
      return ["complete", "complete", "pending", "pending"];
    case "stopped":
      return ["complete", "complete", "complete", "pending"];
    default:
      return ["pending", "pending", "pending", "pending"];
  }
}

export default function WorkspaceProgressView({
  projectState,
  isAgentWorking,
}: Props) {
  const statuses = computeStatuses(projectState, isAgentWorking);

  return (
    <div className="bg-bg-primary border border-border rounded-[24px] p-6 md:p-8 max-w-xl">
      <h3 className="text-lg font-semibold text-text-primary mb-1">
        Deployment Status
      </h3>
      <p className="text-xs text-text-muted mb-6">
        Track the agent&apos;s progress as it builds your infrastructure.
      </p>

      <div className="space-y-6">
        {STEPS.map((label, idx) => {
          const status = statuses[idx];
          const isLast = idx === STEPS.length - 1;
          return (
            <div key={label} className="relative flex gap-4">
              {/* vertical line */}
              {!isLast && (
                <div className="absolute left-4 top-7 bottom-[-20px] w-px bg-border" />
              )}
              {/* icon */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 z-10 border-2 ${
                  status === "complete"
                    ? "bg-accent/20 border-accent text-accent"
                    : status === "loading"
                    ? "bg-bg-primary border-text-primary text-text-primary"
                    : "bg-bg-secondary border-border text-text-muted"
                }`}
              >
                {status === "complete" && <Check className="w-4 h-4" />}
                {status === "loading" && (
                  <div className="w-3.5 h-3.5 rounded-full border-2 border-border border-t-text-primary animate-spin" />
                )}
                {status === "pending" && <Clock className="w-4 h-4" />}
              </div>
              {/* text */}
              <div className="pt-1">
                <p
                  className={`text-sm font-medium ${
                    status === "pending" ? "text-text-muted" : "text-text-primary"
                  }`}
                >
                  {label}
                </p>
                {status === "loading" && (
                  <p className="text-[11px] text-text-muted mt-1">
                    This step may take a few seconds…
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

