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
    <div className="bg-white border border-border rounded-[24px] p-6 md:p-8 max-w-xl">
      <h3 className="text-lg font-semibold text-gray-900 mb-1">
        Deployment Status
      </h3>
      <p className="text-xs text-gray-500 mb-6">
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
                <div className="absolute left-4 top-7 bottom-[-20px] w-px bg-gray-100" />
              )}
              {/* icon */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 z-10 border-2 ${
                  status === "complete"
                    ? "bg-[#D4F79A] border-[#D4F79A] text-black"
                    : status === "loading"
                    ? "bg-white border-black text-black"
                    : "bg-gray-50 border-gray-200 text-gray-300"
                }`}
              >
                {status === "complete" && <Check className="w-4 h-4" />}
                {status === "loading" && (
                  <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-300 border-t-black animate-spin" />
                )}
                {status === "pending" && <Clock className="w-4 h-4" />}
              </div>
              {/* text */}
              <div className="pt-1">
                <p
                  className={`text-sm font-medium ${
                    status === "pending" ? "text-gray-400" : "text-gray-900"
                  }`}
                >
                  {label}
                </p>
                {status === "loading" && (
                  <p className="text-[11px] text-gray-500 mt-1">
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

