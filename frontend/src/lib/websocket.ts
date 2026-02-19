"use client";

import { useEffect, useRef, useCallback } from "react";
import { WSMessage } from "./types";
import { AppAction } from "./reducer";
import { getWsUrl } from "./api";

export function useWebSocket(
  projectId: string | null,
  dispatch: React.Dispatch<AppAction>
) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!projectId) return;

    const ws = new WebSocket(getWsUrl(projectId));
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      switch (msg.type) {
        case "agent_message_start":
          dispatch({ type: "START_ASSISTANT_MESSAGE" });
          break;
        case "agent_message_delta":
          if (msg.token) dispatch({ type: "APPEND_ASSISTANT_TOKEN", token: msg.token });
          break;
        case "agent_message_end":
          dispatch({ type: "END_ASSISTANT_MESSAGE" });
          break;
        case "tool_call_start":
          dispatch({
            type: "ADD_TOOL_CALL",
            tool: msg.tool || "unknown",
            args: msg.arguments || {},
          });
          break;
        case "tool_call_result":
          dispatch({
            type: "ADD_TOOL_RESULT",
            tool: msg.tool || "unknown",
            result: msg.result || "",
          });
          break;
        case "file_tree_update":
          if (msg.files) dispatch({ type: "SET_FILES", files: msg.files });
          break;
        case "git_update":
          if (msg.commits) dispatch({ type: "SET_COMMITS", commits: msg.commits });
          break;
        case "waiting_for_user":
          dispatch({ type: "SET_AGENT_WORKING", working: false });
          break;
        case "stopped":
          dispatch({ type: "AGENT_STOPPED" });
          break;
        case "state_update":
          dispatch({
            type: "STATE_UPDATE",
            state: msg.state || "",
            swaggerUrl: msg.swagger_url || "",
            apiUrl: msg.api_url || "",
          });
          break;
        case "build_complete":
          dispatch({
            type: "BUILD_COMPLETE",
            swaggerUrl: msg.swagger_url || "",
            apiUrl: msg.api_url || "",
          });
          break;
        case "ask_user":
          dispatch({
            type: "ASK_USER",
            question: msg.question || "",
            options: msg.options || [],
          });
          break;
        case "error":
          dispatch({ type: "ADD_ERROR", message: msg.message || "Unknown error" });
          break;
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [projectId, dispatch]);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message }));
    }
  }, []);

  const stopAgent = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "stop" }));
    }
  }, []);

  return { sendMessage, stopAgent };
}
