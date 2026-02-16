"use client";

import { useEffect } from "react";
import { useChat } from "@/hooks/use-chat";
import { useProject } from "@/hooks/use-project";
import { useFileTree } from "@/hooks/use-file-tree";
import { ChatContainer } from "@/components/chat/chat-container";
import { FileExplorer } from "./file-explorer";
import { FileViewer } from "./file-viewer";
import { DockerStatusPanel } from "./docker-status-panel";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";

interface WorkspaceLayoutProps {
  projectId: string;
}

export function WorkspaceLayout({ projectId }: WorkspaceLayoutProps) {
  const { project, loading: projectLoading } = useProject(projectId);
  const {
    messages,
    setMessages,
    isLoading,
    isAgentWorking,
    sendMessage,
    loadHistory,
  } = useChat(projectId);
  const {
    tree,
    selectedFile,
    refresh: refreshTree,
    openFile,
    setSelectedFile,
  } = useFileTree(projectId);

  useEffect(() => {
    loadHistory();
    refreshTree();
  }, [loadHistory, refreshTree]);

  // Refresh file tree when agent finishes
  useEffect(() => {
    if (!isAgentWorking && messages.length > 0) {
      refreshTree();
    }
  }, [isAgentWorking, messages.length, refreshTree]);

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Loading project...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Project not found</p>
          <Link href="/">
            <Button variant="outline">Go back</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-2 border-b bg-background shrink-0">
        <Link href="/">
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <h1 className="font-semibold">{project.name}</h1>
        <Badge variant="outline">{project.status}</Badge>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={refreshTree}
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </header>

      {/* Main workspace — resizable panels */}
      <div className="flex-1 min-h-0">
        <ResizablePanelGroup
          orientation="horizontal"
          className="h-full"
        >
          {/* File explorer — left panel */}
          <ResizablePanel
            defaultSize={20}
            minSize={10}
          >
            <div className="flex flex-col h-full overflow-hidden">
              <div className="px-3 py-2 border-b shrink-0">
                <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Files
                </h2>
              </div>
              <div className="flex-1 min-h-0 overflow-auto">
                <FileExplorer
                  tree={tree}
                  onFileSelect={openFile}
                  selectedPath={selectedFile?.path}
                />
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Chat — center panel */}
          <ResizablePanel defaultSize={45} minSize={20}>
            <ChatContainer
              messages={messages}
              setMessages={setMessages}
              onSend={sendMessage}
              isLoading={isLoading}
              isAgentWorking={isAgentWorking}
            />
          </ResizablePanel>

          {/* File viewer — right panel (always rendered for stable resizing) */}
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={35} minSize={15}>
            {selectedFile ? (
              <FileViewer
                path={selectedFile.path}
                content={selectedFile.content}
                onClose={() => setSelectedFile(null)}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                <p>Select a file to preview</p>
              </div>
            )}</ResizablePanel>
        </ResizablePanelGroup>
      </div>

      {/* Docker status bar */}
      <div className="shrink-0">
        <DockerStatusPanel projectId={projectId} />
      </div>
    </div>
  );
}
