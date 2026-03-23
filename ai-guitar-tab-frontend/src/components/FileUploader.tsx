/**
 * 文件上传组件 — 拖拽上传 + 点击选择
 * =====================================
 * 支持音频文件（MP3/WAV/FLAC）和视频文件（MP4）。
 * 支持两种模式：本地文件上传 和 视频URL粘贴。
 */

import React, { useState, useCallback, useRef } from "react";

interface FileUploaderProps {
  onFileSelected: (file: File) => void;
  onUrlSubmitted: (url: string) => void;
  isLoading: boolean;
}

// 支持的文件类型
const ALLOWED_TYPES = [
  "audio/mpeg",
  "audio/wav",
  "audio/flac",
  "audio/x-flac",
  "video/mp4",
  "video/mpeg",
  "audio/mp4",
];
const ALLOWED_EXTENSIONS = [".mp3", ".wav", ".flac", ".mp4", ".m4a"];
const MAX_FILE_SIZE_MB = 50;

export const FileUploader: React.FC<FileUploaderProps> = ({
  onFileSelected,
  onUrlSubmitted,
  isLoading,
}) => {
  const [activeTab, setActiveTab] = useState<"file" | "url">("file");
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [urlInput, setUrlInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [urlError, setUrlError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ─── 文件验证 ──────────────────────────────────────────────────

  const validateFile = useCallback((file: File): string | null => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `不支持的文件格式：${ext}。请上传 MP3、WAV、FLAC 或 MP4 文件。`;
    }

    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > MAX_FILE_SIZE_MB) {
      return `文件过大（${sizeMB.toFixed(1)}MB），最大支持 ${MAX_FILE_SIZE_MB}MB。`;
    }

    return null;
  }, []);

  // ─── 文件选择 ──────────────────────────────────────────────────

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const err = validateFile(file);
      if (err) {
        setError(err);
        setSelectedFile(null);
        return;
      }

      setError(null);
      setSelectedFile(file);
    },
    [validateFile]
  );

  // ─── 拖拽事件 ──────────────────────────────────────────────────

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files?.[0];
      if (!file) return;

      const err = validateFile(file);
      if (err) {
        setError(err);
        setSelectedFile(null);
        return;
      }

      setError(null);
      setSelectedFile(file);
    },
    [validateFile]
  );

  // ─── 提交 ─────────────────────────────────────────────────────

  const handleFileSubmit = useCallback(() => {
    if (selectedFile && !isLoading) {
      onFileSelected(selectedFile);
    }
  }, [selectedFile, isLoading, onFileSelected]);

  const handleUrlSubmit = useCallback(() => {
    const trimmed = urlInput.trim();
    if (!trimmed) {
      setUrlError("请输入视频链接");
      return;
    }

    // 简单 URL 验证
    const isValid =
      trimmed.startsWith("http://") || trimmed.startsWith("https://");
    if (!isValid) {
      setUrlError("请输入以 http:// 或 https:// 开头的链接");
      return;
    }

    setUrlError(null);
    onUrlSubmitted(trimmed);
  }, [urlInput, onUrlSubmitted]);

  // ─── 平台检测 ─────────────────────────────────────────────────

  const detectPlatform = (url: string): string => {
    if (url.includes("bilibili.com") || url.includes("b23.tv")) return "bilibili";
    if (url.includes("youtube.com") || url.includes("youtu.be")) return "youtube";
    if (url.includes("douyin.com")) return "douyin";
    return "unknown";
  };

  const platform = detectPlatform(urlInput);
  const platformIcons: Record<string, string> = {
    bilibili: "📺",
    youtube: "▶️",
    douyin: "🎵",
    unknown: "🔗",
  };

  return (
    <div className="w-full max-w-xl mx-auto">
      {/* 标签切换 */}
      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-xl">
        <button
          onClick={() => setActiveTab("file")}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all
            ${activeTab === "file"
              ? "bg-white text-blue-600 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
            }`}
        >
          📁 上传音频
        </button>
        <button
          onClick={() => setActiveTab("url")}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all
            ${activeTab === "url"
              ? "bg-white text-purple-600 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
            }`}
        >
          🔗 视频链接
        </button>
      </div>

      {/* ── 文件上传 ── */}
      {activeTab === "file" && (
        <div className="space-y-4">
          {/* 拖拽区域 */}
          <div
            onClick={() => !isLoading && fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
              transition-all duration-200
              ${isDragging
                ? "border-blue-500 bg-blue-50 scale-[1.02]"
                : "border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50"
              }
              ${isLoading ? "opacity-50 cursor-not-allowed" : ""}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp3,.wav,.flac,.mp4,.m4a,audio/*"
              onChange={handleFileChange}
              className="hidden"
              disabled={isLoading}
            />

            {/* 图标 */}
            <div className="text-5xl mb-4">
              {selectedFile ? "🎵" : "🎸"}
            </div>

            {selectedFile ? (
              <>
                <p className="text-gray-800 font-medium text-lg mb-1">
                  {selectedFile.name}
                </p>
                <p className="text-gray-400 text-sm">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                </p>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                    setError(null);
                  }}
                  className="mt-3 text-xs text-red-500 hover:text-red-700"
                >
                  移除文件
                </button>
              </>
            ) : (
              <>
                <p className="text-gray-700 font-medium mb-1">
                  拖拽音频文件到这里
                </p>
                <p className="text-gray-400 text-sm mb-3">
                  或点击选择文件
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {ALLOWED_EXTENSIONS.map((ext) => (
                    <span
                      key={ext}
                      className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded-full"
                    >
                      {ext}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-gray-300 mt-3">
                  最大 {MAX_FILE_SIZE_MB}MB
                </p>
              </>
            )}
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 px-4 py-3 rounded-xl">
              <span>⚠️</span>
              {error}
            </div>
          )}

          {/* 上传按钮 */}
          <button
            onClick={handleFileSubmit}
            disabled={!selectedFile || isLoading}
            className={`w-full py-4 rounded-xl text-white font-semibold text-lg
              transition-all duration-200 shadow-lg
              ${selectedFile && !isLoading
                ? "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 cursor-pointer"
                : "bg-gray-300 cursor-not-allowed"
              }`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin">⏳</span>
                处理中...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                🎯 开始扒谱
              </span>
            )}
          </button>
        </div>
      )}

      {/* ── URL 粘贴 ── */}
      {activeTab === "url" && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl">{platformIcons[platform]}</span>
              <span className="text-gray-600 text-sm">
                {platform === "bilibili" && "B站视频"}
                {platform === "youtube" && "YouTube 视频"}
                {platform === "douyin" && "抖音视频"}
                {platform === "unknown" && "支持 B站 / YouTube / 抖音"}
              </span>
            </div>

            <input
              type="url"
              value={urlInput}
              onChange={(e) => {
                setUrlInput(e.target.value);
                setUrlError(null);
              }}
              onKeyDown={(e) => e.key === "Enter" && handleUrlSubmit()}
              placeholder="https://www.bilibili.com/video/BVxxx"
              className={`w-full px-4 py-3 border rounded-xl text-gray-700 focus:outline-none
                focus:ring-2 transition-all
                ${urlError ? "border-red-400 focus:ring-red-200" : "border-gray-200 focus:border-blue-400 focus:ring-blue-100"}
              `}
              disabled={isLoading}
            />

            {urlError && (
              <p className="mt-2 text-red-500 text-sm flex items-center gap-1">
                <span>⚠️</span> {urlError}
              </p>
            )}

            <div className="mt-4 text-xs text-gray-400 space-y-1">
              <p>💡 提示：B站视频建议使用 BV 号链接（如 BV1xx411c7XZ）</p>
              <p>⚠️ 部分视频可能因版权限制无法下载</p>
            </div>
          </div>

          <button
            onClick={handleUrlSubmit}
            disabled={!urlInput.trim() || isLoading}
            className={`w-full py-4 rounded-xl text-white font-semibold text-lg
              transition-all duration-200 shadow-lg
              ${urlInput.trim() && !isLoading
                ? "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 cursor-pointer"
                : "bg-gray-300 cursor-not-allowed"
              }`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin">⏳</span>
                解析中...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                ▶ 解析视频
              </span>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
