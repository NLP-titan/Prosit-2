"use client";

import { File, Folder } from "lucide-react";

interface Props {
  files: string[];
}

export default function FileTree({ files }: Props) {
  if (files.length === 0) {
    return <div className="text-zinc-500 text-sm p-4">No files yet.</div>;
  }

  return (
    <div className="p-2 text-sm font-mono">
      {files.map((f) => {
        const depth = f.split("/").length - 1;
        const name = f.split("/").pop() || f;
        const isDir = false; // all entries from the backend are files
        return (
          <div
            key={f}
            className="flex items-center gap-1.5 py-0.5 text-zinc-300 hover:text-white hover:bg-zinc-800 rounded px-1"
            style={{ paddingLeft: `${depth * 12 + 4}px` }}
          >
            {isDir ? (
              <Folder className="w-3.5 h-3.5 text-yellow-400 shrink-0" />
            ) : (
              <File className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            )}
            <span className="truncate">{name}</span>
          </div>
        );
      })}
    </div>
  );
}
