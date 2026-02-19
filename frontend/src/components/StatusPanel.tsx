"use client";

import { useState } from "react";
import { GitCommit } from "@/lib/types";
import FileTree from "./FileTree";
import GitLog from "./GitLog";
import clsx from "clsx";

type Tab = "status" | "files" | "git";

interface Props {
  projectState: string;
  files: string[];
  commits: GitCommit[];
  swaggerUrl: string | null;
  apiUrl: string | null;
}

export default function StatusPanel({ projectState, files, commits, swaggerUrl, apiUrl }: Props) {
  const [tab, setTab] = useState<Tab>("status");

  const tabs: { id: Tab; label: string }[] = [
    { id: "status", label: "Status" },
    { id: "files", label: "Files" },
    { id: "git", label: "Git" },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-zinc-700">
        <div className="flex">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={clsx(
                "px-4 py-2.5 text-sm transition-colors",
                tab === t.id
                  ? "text-white border-b-2 border-blue-500"
                  : "text-zinc-400 hover:text-white"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {tab === "status" && (
          <div className="p-4 space-y-4">
            <div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">State</div>
              <div className="text-sm font-mono">
                <span
                  className={clsx(
                    "inline-block px-2 py-0.5 rounded text-xs",
                    projectState === "running"
                      ? "bg-emerald-900 text-emerald-300"
                      : projectState === "error"
                        ? "bg-red-900 text-red-300"
                        : "bg-zinc-800 text-zinc-300"
                  )}
                >
                  {projectState}
                </span>
              </div>
            </div>

            {swaggerUrl && (
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  Swagger UI
                </div>
                <a
                  href={swaggerUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 text-sm underline"
                >
                  {swaggerUrl}
                </a>
              </div>
            )}

            {apiUrl && (
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  API URL
                </div>
                <a
                  href={apiUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 text-sm underline"
                >
                  {apiUrl}
                </a>
              </div>
            )}
          </div>
        )}

        {tab === "files" && <FileTree files={files} />}
        {tab === "git" && <GitLog commits={commits} />}
      </div>
    </div>
  );
}
