"use client";

import { useState, useMemo } from "react";
import { File, Folder, FolderOpen, ChevronRight, ChevronDown } from "lucide-react";
import clsx from "clsx";

interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: TreeNode[];
}

function buildTree(files: string[]): TreeNode[] {
  const root: TreeNode[] = [];
  const dirs = new Map<string, TreeNode>();

  for (const filePath of files) {
    const parts = filePath.split("/");
    let currentChildren = root;
    let currentPath = "";

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLast = i === parts.length - 1;

      if (isLast) {
        currentChildren.push({ name: part, path: filePath, isDir: false, children: [] });
      } else {
        let dirNode = dirs.get(currentPath);
        if (!dirNode) {
          dirNode = { name: part, path: currentPath, isDir: true, children: [] };
          dirs.set(currentPath, dirNode);
          currentChildren.push(dirNode);
        }
        currentChildren = dirNode.children;
      }
    }
  }

  return root;
}

interface TreeNodeProps {
  node: TreeNode;
  depth: number;
  selectedFile: string | null;
  onFileSelect: (path: string) => void;
  defaultExpanded: boolean;
}

function TreeNodeComponent({ node, depth, selectedFile, onFileSelect, defaultExpanded }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (!node.isDir) {
    return (
      <button
        onClick={() => onFileSelect(node.path)}
        className={clsx(
          "flex items-center gap-1.5 py-0.5 px-1 w-full text-left text-xs font-mono rounded hover:bg-bg-hover",
          selectedFile === node.path ? "bg-bg-secondary text-text-primary" : "text-text-secondary"
        )}
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        <File className="w-3.5 h-3.5 text-text-muted shrink-0" />
        <span className="truncate">{node.name}</span>
      </button>
    );
  }

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 py-0.5 px-1 w-full text-left text-xs font-mono text-text-primary hover:bg-bg-hover rounded"
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 text-text-muted shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 text-text-muted shrink-0" />
        )}
        {expanded ? (
          <FolderOpen className="w-3.5 h-3.5 text-yellow-400 shrink-0" />
        ) : (
          <Folder className="w-3.5 h-3.5 text-yellow-400 shrink-0" />
        )}
        <span className="truncate">{node.name}</span>
      </button>
      {expanded && (
        <div>
          {node.children
            .sort((a, b) => {
              if (a.isDir && !b.isDir) return -1;
              if (!a.isDir && b.isDir) return 1;
              return a.name.localeCompare(b.name);
            })
            .map((child) => (
              <TreeNodeComponent
                key={child.path}
                node={child}
                depth={depth + 1}
                selectedFile={selectedFile}
                onFileSelect={onFileSelect}
                defaultExpanded={depth < 1}
              />
            ))}
        </div>
      )}
    </div>
  );
}

interface Props {
  files: string[];
  selectedFile: string | null;
  onFileSelect: (path: string) => void;
}

export default function FileExplorer({ files, selectedFile, onFileSelect }: Props) {
  const tree = useMemo(() => buildTree(files), [files]);

  if (files.length === 0) {
    return (
      <div className="text-text-muted text-xs p-3">
        No files yet. Start a conversation to generate your project.
      </div>
    );
  }

  return (
    <div className="py-1 overflow-y-auto h-full">
      {tree
        .sort((a, b) => {
          if (a.isDir && !b.isDir) return -1;
          if (!a.isDir && b.isDir) return 1;
          return a.name.localeCompare(b.name);
        })
        .map((node) => (
          <TreeNodeComponent
            key={node.path}
            node={node}
            depth={0}
            selectedFile={selectedFile}
            onFileSelect={onFileSelect}
            defaultExpanded={true}
          />
        ))}
    </div>
  );
}
