"use client";

import { GitCommit } from "@/lib/types";
import { GitCommitHorizontal } from "lucide-react";

interface Props {
  commits: GitCommit[];
}

export default function GitLog({ commits }: Props) {
  if (commits.length === 0) {
    return <div className="text-zinc-500 text-sm p-4">No commits yet.</div>;
  }

  return (
    <div className="p-2 text-sm">
      {commits.map((c) => (
        <div
          key={c.hash}
          className="flex items-start gap-2 py-1.5 px-1 hover:bg-zinc-800 rounded"
        >
          <GitCommitHorizontal className="w-4 h-4 mt-0.5 text-zinc-500 shrink-0" />
          <div className="min-w-0">
            <span className="font-mono text-yellow-400 text-xs">{c.hash}</span>
            <p className="text-zinc-300 truncate">{c.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
