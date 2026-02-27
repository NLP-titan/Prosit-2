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
    { id: "status", label: "Overview" },
    { id: "files", label: "Files" },
    { id: "git", label: "Changes" },
  ];

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="border-b border-border bg-[#FAFAFA]">
        <div className="flex px-2 py-1.5 gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={clsx(
                "px-3 py-1.5 text-xs font-medium rounded-full transition-colors",
                tab === t.id
                  ? "bg-black text-white"
                  : "text-text-secondary hover:text-text-primary hover:bg-bg-secondary"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {tab === "status" && (
          <div className="p-4 space-y-4 text-sm">
            <div>
              <div className="text-[11px] text-text-muted uppercase tracking-[0.16em] mb-1">
                Deployment state
              </div>
              <div className="text-sm font-mono">
                <span
                  className={clsx(
                    "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px]",
                    projectState === "running"
                      ? "bg-[#D4F79A] text-black"
                      : projectState === "error"
                        ? "bg-red-100 text-red-700"
                        : "bg-bg-secondary text-text-secondary"
                  )}
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                  {projectState}
                </span>
              </div>
            </div>

            {swaggerUrl && (
              <div>
                <div className="text-[11px] text-text-muted uppercase tracking-[0.16em] mb-1">
                  Interactive docs
                </div>
                <a
                  href={swaggerUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-accent hover:opacity-80 underline break-all"
                >
                  {swaggerUrl}
                </a>
              </div>
            )}

            {apiUrl && (
              <div>
                <div className="text-[11px] text-text-muted uppercase tracking-[0.16em] mb-1">
                  API base URL
                </div>
                <a
                  href={apiUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-accent hover:opacity-80 underline break-all"
                >
                  {apiUrl}
                </a>
              </div>
            )}

            <div className="text-xs text-text-secondary bg-bg-secondary/60 rounded-2xl px-3 py-2.5 space-y-1">
              <p className="font-medium text-text-primary">
                What this means
              </p>
              <p>
                When the state is <span className="font-mono">running</span>,
                your backend is live and ready for your frontend to call.
              </p>
              <p>
                Use the links above to explore your API in the browser or from
                tools like Postman, curl, or your own app.
              </p>
            </div>
          </div>
        )}

        {tab === "files" && <FileTree files={files} />}
        {tab === "git" && <GitLog commits={commits} />}
      </div>
    </div>
  );
}
