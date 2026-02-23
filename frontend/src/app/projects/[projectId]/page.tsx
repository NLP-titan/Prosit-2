"use client";

import { useReducer, useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { appReducer, initialState } from "@/lib/reducer";
import { useWebSocket } from "@/lib/websocket";
import { getProject, getFileTree } from "@/lib/api";
import ChatPanel from "@/components/ChatPanel";
import FileExplorer from "@/components/FileExplorer";
import FileViewer from "@/components/FileViewer";
import ThemeToggle from "@/components/ThemeToggle";
import { Allotment } from "allotment";
import "allotment/dist/style.css";
import {
  ArrowLeft,
  Hammer,
  Eye,
  EyeOff,
  ExternalLink,
  GitCommitHorizontal,
  ChevronDown,
} from "lucide-react";
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

export default function WorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [state, dispatch] = useReducer(appReducer, initialState);
  const [loading, setLoading] = useState(true);
  const [gitDropdownOpen, setGitDropdownOpen] = useState(false);

  // Load project on mount
  useEffect(() => {
    async function load() {
      try {
        const project = await getProject(projectId);
        dispatch({ type: "SET_PROJECT", project });
        // Load file tree
        const files = await getFileTree(projectId);
        dispatch({ type: "SET_FILES", files });
      } catch (e) {
        console.error("Failed to load project:", e);
      }
      setLoading(false);
    }
    load();
  }, [projectId]);

  // Ctrl+O to toggle tool details
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.ctrlKey && e.key === "o") {
        e.preventDefault();
        dispatch({ type: "TOGGLE_TOOL_DETAILS" });
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const { sendMessage, stopAgent } = useWebSocket(
    loading ? null : projectId,
    dispatch
  );

  const handleSend = useCallback(
    (message: string) => {
      dispatch({ type: "ADD_USER_MESSAGE", content: message });
      sendMessage(message);
    },
    [sendMessage]
  );

  const handleStop = useCallback(() => {
    stopAgent();
    dispatch({ type: "AGENT_STOPPED" });
  }, [stopAgent]);

  const handleAnswerAskUser = useCallback(
    (messageId: string, answer: string) => {
      dispatch({ type: "MARK_ANSWERED", messageId });
      dispatch({ type: "ADD_USER_MESSAGE", content: answer });
      sendMessage(answer);
    },
    [sendMessage]
  );

  const handleFileSelect = useCallback((path: string) => {
    dispatch({ type: "SELECT_FILE", path });
  }, []);

  const handleCloseFile = useCallback(() => {
    dispatch({ type: "SELECT_FILE", path: null });
  }, []);

  // Dispatch a custom event when files change so FileViewer can refresh
  useEffect(() => {
    if (state.files.length > 0) {
      window.dispatchEvent(new Event("backendforge:file-changed"));
    }
  }, [state.files]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-text-secondary animate-pulse">Loading project...</div>
      </div>
    );
  }

  const projectState = state.project?.state || "created";
  const colorClass = STATE_COLORS[projectState] || STATE_COLORS.created;

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border px-4 py-2.5 flex items-center gap-3 shrink-0">
        <button
          onClick={() => router.push("/")}
          className="p-1 text-text-secondary hover:text-text-primary rounded hover:bg-bg-secondary transition-colors"
          title="Back to projects"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>

        <Hammer className="w-4 h-4 text-accent" />
        <h1 className="font-semibold text-sm truncate">
          {state.project?.name || state.project?.id || projectId}
        </h1>

        <span className={clsx("text-[10px] px-1.5 py-0.5 rounded", colorClass)}>
          {projectState}
        </span>

        {state.swaggerUrl && (
          <a
            href={state.swaggerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-accent hover:opacity-80"
          >
            Swagger <ExternalLink className="w-3 h-3" />
          </a>
        )}

        {/* Git log dropdown */}
        {state.commits.length > 0 && (
          <div className="relative ml-auto">
            <button
              onClick={() => setGitDropdownOpen(!gitDropdownOpen)}
              className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary px-2 py-1 rounded hover:bg-bg-secondary"
            >
              <GitCommitHorizontal className="w-3.5 h-3.5" />
              {state.commits.length} commit{state.commits.length !== 1 ? "s" : ""}
              <ChevronDown className="w-3 h-3" />
            </button>
            {gitDropdownOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setGitDropdownOpen(false)} />
                <div className="absolute right-0 top-full mt-1 z-20 w-80 bg-bg-primary border border-border rounded-lg shadow-xl overflow-hidden">
                  <div className="max-h-64 overflow-y-auto p-2">
                    {state.commits.map((c) => (
                      <div key={c.hash} className="flex items-start gap-2 py-1.5 px-2 text-xs hover:bg-bg-secondary rounded">
                        <span className="font-mono text-yellow-400 shrink-0">{c.hash}</span>
                        <span className="text-text-secondary truncate">{c.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {!state.commits.length && (
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => dispatch({ type: "TOGGLE_TOOL_DETAILS" })}
              className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors px-2 py-1 rounded hover:bg-bg-secondary"
              title="Toggle tool details (Ctrl+O)"
            >
              {state.showToolDetails ? (
                <EyeOff className="w-3.5 h-3.5" />
              ) : (
                <Eye className="w-3.5 h-3.5" />
              )}
              <kbd className="hidden sm:inline text-[10px] bg-bg-secondary px-1 rounded border border-border">
                Ctrl+O
              </kbd>
            </button>
          </div>
        )}

        <ThemeToggle />
      </header>

      {/* 3-panel layout */}
      <div className="flex-1 min-h-0">
        <Allotment proportionalLayout={false}>
          {/* Left: File Explorer */}
          <Allotment.Pane preferredSize={250} minSize={120} maxSize={450}>
            <div className="h-full flex flex-col border-r border-border">
              <div className="border-b border-border px-3 py-2">
                <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Files</h2>
              </div>
              <div className="flex-1 overflow-y-auto">
                <FileExplorer
                  files={state.files}
                  selectedFile={state.selectedFile}
                  onFileSelect={handleFileSelect}
                />
              </div>
            </div>
          </Allotment.Pane>

          {/* Center: Chat */}
          <Allotment.Pane minSize={300}>
            <ChatPanel
              messages={state.messages}
              onSend={handleSend}
              onStop={handleStop}
              isAgentWorking={state.isAgentWorking}
              showToolDetails={state.showToolDetails}
              onAnswerAskUser={handleAnswerAskUser}
            />
          </Allotment.Pane>

          {/* Right: File Viewer */}
          <Allotment.Pane preferredSize={450} minSize={200}>
            <div className="h-full border-l border-border">
              <FileViewer
                projectId={projectId}
                filePath={state.selectedFile}
                onClose={handleCloseFile}
              />
            </div>
          </Allotment.Pane>
        </Allotment>
      </div>
    </div>
  );
}
