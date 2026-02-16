"use client";

import { useState } from "react";
import { ChevronRight, File, Folder, FolderOpen } from "lucide-react";
import type { FileNode } from "@/lib/types";

interface FileExplorerProps {
  tree: FileNode | null;
  onFileSelect: (path: string) => void;
  selectedPath?: string;
}

export function FileExplorer({
  tree,
  onFileSelect,
  selectedPath,
}: FileExplorerProps) {
  if (!tree) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        No files yet. Start a conversation to generate code.
      </div>
    );
  }

  return (
    <div className="text-sm p-2">
      {tree.children?.map((node) => (
        <TreeNode
          key={node.name}
          node={node}
          depth={0}
          onFileSelect={onFileSelect}
          selectedPath={selectedPath}
        />
      ))}
    </div>
  );
}

function TreeNode({
  node,
  depth,
  onFileSelect,
  selectedPath,
}: {
  node: FileNode;
  depth: number;
  onFileSelect: (path: string) => void;
  selectedPath?: string;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isDir = node.type === "directory";
  const isSelected = node.path === selectedPath;

  if (isDir) {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 w-full text-left px-1 py-0.5 rounded hover:bg-muted transition-colors"
          style={{ paddingLeft: `${depth * 12 + 4}px` }}
        >
          <ChevronRight
            className={`h-3 w-3 shrink-0 transition-transform ${
              expanded ? "rotate-90" : ""
            }`}
          />
          {expanded ? (
            <FolderOpen className="h-4 w-4 text-blue-500 shrink-0" />
          ) : (
            <Folder className="h-4 w-4 text-blue-500 shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
        </button>
        {expanded &&
          node.children?.map((child) => (
            <TreeNode
              key={child.name}
              node={child}
              depth={depth + 1}
              onFileSelect={onFileSelect}
              selectedPath={selectedPath}
            />
          ))}
      </div>
    );
  }

  return (
    <button
      onClick={() => node.path && onFileSelect(node.path)}
      className={`flex items-center gap-1 w-full text-left px-1 py-0.5 rounded transition-colors ${
        isSelected ? "bg-primary/10 text-primary" : "hover:bg-muted"
      }`}
      style={{ paddingLeft: `${depth * 12 + 20}px` }}
    >
      <File className="h-4 w-4 text-muted-foreground shrink-0" />
      <span className="truncate">{node.name}</span>
    </button>
  );
}
