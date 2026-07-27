import type { TreeNode } from "../types";

export interface HealthStatus {
  status: string;
  version: string;
}

export interface GraceState {
  completed_waves: string[];
  escalation: { reason: string; details: string } | null;
  github_mode?: boolean;
  pr_url?: string;
  pr_number?: number;
  merged?: boolean;
}

export interface ArtifactFile {
  name: string;
  path: string;
  size: number;
}

export interface ArtifactList {
  path: string;
  files: ArtifactFile[];
}

export interface CreateArtifactResponse {
  success: boolean;
  path: string;
}

export interface RunOptions {
  plan?: string;
  worker?: string;
  state?: string;
  openai_api_key?: string;
  github_token?: string;
  llm_model?: string;
  llm_api_url?: string;
  workspace?: string;
}

const BASE_URL = (import.meta as any).env?.VITE_API_URL || "";

async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function requestText(path: string): Promise<string> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.text();
}

export async function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/api/health");
}

export async function getState(): Promise<GraceState> {
  return request<GraceState>("/api/state");
}

export async function getArtifacts(): Promise<ArtifactList> {
  return request<ArtifactList>("/api/artifacts");
}

export async function createArtifact(path: string): Promise<CreateArtifactResponse> {
  const res = await fetch(`${BASE_URL}/api/artifacts/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getArtifactContent(path: string): Promise<string> {
  return requestText(`/api/artifacts/file?path=${encodeURIComponent(path)}`);
}

export async function saveArtifact(path: string, content: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/artifacts/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
}

export async function getEvidenceTree(): Promise<TreeNode> {
  return request<TreeNode>("/api/evidence");
}

export async function getEvidenceFile(path: string): Promise<string> {
  return requestText(`/api/evidence/file?path=${encodeURIComponent(path)}`);
}

export async function resetState(): Promise<void> {
  await fetch(`${BASE_URL}/api/state`, { method: "DELETE" });
}

export async function runOrchestrator(options: RunOptions = {}): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export function parseLogs(
  text: string,
): (import("../types").LogEntry | { error: string; raw: string })[] {
  return text
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => {
      try {
        const parsed = JSON.parse(line);
        if (parsed.module !== undefined && parsed.event !== undefined) {
          return parsed as import("../types").LogEntry;
        }
        return { error: "Not a valid log envelope", raw: line };
      } catch {
        return { error: "Not valid JSON", raw: line };
      }
    });
}

