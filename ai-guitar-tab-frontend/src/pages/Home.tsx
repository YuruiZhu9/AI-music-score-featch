/**
 * 首页 — 上传页面
 * ==================
 * 支持两种输入方式：
 * 1. 拖拽/选择本地音频文件
 * 2. 粘贴视频链接（B站/YouTube）
 */
import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { FileUploader } from "../components/FileUploader";
import { ProgressBar } from "../components/ProgressBar";
import {
  uploadAudio,
  waitForResult,
  getHealth,
  TaskStatus,
} from "../api/client";

type Page = "home" | "processing" | "error";

export default function Home() {
  const navigate = useNavigate();
  const [page, setPage] = useState<Page>("home");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 处理文件选择
  const handleFileSelected = useCallback(async (file: File) => {
    setPage("processing");
    setTaskId(null);
    setTaskStatus(null);
    setError(null);

    try {
      // 先检查后端是否可用
      try {
        await getHealth();
      } catch {
        throw new Error("后端服务不可用，请确保 FastAPI 服务正在运行（localhost:8000）。");
      }

      // 上传文件
      const uploadRes = await uploadAudio(file);
      setTaskId(uploadRes.task_id);

      // 轮询直到完成
      const result = await waitForResult(uploadRes.task_id, (status) => {
        setTaskStatus(status);
      });

      // 跳转到结果页（使用 query param）
      navigate(`/result?taskId=${uploadRes.task_id}`, { replace: true });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "未知错误";
      setError(msg);
      setPage("error");
    }
  }, [navigate]);

  // 处理 URL 提交（暂不支持）
  const handleUrlSubmitted = useCallback(async (_url: string) => {
    setError("视频链接分析功能正在开发中，请先使用音频文件上传。");
    setPage("error");
  }, []);

  // 返回首页
  const handleGoHome = useCallback(() => {
    setPage("home");
    setTaskId(null);
    setTaskStatus(null);
    setError(null);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex flex-col">
      {/* 顶部区域 */}
      <div className="pt-16 pb-8 text-center">
        <h1 className="text-5xl font-bold text-white mb-3 flex items-center justify-center gap-3">
          <span>🎸</span>
          <span>AI Guitar Tab</span>
        </h1>
        <p className="text-blue-300 text-lg">
          输入音频 / 视频链接，几分钟即可获得吉他谱
        </p>
        <div className="flex justify-center gap-3 mt-4 flex-wrap">
          {["🎵 MP3", "🎙️ WAV", "💿 FLAC", "🎬 MP4", "📺 B站", "▶️ YouTube"].map((tag) => (
            <span key={tag} className="px-3 py-1 bg-blue-800/40 text-blue-200 text-sm rounded-full">
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* 主内容区 */}
      <div className="flex-1 flex items-start justify-center px-4 pb-16">
        <div className="w-full max-w-2xl">
          {/* 首页：上传区域 */}
          {page === "home" && (
            <div className="space-y-6">
              <FileUploader
                onFileSelected={handleFileSelected}
                onUrlSubmitted={handleUrlSubmitted}
                isLoading={false}
              />

              {/* 特点展示 */}
              <div className="grid grid-cols-3 gap-4 mt-8">
                {[
                  { icon: "⚡", title: "智能识别", desc: "AI 自动检测和弦、BPM、指法" },
                  { icon: "🎼", title: "多格式导出", desc: "Guitar Pro / PDF / 文本谱" },
                  { icon: "🚀", title: "快速处理", desc: "3 分钟歌曲，约 2-5 分钟出谱" },
                ].map((item) => (
                  <div key={item.title} className="bg-white/5 border border-white/10 rounded-2xl p-4 text-center">
                    <div className="text-3xl mb-2">{item.icon}</div>
                    <div className="text-white font-semibold text-sm mb-1">{item.title}</div>
                    <div className="text-gray-400 text-xs">{item.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 处理中：进度条 */}
          {page === "processing" && (
            <div className="space-y-4">
              <ProgressBar
                progress={taskStatus?.progress ?? 0}
                stage={taskStatus?.stage ?? "等待上传..."}
              />
              <p className="text-center text-gray-400 text-sm">
                正在处理中，请勿关闭页面...
              </p>
            </div>
          )}

          {/* 错误页 */}
          {page === "error" && (
            <div className="bg-red-900/30 border border-red-500/30 rounded-2xl p-8 text-center space-y-4">
              <div className="text-5xl">😔</div>
              <h2 className="text-xl font-semibold text-white">处理失败</h2>
              <p className="text-red-300">{error}</p>
              <div className="space-y-2">
                <button
                  onClick={handleGoHome}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors"
                >
                  ← 重新上传
                </button>
                <p className="text-gray-500 text-xs">
                  如果问题持续，请检查后端服务是否运行
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
