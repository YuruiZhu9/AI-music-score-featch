/**
 * API 客户端 — 对接后端 FastAPI
 * ================================
 * 封装所有与后端交互的 HTTP 请求。
 */

import axios, { AxiosInstance } from 'axios';

// ---------------------------------------------------------------------------
// 类型定义
// ---------------------------------------------------------------------------

/** 任务状态 */
export type TaskStatus = 'pending' | 'processing' | 'done' | 'error';

/** 单个和弦 */
export interface Chord {
  start: number;
  end: number;
  chord: string;
}

/** 音符段落 */
export interface NoteSegment {
  start: number;
  end: number;
  pitch: number; // MIDI pitch
  duration: number;
  string?: number; // 吉他弦号（1-6）
  fret?: number; // 品丝号
}

/** 分析结果 */
export interface AnalysisResult {
  bpm: number;
  time_signature: string;
  chords: Chord[];
  segments: NoteSegment[];
}

/** 任务详情 */
export interface TaskRecord {
  task_id: string;
  status: TaskStatus;
  progress: number;
  stage?: string;
  result?: AnalysisResult;
  error?: string;
}

/** 上传响应 */
export interface UploadResponse {
  task_id: string;
  status: TaskStatus;
}

/** 导出文件类型 */
export type ExportFormat = 'pdf' | 'gta' | 'gp' | 'midi';

// ---------------------------------------------------------------------------
// API 客户端
// ---------------------------------------------------------------------------

// 开发环境默认指向本地后端；生产环境使用环境变量
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 60_000, // 60s，适用于音频上传
      headers: { 'Content-Type': 'application/json' },
    });

    // 响应拦截：统一抛出错误
    this.client.interceptors.response.use(
      (res) => res,
      (err) => {
        const msg = err.response?.data?.detail || err.message || '未知错误';
        return Promise.reject(new Error(msg));
      }
    );
  }

  // ── 上传音频文件（FormData）────────────────────────────────────────────
  async uploadAudio(file: File): Promise<UploadResponse> {
    const form = new FormData();
    form.append('file', file, file.name);

    const res = await this.client.post<UploadResponse>('/api/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      // 音频文件较大，提升超时
      timeout: 300_000,
    });
    return res.data;
  }

  // ── 通过 URL 触发分析 ─────────────────────────────────────────────────
  async analyzeUrl(url: string): Promise<UploadResponse> {
    const res = await this.client.post<UploadResponse>('/api/analyze-url', { url });
    return res.data;
  }

  // ── 查询任务状态 ──────────────────────────────────────────────────────
  async getTask(taskId: string): Promise<TaskRecord> {
    const res = await this.client.get<TaskRecord>(`/api/task/${taskId}`);
    return res.data;
  }

  // ── 获取分析结果 JSON ─────────────────────────────────────────────────
  async getResult(taskId: string): Promise<AnalysisResult> {
    const res = await this.client.get<AnalysisResult>(`/api/result/${taskId}`);
    return res.data;
  }

  // ── 获取分离后的音频轨（Blob URL）──────────────────────────────────────
  async getSeparateTrack(
    taskId: string,
    track: 'guitar' | 'bass' | 'drums' | 'vocals'
  ): Promise<string> {
    const res = await this.client.get(`/api/separate/${taskId}?track=${track}`, {
      responseType: 'blob',
    });
    return URL.createObjectURL(res.data);
  }

  // ── 轮询任务直到完成 ──────────────────────────────────────────────────
  async pollTask(
    taskId: string,
    onProgress?: (task: TaskRecord) => void,
    intervalMs = 2000,
    maxAttempts = 150 // 最多等待 5 分钟
  ): Promise<TaskRecord> {
    for (let i = 0; i < maxAttempts; i++) {
      const task = await this.getTask(taskId);

      if (onProgress) onProgress(task);

      if (task.status === 'done') return task;
      if (task.status === 'error') {
        throw new Error(`任务失败: ${task.error || '未知错误'}`);
      }

      await this.delay(intervalMs);
    }
    throw new Error('任务超时，请稍后重试');
  }

  // ── 下载导出文件（返回 Blob URL）──────────────────────────────────────
  async downloadExport(taskId: string, format: ExportFormat): Promise<string> {
    const res = await this.client.get(`/api/download/${format}/${taskId}`, {
      responseType: 'blob',
    });
    return URL.createObjectURL(res.data);
  }

  private delay(ms: number) {
    return new Promise((r) => setTimeout(r, ms));
  }
}

// ---------------------------------------------------------------------------
// 导出单例
// ---------------------------------------------------------------------------
export const api = new ApiClient(BASE_URL);
export default api;
