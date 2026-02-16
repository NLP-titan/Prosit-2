export interface SSEHandlers {
  onMessageStart: () => void;
  onTextDelta: (content: string) => void;
  onToolStart: (data: {
    id: string;
    name: string;
    arguments: string;
  }) => void;
  onToolResult: (data: {
    id: string;
    name: string;
    result: string;
    is_error: boolean;
  }) => void;
  onAskUser: (data: {
    question: string;
    tool_call_id: string;
    options?: { label: string; description?: string; multi_select?: boolean }[];
  }) => void;
  onMessageEnd: () => void;
  onError: (message: string) => void;
}

export function connectSSE(
  url: string,
  handlers: SSEHandlers
): { close: () => void } {
  const eventSource = new EventSource(url);

  eventSource.addEventListener("message_start", () => {
    handlers.onMessageStart();
  });

  eventSource.addEventListener("text_delta", (e) => {
    const data = JSON.parse(e.data);
    handlers.onTextDelta(data.content);
  });

  eventSource.addEventListener("tool_start", (e) => {
    const data = JSON.parse(e.data);
    handlers.onToolStart(data);
  });

  eventSource.addEventListener("tool_result", (e) => {
    const data = JSON.parse(e.data);
    handlers.onToolResult(data);
  });

  eventSource.addEventListener("ask_user", (e) => {
    const data = JSON.parse(e.data);
    handlers.onAskUser(data);
  });

  eventSource.addEventListener("message_end", () => {
    handlers.onMessageEnd();
    eventSource.close();
  });

  eventSource.addEventListener("error", (e) => {
    if (e instanceof MessageEvent) {
      const data = JSON.parse(e.data);
      handlers.onError(data.message);
    }
    eventSource.close();
  });

  eventSource.onerror = () => {
    // EventSource auto-reconnects on error, but we close it
    // since our streams are one-shot
    eventSource.close();
  };

  return { close: () => eventSource.close() };
}
