import type { Project, FileNode, DockerStatus } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// Projects
export async function createProject(
  name: string,
  description: string = ""
): Promise<Project> {
  return fetchAPI("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });
}

export async function listProjects(): Promise<Project[]> {
  return fetchAPI("/api/v1/projects");
}

export async function getProject(id: string): Promise<Project> {
  return fetchAPI(`/api/v1/projects/${id}`);
}

export async function deleteProject(id: string): Promise<void> {
  await fetchAPI(`/api/v1/projects/${id}`, { method: "DELETE" });
}

// Chat
export async function sendMessage(
  projectId: string,
  message: string
): Promise<{ status: string }> {
  return fetchAPI(`/api/v1/chat/${projectId}/send`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export async function getChatHistory(
  projectId: string
): Promise<
  {
    id: string;
    role: string;
    content: string | null;
    tool_calls: any[] | null;
    tool_call_id: string | null;
    tool_name: string | null;
    created_at: string;
  }[]
> {
  return fetchAPI(`/api/v1/chat/${projectId}/history`);
}

export function getStreamUrl(projectId: string): string {
  return `${API_BASE}/api/v1/chat/${projectId}/stream`;
}

// Files
export async function getFileTree(projectId: string): Promise<FileNode> {
  return fetchAPI(`/api/v1/files/${projectId}/tree`);
}

export async function getFileContent(
  projectId: string,
  path: string
): Promise<{ path: string; content: string }> {
  return fetchAPI(
    `/api/v1/files/${projectId}/content?path=${encodeURIComponent(path)}`
  );
}

// Docker
export async function startDocker(projectId: string): Promise<any> {
  return fetchAPI(`/api/v1/docker/${projectId}/start`, { method: "POST" });
}

export async function stopDocker(projectId: string): Promise<any> {
  return fetchAPI(`/api/v1/docker/${projectId}/stop`, { method: "POST" });
}

export async function getDockerStatus(
  projectId: string
): Promise<DockerStatus> {
  return fetchAPI(`/api/v1/docker/${projectId}/status`);
}

export async function getDockerLogs(
  projectId: string
): Promise<{ logs: string }> {
  return fetchAPI(`/api/v1/docker/${projectId}/logs`);
}
