/**
 * API 客户端 — 与 FastAPI 后端通信
 * 使用原生 fetch 实现，无额外依赖
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface UploadResponse {
  task_id: string;
  status: "pending" | "processing" | "done" | "error";
  message: string;
  poll_url: string;
}

export interface TaskStatus {
  task_id: string;
  status: "pending" | "processing" | "done" | "error";
  progress: number;
  stage: string;
  error?: string;
}

export interface ChordEvent {
  start: number;
  end: number;
  chord: string;
}

export interface NoteEvent {
  time: number;
  frequency?: number;
  note: string;
  string?: number;
  fret?: number;
  duration?: string;
  confidence?: number;
}

export interface AnalysisResult {
  task_id: string;
  bpm: number;
  time_signature: string;
  duration_sec: number;
  chords: ChordEvent[];
  notes: NoteEvent[];
  pitch?: {
    notes: NoteEvent[];
    total_notes: number;
    duration_sec: number;
  };
  score_files?: {
    gta?: string;
    pdf?: string;
    json?: string;
  };
  gta_text?: string;
}

// ─── 底层 fetch 封装 ────────────────────────────────────────────

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

// ─── API 客户端 ─────────────────────────────────────────────────

export const apiClient = {
  async uploadAudio(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `上传失败 HTTP ${response.status}`);
    }
    return response.json();
  },

  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    return apiFetch<TaskStatus>(`/api/task/${taskId}`);
  },

  async getAnalysisResult(taskId: string): Promise<{ task_id: string; result: AnalysisResult }> {
    return apiFetch<{ task_id: string; result: AnalysisResult }>(`/api/result/${taskId}`);
  },

  async getHealth(): Promise<{ status: string }> {
    return apiFetch<{ status: string }>("/health");
  },

  async analyzeUrl(url: string): Promise<UrlAnalyzeResponse> {
    const formData = new FormData();
    formData.append("url", url);
    const response = await fetch(`${API_BASE_URL}/api/analyze-url`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `请求失败 HTTP ${response.status}`);
    }
    return response.json();
  },
};

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  return apiClient.getTaskStatus(taskId);
}

export async function getAnalysisResult(taskId: string): Promise<{ task_id: string; result: AnalysisResult }> {
  return apiClient.getAnalysisResult(taskId);
}

export async function getHealth(): Promise<{ status: string }> {
  return apiClient.getHealth();
}

export async function uploadAudio(file: File): Promise<UploadResponse> {
  return apiClient.uploadAudio(file);
}

export async function pollTaskUntilDone(
  taskId: string,
  onProgress: (status: TaskStatus) => void,
  options: { maxAttempts?: number; intervalMs?: number } = {}
): Promise<TaskStatus> {
  const { maxAttempts = 150, intervalMs = 2000 } = options;
  for (let i = 0; i < maxAttempts; i++) {
    const status = await getTaskStatus(taskId);
    onProgress(status);
    if (status.status === "done") return status;
    if (status.status === "error") throw new Error(status.error || "处理失败");
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("处理超时，请稍后重试");
}

export async function waitForResult(
  taskId: string,
  onProgress: (status: TaskStatus) => void
): Promise<AnalysisResult> {
  await pollTaskUntilDone(taskId, onProgress);
  const { result } = await getAnalysisResult(taskId);
  return result;
}

// ─── 视频 URL 分析 ─────────────────────────────────────────────

export interface UrlAnalyzeResponse {
  task_id: string;
  status: "pending" | "processing" | "done" | "error";
  message: string;
  metadata?: {
    title: string;
    duration: number;
    uploader: string;
    thumbnail?: string;
  };
  poll_url: string;
}

export async function analyzeUrl(url: string): Promise<UrlAnalyzeResponse> {
  return apiClient.analyzeUrl(url);
}
