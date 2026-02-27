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
import StatusPanel from "@/components/StatusPanel";
import WorkspaceDatabaseView from "@/components/WorkspaceDatabaseView";
import WorkspaceCapabilitiesView from "@/components/WorkspaceCapabilitiesView";
import WorkspaceProgressView from "@/components/WorkspaceProgressView";
import { Allotment } from "allotment";
import "allotment/dist/style.css";
import {
  ArrowLeft,
  Bot,
  Eye,
  EyeOff,
  ExternalLink,
  GitCommitHorizontal,
  ChevronDown,
  Layout,
  Database,
  Zap,
  Activity,
} from "lucide-react";
import clsx from "clsx";

const STATE_COLORS: Record<string, string> = {
  running: "bg-[#D4F79A] text-black",
  error: "bg-red-100 text-red-700",
  building: "bg-amber-100 text-amber-800",
  generating: "bg-sky-100 text-sky-800",
  scaffolded: "bg-purple-100 text-purple-800",
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
  const [mode, setMode] = useState<"overview" | "advanced">("overview");
  const [rightTab, setRightTab] = useState<"preview" | "status">("preview");
  const [overviewTab, setOverviewTab] = useState<
    "database" | "capabilities" | "progress"
  >("database");
  const [showOnboarding, setShowOnboarding] = useState(false);

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

  // Simple first-run onboarding stored in localStorage
  useEffect(() => {
    try {
      if (typeof window === "undefined") return;
      const seen = window.localStorage.getItem("mesora_onboarding_v1");
      if (!seen) {
        setShowOnboarding(true);
      }
    } catch {
      // ignore storage errors
    }
  }, []);

  const dismissOnboarding = () => {
    setShowOnboarding(false);
    try {
      window.localStorage.setItem("mesora_onboarding_v1", "1");
    } catch {
      // ignore
    }
  };

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
    <div className="min-h-screen bg-[#F4F4F4] py-4">
      <div className="max-w-[1600px] mx-auto h-[calc(100vh-2rem)] flex flex-col rounded-[32px] border border-border bg-white shadow-sm overflow-hidden">
        {/* Header */}
        <header className="px-4 sm:px-6 py-3 border-b border-border flex items-center gap-3 shrink-0">
          <button
            onClick={() => router.push("/builder")}
            className="p-1.5 text-text-secondary hover:text-text-primary rounded-full hover:bg-bg-secondary transition-colors"
            title="Back to projects"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-2xl bg-[#D4F79A] flex items-center justify-center">
              <Bot className="w-4 h-4 text-black" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">
                Mesora agent
              </p>
              <h1 className="text-sm font-semibold text-gray-900 truncate">
                {state.project?.name || state.project?.id || projectId}
              </h1>
            </div>
          </div>

          <span
            className={clsx(
              "ml-2 inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-full",
              colorClass
            )}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {projectState}
          </span>

          {state.swaggerUrl && (
            <a
              href={state.swaggerUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-3 hidden sm:inline-flex items-center gap-1 text-[11px] text-accent hover:opacity-80 px-2 py-1 rounded-full bg-bg-secondary"
            >
              <span>Swagger</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}

          {/* Git log dropdown */}
          {state.commits.length > 0 && (
            <div className="relative ml-auto">
              <button
                onClick={() => setGitDropdownOpen(!gitDropdownOpen)}
                className="flex items-center gap-1.5 text-[11px] text-text-secondary hover:text-text-primary px-2 py-1 rounded-full hover:bg-bg-secondary"
              >
                <GitCommitHorizontal className="w-3.5 h-3.5" />
                {state.commits.length} commit
                {state.commits.length !== 1 ? "s" : ""}
                <ChevronDown className="w-3 h-3" />
              </button>
              {gitDropdownOpen && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setGitDropdownOpen(false)}
                  />
                  <div className="absolute right-0 top-full mt-1 z-20 w-80 bg-bg-primary border border-border rounded-xl shadow-xl overflow-hidden">
                    <div className="max-h-64 overflow-y-auto p-2">
                      {state.commits.map((c) => (
                        <div
                          key={c.hash}
                          className="flex items-start gap-2 py-1.5 px-2 text-xs hover:bg-bg-secondary rounded"
                        >
                          <span className="font-mono text-yellow-400 shrink-0">
                            {c.hash}
                          </span>
                          <span className="text-text-secondary truncate">
                            {c.message}
                          </span>
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
                className="hidden sm:inline-flex items-center gap-1.5 text-[11px] text-text-secondary hover:text-text-primary transition-colors px-2 py-1 rounded-full hover:bg-bg-secondary"
                title="Toggle tool details (Ctrl+O)"
              >
                {state.showToolDetails ? (
                  <EyeOff className="w-3.5 h-3.5" />
                ) : (
                  <Eye className="w-3.5 h-3.5" />
                )}
                <kbd className="hidden md:inline text-[10px] bg-bg-secondary px-1 rounded border border-border">
                  Ctrl+O
                </kbd>
              </button>
            </div>
          )}

          <div className="ml-2">
            <ThemeToggle />
          </div>
        </header>

        {/* Mode switch */}
        <div className="px-4 sm:px-6 pt-3 flex items-center gap-2 border-b border-border bg-[#F4F4F4]">
          <button
            type="button"
            onClick={() => setMode("overview")}
            className={clsx(
              "text-xs font-medium px-3 py-1.5 rounded-full transition-colors",
              mode === "overview"
                ? "bg-black text-white"
                : "text-text-secondary hover:bg-bg-secondary"
            )}
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => setMode("advanced")}
            className={clsx(
              "text-xs font-medium px-3 py-1.5 rounded-full transition-colors",
              mode === "advanced"
                ? "bg-black text-white"
                : "text-text-secondary hover:bg-bg-secondary"
            )}
          >
            Advanced (files &amp; code)
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 min-h-0 bg-[#F4F4F4] px-2 pb-2 pt-2 sm:px-3 sm:pb-3 sm:pt-3">
          {mode === "advanced" ? (
            <Allotment proportionalLayout={false}>
              {/* Left: File Explorer */}
              <Allotment.Pane preferredSize={260} minSize={140} maxSize={420}>
                <div className="h-full flex flex-col bg-white rounded-[24px] border border-border overflow-hidden">
                  <div className="px-3 py-2 border-b border-border flex items-center justify-between bg-[#FAFAFA]">
                    <div className="flex items-center gap-2">
                      <Layout className="w-3.5 h-3.5 text-text-muted" />
                      <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-[0.16em]">
                        Files
                      </h2>
                    </div>
                    <span className="text-[10px] text-text-muted">
                      {state.files.length || 0} items
                    </span>
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
              <Allotment.Pane minSize={320}>
                <div className="h-full flex flex-col bg-[#F4F4F4] rounded-[24px] border border-border overflow-hidden">
                  <div className="px-4 py-3 border-b border-border bg-white/80 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-black text-white flex items-center justify-center">
                        <Bot className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-gray-900">
                          Conversation
                        </p>
                        <p className="text-[11px] text-gray-500">
                          Tell the agent what backend you need.
                        </p>
                      </div>
                    </div>
                    {state.isAgentWorking && (
                      <span className="inline-flex items-center gap-2 text-[11px] font-medium text-gray-600 bg-white px-3 py-1 rounded-full shadow-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#D4F79A] animate-pulse" />
                        Working
                      </span>
                    )}
                  </div>
                  <div className="flex-1 min-h-0 flex flex-col">
                    {showOnboarding && (
                      <div className="mx-4 mt-3 mb-1 rounded-2xl bg-white border border-border px-4 py-3 text-xs text-text-secondary">
                        <p className="font-medium text-text-primary mb-1.5">
                          New here? Here&apos;s how this workspace works:
                        </p>
                        <ol className="list-decimal list-inside space-y-1">
                          <li>
                            In the <span className="font-semibold">Conversation</span>{" "}
                            panel, describe in plain English what backend you want.
                          </li>
                          <li>
                            Watch the agent work, then explore generated files and docs in{" "}
                            <span className="font-semibold">Files</span> and{" "}
                            <span className="font-semibold">Status</span>.
                          </li>
                          <li>
                            When you&apos;re ready for deeper docs, open the{" "}
                            <a
                              href="https://github.com/NLP-titan/Prosit-2"
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline text-accent"
                            >
                              Prosit-2 repository
                            </a>{" "}
                            to see implementation details.
                          </li>
                        </ol>
                        <button
                          type="button"
                          onClick={dismissOnboarding}
                          className="mt-3 inline-flex items-center text-[11px] font-medium text-text-secondary hover:text-text-primary"
                        >
                          Got it, hide this
                        </button>
                      </div>
                    )}
                    <div className="flex-1 min-h-0">
                      <ChatPanel
                        messages={state.messages}
                        onSend={handleSend}
                        onStop={handleStop}
                        isAgentWorking={state.isAgentWorking}
                        showToolDetails={state.showToolDetails}
                        onAnswerAskUser={handleAnswerAskUser}
                      />
                    </div>
                  </div>
                </div>
              </Allotment.Pane>

              {/* Right: File Viewer / Status */}
              <Allotment.Pane preferredSize={420} minSize={220}>
                <div className="h-full flex flex-col bg-white rounded-[24px] border border-border overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-border bg-[#FAFAFA] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setRightTab("preview")}
                        className={clsx(
                          "text-xs font-medium px-3 py-1 rounded-full transition-colors",
                          rightTab === "preview"
                            ? "bg-black text-white"
                            : "text-text-secondary hover:bg-bg-secondary"
                        )}
                      >
                        Preview
                      </button>
                      <button
                        type="button"
                        onClick={() => setRightTab("status")}
                        className={clsx(
                          "text-xs font-medium px-3 py-1 rounded-full transition-colors",
                          rightTab === "status"
                            ? "bg-black text-white"
                            : "text-text-secondary hover:bg-bg-secondary"
                        )}
                      >
                        Status
                      </button>
                    </div>
                    {state.apiUrl && rightTab === "status" && (
                      <a
                        href={state.apiUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hidden sm:inline text-[11px] text-accent hover:opacity-80"
                      >
                        Open API
                      </a>
                    )}
                  </div>
                  <div className="flex-1 min-h-0">
                    {rightTab === "preview" ? (
                      <FileViewer
                        projectId={projectId}
                        filePath={state.selectedFile}
                        onClose={handleCloseFile}
                      />
                    ) : (
                      <StatusPanel
                        projectState={projectState}
                        files={state.files}
                        commits={state.commits}
                        swaggerUrl={state.swaggerUrl}
                        apiUrl={state.apiUrl}
                      />
                    )}
                  </div>
                </div>
              </Allotment.Pane>
            </Allotment>
          ) : (
            <Allotment proportionalLayout={false}>
              {/* Left: Chat (simplified) */}
              <Allotment.Pane preferredSize={420} minSize={260} maxSize={520}>
                <div className="h-full flex flex-col bg-[#F4F4F4] rounded-[24px] border border-border overflow-hidden">
                  <div className="px-4 py-3 border-b border-border bg-white/80 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-black text-white flex items-center justify-center">
                        <Bot className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-gray-900">
                          Mesora Agent
                        </p>
                        <p className="text-[11px] text-gray-500">
                          Describe in plain English the backend you need.
                        </p>
                      </div>
                    </div>
                    {state.isAgentWorking && (
                      <span className="inline-flex items-center gap-2 text-[11px] font-medium text-gray-600 bg-white px-3 py-1 rounded-full shadow-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#D4F79A] animate-pulse" />
                        Working
                      </span>
                    )}
                  </div>
                  <div className="flex-1 min-h-0">
                    <ChatPanel
                      messages={state.messages}
                      onSend={handleSend}
                      onStop={handleStop}
                      isAgentWorking={state.isAgentWorking}
                      showToolDetails={state.showToolDetails}
                      onAnswerAskUser={handleAnswerAskUser}
                    />
                  </div>
                </div>
              </Allotment.Pane>

              {/* Right: Database / Capabilities / Progress tabs */}
              <Allotment.Pane minSize={420}>
                <div className="h-full bg-white rounded-[24px] border border-border overflow-hidden flex flex-col">
                  <div className="px-4 py-3 border-b border-border bg-[#FAFAFA] flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <button
                        type="button"
                        onClick={() => setOverviewTab("database")}
                        className={clsx(
                          "text-xs font-medium pb-1 border-b-2 border-transparent flex items-center gap-1.5",
                          overviewTab === "database"
                            ? "border-black text-gray-900"
                            : "text-gray-400 hover:text-gray-600"
                        )}
                      >
                        <Database className="w-3.5 h-3.5" />
                        Database
                      </button>
                      <button
                        type="button"
                        onClick={() => setOverviewTab("capabilities")}
                        className={clsx(
                          "text-xs font-medium pb-1 border-b-2 border-transparent flex items-center gap-1.5",
                          overviewTab === "capabilities"
                            ? "border-black text-gray-900"
                            : "text-gray-400 hover:text-gray-600"
                        )}
                      >
                        <Zap className="w-3.5 h-3.5" />
                        Capabilities
                      </button>
                      <button
                        type="button"
                        onClick={() => setOverviewTab("progress")}
                        className={clsx(
                          "text-xs font-medium pb-1 border-b-2 border-transparent flex items-center gap-1.5",
                          overviewTab === "progress"
                            ? "border-black text-gray-900"
                            : "text-gray-400 hover:text-gray-600"
                        )}
                      >
                        <Activity className="w-3.5 h-3.5" />
                        Progress
                      </button>
                    </div>
                    <span className="text-[11px] px-3 py-1 rounded-full border border-border bg-white text-gray-600">
                      <span
                        className={clsx(
                          "inline-block w-1.5 h-1.5 rounded-full mr-1",
                          state.swaggerUrl ? "bg-green-500" : "bg-gray-300"
                        )}
                      />
                      {state.swaggerUrl ? "Live & Connected" : "Draft Mode"}
                    </span>
                  </div>
                  <div className="p-4 md:p-6 flex-1 overflow-y-auto text-sm text-text-secondary">
                    {overviewTab === "database" && (
                      <div>
                        <h2 className="text-lg font-semibold text-gray-900 mb-1">
                          Your Data Structure
                        </h2>
                        <p className="text-xs text-gray-500 mb-4">
                          This is how your application&apos;s information is
                          organized securely in the cloud.
                        </p>
                        <WorkspaceDatabaseView
                          projectId={projectId}
                          swaggerUrl={state.swaggerUrl}
                        />
                      </div>
                    )}
                    {overviewTab === "capabilities" && (
                      <div>
                        <h2 className="text-lg font-semibold text-gray-900 mb-1">
                          App Capabilities
                        </h2>
                        <p className="text-xs text-gray-500 mb-4">
                          These are the actions your frontend can ask this
                          backend to perform.
                        </p>
                        <WorkspaceCapabilitiesView
                          projectId={projectId}
                          swaggerUrl={state.swaggerUrl}
                        />
                      </div>
                    )}
                    {overviewTab === "progress" && (
                      <WorkspaceProgressView projectState={projectState} />
                    )}
                  </div>
                </div>
              </Allotment.Pane>
            </Allotment>
          )}
        </div>
      </div>
    </div>
  );
}
