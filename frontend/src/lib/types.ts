// WebSocket message types (server → client)
export type WSMessageType =
  | "agent_message_start"
  | "agent_message_delta"
  | "agent_message_end"
  | "tool_call_start"
  | "tool_call_result"
  | "file_tree_update"
  | "git_update"
  | "build_complete"
  | "waiting_for_user"
  | "stopped"
  | "state_update"
  | "ask_user"
  | "error";

export interface WSMessage {
  type: WSMessageType;
  // agent_message_delta
  token?: string;
  // tool_call_start / tool_call_result
  tool?: string;
  arguments?: Record<string, unknown>;
  result?: string;
  // file_tree_update
  files?: string[];
  // git_update
  commits?: GitCommit[];
  // build_complete / state_update
  swagger_url?: string;
  api_url?: string;
  // state_update
  state?: string;
  // error / stopped
  message?: string;
  // ask_user
  question?: string;
  options?: string[];
}

export interface ToolStep {
  tool: string;
  status: "running" | "done";
  result?: string;
  args?: Record<string, unknown>;
}

export interface ToolGroup {
  id: string;
  steps: ToolStep[];
  isActive: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "tool_group" | "build_summary" | "ask_user";
  content: string;
  toolGroup?: ToolGroup;
  isStreaming?: boolean;
  swaggerUrl?: string;
  apiUrl?: string;
  // ask_user
  options?: string[];
  answered?: boolean;
}

export interface GitCommit {
  hash: string;
  message: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  state: string;
  app_port: number;
  db_port: number;
  created_at: string;
  swagger_url: string;
  api_url: string;
}

export interface AppState {
  project: Project | null;
  messages: ChatMessage[];
  files: string[];
  commits: GitCommit[];
  isAgentWorking: boolean;
  swaggerUrl: string | null;
  apiUrl: string | null;
  showToolDetails: boolean;
  selectedFile: string | null;
}
