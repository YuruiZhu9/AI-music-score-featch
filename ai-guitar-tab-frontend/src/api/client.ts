/**
 * API 客户端 — 与 FastAPI 后端通信
 */
import axios, { AxiosInstance, AxiosError } from "axios";

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

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail: string }>) => {
    const message = error.response?.data?.detail || error.message || "未知错误";
    console.error("[API Error]", message);
    return Promise.reject(new Error(message));
  }
);

export async function uploadAudio(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<UploadResponse>("/api/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await apiClient.get<TaskStatus>(`/api/task/${taskId}`);
  return response.data;
}

export async function getAnalysisResult(taskId: string): Promise<{ task_id: string; result: AnalysisResult }> {
  const response = await apiClient.get<{ task_id: string; result: AnalysisResult }>(`/api/result/${taskId}`);
  return response.data;
}

export async function getHealth(): Promise<{ status: string }> {
  const response = await apiClient.get<{ status: string }>("/health");
  return response.data;
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

export { apiClient };
