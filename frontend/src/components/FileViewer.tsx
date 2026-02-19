"use client";

import { useState, useEffect } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark, oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { X, FileCode } from "lucide-react";
import { getFileContent } from "@/lib/api";
import { useTheme } from "./ThemeProvider";

const EXT_LANGUAGE: Record<string, string> = {
  py: "python",
  ts: "typescript",
  tsx: "tsx",
  js: "javascript",
  jsx: "jsx",
  json: "json",
  yml: "yaml",
  yaml: "yaml",
  md: "markdown",
  sql: "sql",
  toml: "toml",
  ini: "ini",
  cfg: "ini",
  txt: "text",
  sh: "bash",
  bash: "bash",
  dockerfile: "docker",
  env: "bash",
};

function getLanguage(path: string): string {
  const name = path.split("/").pop()?.toLowerCase() || "";
  if (name === "dockerfile") return "docker";
  if (name === ".env" || name === ".env.example") return "bash";
  const ext = name.split(".").pop() || "";
  return EXT_LANGUAGE[ext] || "text";
}

interface Props {
  projectId: string;
  filePath: string | null;
  onClose: () => void;
}

export default function FileViewer({ projectId, filePath, onClose }: Props) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [version, setVersion] = useState(0);
  const { theme } = useTheme();

  // Exposed for parent to trigger refresh
  useEffect(() => {
    if (!filePath) {
      setContent(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    getFileContent(projectId, filePath)
      .then((text) => {
        if (!cancelled) setContent(text);
      })
      .catch(() => {
        if (!cancelled) setContent("// Failed to load file");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, filePath, version]);

  // Re-fetch when file is updated by agent
  useEffect(() => {
    // Listen for custom event dispatched when files change
    const handler = () => setVersion((v) => v + 1);
    window.addEventListener("backendforge:file-changed", handler);
    return () => window.removeEventListener("backendforge:file-changed", handler);
  }, []);

  if (!filePath) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        <div className="text-center">
          <FileCode className="w-8 h-8 mx-auto mb-2 text-text-muted" />
          <p>Select a file to view</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border px-3 py-2 flex items-center justify-between shrink-0">
        <span className="text-xs font-mono text-text-secondary truncate">{filePath}</span>
        <button
          onClick={onClose}
          className="p-1 text-text-muted hover:text-text-primary rounded hover:bg-bg-secondary shrink-0"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="text-text-muted text-xs p-4 animate-pulse">Loading...</div>
        ) : (
          <SyntaxHighlighter
            language={getLanguage(filePath)}
            style={theme === "dark" ? oneDark : oneLight}
            customStyle={{
              margin: 0,
              padding: "12px",
              fontSize: "11px",
              lineHeight: "1.5",
              background: "transparent",
              minHeight: "100%",
            }}
            showLineNumbers
            lineNumberStyle={{
              color: theme === "dark" ? "#52525b" : "#a1a1aa",
              fontSize: "10px",
              minWidth: "2.5em",
            }}
          >
            {content || ""}
          </SyntaxHighlighter>
        )}
      </div>
    </div>
  );
}
