"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FileViewerProps {
  path: string;
  content: string;
  onClose: () => void;
}

export function FileViewer({ path, content, onClose }: FileViewerProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30 shrink-0">
        <span className="text-sm font-medium truncate">{path}</span>
        <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={onClose}>
          <X className="h-3 w-3" />
        </Button>
      </div>
      <div className="flex-1 min-h-0 overflow-auto">
        <pre className="p-4 text-xs leading-relaxed font-mono whitespace-pre">
          <code>{content}</code>
        </pre>
      </div>
    </div>
  );
}
