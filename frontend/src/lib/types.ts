export interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
  docker_port: number | null;
  created_at: string;
  updated_at: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: string;
  result?: string;
  is_error?: boolean;
  status: "running" | "done";
}

export interface AskUserOption {
  label: string;
  description?: string;
  multi_select?: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string | null;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
  timestamp: Date;
  askUser?: {
    question: string;
    toolCallId: string;
    options?: AskUserOption[];
    answered?: boolean;
  };
}

export interface FileNode {
  name: string;
  type: "file" | "directory";
  path?: string;
  size?: number;
  children?: FileNode[];
}

export interface DockerStatus {
  status: string;
  services: {
    name: string;
    state: string;
    status: string;
    port: number | null;
  }[];
}
