"use client";

import { GitCommit } from "@/lib/types";
import { GitCommitHorizontal } from "lucide-react";

interface Props {
  commits: GitCommit[];
}

export default function GitLog({ commits }: Props) {
  if (commits.length === 0) {
    return (
      <div className="text-text-muted text-sm p-4">
        No changes have been committed yet.
      </div>
    );
  }

  return (
    <div className="p-4 text-sm space-y-3">
      {commits.map((c) => (
        <div
          key={c.hash}
          className="flex items-start gap-3"
        >
          <div className="flex flex-col items-center pt-0.5">
            <span className="w-2 h-2 rounded-full bg-[#D4F79A]" />
            <span className="flex-1 w-px bg-border mt-1" />
          </div>
          <div className="min-w-0 flex-1 bg-[#FAFAFA] border border-border rounded-2xl px-3 py-2.5">
            <div className="flex items-center gap-2 mb-1">
              <GitCommitHorizontal className="w-4 h-4 text-text-muted shrink-0" />
              <span className="font-mono text-[11px] text-yellow-600 truncate">
                {c.hash}
              </span>
            </div>
            <p className="text-xs text-text-primary">{c.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
