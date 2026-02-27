import { Project } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface DatabasePreviewField {
  name: string;
  typeLabel: string;
}

export interface DatabasePreviewModel {
  name: string;
  description: string;
  fields: DatabasePreviewField[];
}

export interface DatabasePreviewResponse {
  models: DatabasePreviewModel[];
}

export interface CapabilitiesPreviewGroup {
  name: string;
  items: string[];
}

export interface CapabilitiesPreviewResponse {
  groups: CapabilitiesPreviewGroup[];
}

export async function createProject(name: string, description: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
}

export async function listProjects(): Promise<Project[]> {
  const res = await fetch(`${API_BASE}/projects`);
  if (!res.ok) throw new Error("Failed to list projects");
  return res.json();
}

export async function getProject(id: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects/${id}`);
  if (!res.ok) throw new Error("Failed to get project");
  return res.json();
}

export async function deleteProject(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete project");
}

export async function getFileTree(projectId: string): Promise<string[]> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/files`);
  if (!res.ok) throw new Error("Failed to get file tree");
  return res.json();
}

export async function getFileContent(projectId: string, path: string): Promise<string> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/files/content?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error("Failed to get file content");
  return res.text();
}

export async function getChatHistory(projectId: string): Promise<Array<{ role: string; content: string }>> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/chat/history`);
  if (!res.ok) throw new Error("Failed to get chat history");
  return res.json();
}

export async function getDatabasePreview(projectId: string): Promise<DatabasePreviewResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/preview/database`);
  if (!res.ok) {
    throw new Error("Failed to get database preview");
  }
  return res.json();
}

export async function getCapabilitiesPreview(projectId: string): Promise<CapabilitiesPreviewResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/preview/capabilities`);
  if (!res.ok) {
    throw new Error("Failed to get capabilities preview");
  }
  return res.json();
}

export async function stopProject(projectId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/stop`, { method: "POST" });
  if (!res.ok) {
    throw new Error("Failed to stop project");
  }
}

export function getWsUrl(projectId: string): string {
  const wsBase = (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000");
  return `${wsBase}/ws/chat/${projectId}`;
}
