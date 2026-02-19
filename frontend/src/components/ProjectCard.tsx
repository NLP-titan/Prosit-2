"use client";

import { Project } from "@/lib/types";
import { Trash2 } from "lucide-react";
import clsx from "clsx";

const STATE_COLORS: Record<string, string> = {
  running: "bg-emerald-900 text-emerald-300",
  error: "bg-red-900 text-red-300",
  building: "bg-yellow-900 text-yellow-300",
  generating: "bg-blue-900 text-blue-300",
  scaffolded: "bg-purple-900 text-purple-300",
  stopped: "bg-bg-tertiary text-text-secondary",
  created: "bg-bg-secondary text-text-secondary",
};

interface Props {
  project: Project;
  onClick: () => void;
  onDelete: (e: React.MouseEvent) => void;
}

export default function ProjectCard({ project, onClick, onDelete }: Props) {
  const colorClass = STATE_COLORS[project.state] || STATE_COLORS.created;

  return (
    <div
      onClick={onClick}
      className="group relative border border-border rounded-lg p-4 hover:border-text-muted hover:bg-bg-secondary/50 cursor-pointer transition-colors"
    >
      <button
        onClick={onDelete}
        className="absolute top-3 right-3 p-1.5 rounded text-text-muted opacity-0 group-hover:opacity-100 hover:text-red-400 hover:bg-bg-tertiary transition-all"
        title="Delete project"
      >
        <Trash2 className="w-4 h-4" />
      </button>

      <div className="flex items-center gap-2 mb-2">
        <h3 className="font-semibold text-sm truncate">
          {project.name || project.id}
        </h3>
        <span className={clsx("text-[10px] px-1.5 py-0.5 rounded shrink-0", colorClass)}>
          {project.state}
        </span>
      </div>

      {project.description && (
        <p className="text-xs text-text-secondary line-clamp-2 mb-2">
          {project.description}
        </p>
      )}

      <p className="text-[10px] text-text-muted">
        {new Date(project.created_at).toLocaleDateString()}
      </p>
    </div>
  );
}
