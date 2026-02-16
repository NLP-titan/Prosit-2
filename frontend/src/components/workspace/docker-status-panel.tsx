"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Play,
  Square,
  ExternalLink,
  Loader2,
  CircleDot,
} from "lucide-react";
import {
  startDocker,
  stopDocker,
  getDockerStatus,
} from "@/lib/api-client";
import type { DockerStatus } from "@/lib/types";

interface DockerStatusPanelProps {
  projectId: string;
  onStatusChange?: (status: DockerStatus) => void;
}

export function DockerStatusPanel({
  projectId,
  onStatusChange,
}: DockerStatusPanelProps) {
  const [status, setStatus] = useState<DockerStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState<"start" | "stop" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await getDockerStatus(projectId);
      setStatus(s);
      onStatusChange?.(s);
    } catch {
      // Docker might not be set up yet
    }
  }, [projectId, onStatusChange]);

  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, 10000);
    return () => clearInterval(interval);
  }, [refreshStatus]);

  const handleStart = async () => {
    setAction("start");
    setLoading(true);
    setError(null);
    try {
      const result = await startDocker(projectId);
      if (result?.status === "error") {
        setError(result.message || "Failed to start containers");
      }
      await refreshStatus();
      setTimeout(refreshStatus, 3000);
      setTimeout(refreshStatus, 8000);
      setTimeout(refreshStatus, 15000);
    } catch (err: any) {
      setError(err?.message || "Failed to start containers");
      console.error("Failed to start:", err);
    } finally {
      setLoading(false);
      setAction(null);
    }
  };

  const handleStop = async () => {
    setAction("stop");
    setLoading(true);
    setError(null);
    try {
      await stopDocker(projectId);
      await refreshStatus();
    } catch (err: any) {
      setError(err?.message || "Failed to stop containers");
      console.error("Failed to stop:", err);
    } finally {
      setLoading(false);
      setAction(null);
    }
  };

  const isRunning = status?.services?.some((s) => s.state === "running");
  // Find port from api service, or any service with a published port
  const apiPort =
    status?.services?.find((s) => s.name.includes("api"))?.port ||
    status?.services?.find((s) => s.port)?.port;

  // Debug: log status on every update
  useEffect(() => {
    if (status) {
      console.log("[DockerStatus]", JSON.stringify(status));
    }
  }, [status]);

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-t bg-muted/30 text-sm">
      <span className="text-muted-foreground font-medium">Docker:</span>

      {error && (
        <span className="text-xs text-red-500 truncate max-w-[300px]" title={error}>
          {error}
        </span>
      )}

      {!error && (status?.services?.map((svc) => (
        <div key={svc.name} className="flex items-center gap-1">
          <CircleDot
            className={`h-3 w-3 ${
              svc.state === "running" ? "text-green-500" : "text-gray-400"
            }`}
          />
          <span className="text-xs">{svc.name}</span>
          {svc.port && (
            <span className="text-xs text-muted-foreground">:{svc.port}</span>
          )}
        </div>
      )) || (
        <span className="text-xs text-muted-foreground">Not started</span>
      ))}

      <div className="flex-1" />

      {isRunning && apiPort && (
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() =>
            window.open(`http://localhost:${apiPort}/docs`, "_blank")
          }
        >
          <ExternalLink className="h-3 w-3 mr-1" />
          Swagger UI
        </Button>
      )}

      {isRunning ? (
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={handleStop}
          disabled={loading}
        >
          {loading && action === "stop" ? (
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          ) : (
            <Square className="h-3 w-3 mr-1" />
          )}
          Stop
        </Button>
      ) : (
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={handleStart}
          disabled={loading}
        >
          {loading && action === "start" ? (
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          ) : (
            <Play className="h-3 w-3 mr-1" />
          )}
          Start
        </Button>
      )}
    </div>
  );
}
