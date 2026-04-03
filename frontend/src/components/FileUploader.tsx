/**
 * FileUploader — 拖拽上传组件
 * ================================
 * 支持拖拽和点击上传音频文件，同时提供 B站 / YouTube URL 输入入口。
 */

import React, { useCallback, useRef, useState } from 'react';
import { Upload, Link2, X, Music, Loader2 } from 'lucide-react';

interface FileUploaderProps {
  /** 上传文件时的回调 */
  onFileSelected: (file: File) => void;
  /** 提交 URL 时的回调 */
  onUrlSubmit: (url: string) => void;
  /** 是否正在处理 */
  loading?: boolean;
}

// 支持的音频 MIME 类型和文件扩展名
const ACCEPTED_TYPES = [
  'audio/mpeg', 'audio/wav', 'audio/flac',
  'audio/mp4', 'audio/x-m4a', 'audio/ogg',
  'video/mp4', 'video/webm', 'video/ogg',
];
const ACCEPTED_EXTS = '.mp3 .wav .flac .m4a .ogg .mp4 .webm';

// ---------------------------------------------------------------------------
// URL 验证
// ---------------------------------------------------------------------------
/** 检测是否为支持的视频/音频 URL */
function detectUrlPlatform(url: string): { name: string; icon: string; ok: boolean } {
  const lower = url.toLowerCase();
  if (lower.includes('bilibili.com') || lower.includes('b23.tv')) {
    return { name: '哔哩哔哩', icon: '📺', ok: true };
  }
  if (lower.includes('youtube.com') || lower.includes('youtu.be')) {
    return { name: 'YouTube', icon: '▶️', ok: true };
  }
  return { name: '未知平台', icon: '🔗', ok: false };
}

// ---------------------------------------------------------------------------
// 主组件
// ---------------------------------------------------------------------------
export const FileUploader: React.FC<FileUploaderProps> = ({
  onFileSelected,
  onUrlSubmit,
  loading = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [urlValue, setUrlValue] = useState('');
  const [urlError, setUrlError] = useState<string | null>(null);
  const [platformInfo, setPlatformInfo] = useState<{ name: string; icon: string; ok: boolean } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // -------------------------------------------------------------------------
  // 文件处理
  // -------------------------------------------------------------------------
  const processFile = useCallback(
    (file: File) => {
      // 扩展名二次校验
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      const isAcceptedType = ACCEPTED_TYPES.includes(file.type);
      const isAcceptedExt = ACCEPTED_EXTS.split(' ').includes(ext);

      if (!isAcceptedType && !isAcceptedExt) {
        alert(
          `不支持的文件格式 "${ext}"。\n\n` +
          `请上传以下格式：MP3 · WAV · FLAC · M4A · OGG · MP4 · WebM`
        );
        return;
      }

      // 50MB 限制
      const MAX_SIZE = 50 * 1024 * 1024;
      if (file.size > MAX_SIZE) {
        alert(`文件过大（${(file.size / 1024 / 1024).toFixed(1)} MB）。\n最大支持 50 MB，请压缩或截取后再上传。`);
        return;
      }

      onFileSelected(file);
    },
    [onFileSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  // -------------------------------------------------------------------------
  // URL 验证
  // -------------------------------------------------------------------------
  const handleUrlChange = (val: string) => {
    setUrlValue(val);
    setUrlError(null);
    if (val.trim()) {
      const info = detectUrlPlatform(val);
      setPlatformInfo(info);
      if (!info.ok) {
        setUrlError(`暂不支持 "${info.name}" 链接，当前仅支持哔哩哔哩和 YouTube`);
      }
    } else {
      setPlatformInfo(null);
    }
  };

  const handleUrlSubmit = () => {
    const trimmed = urlValue.trim();
    if (!trimmed) {
      setUrlError('请输入链接');
      return;
    }
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      setUrlError('链接必须以 http:// 或 https:// 开头');
      return;
    }
    const info = platformInfo;
    if (!info?.ok) {
      setUrlError('暂不支持该平台，请使用哔哩哔哩或 YouTube 链接');
      return;
    }
    setShowUrlInput(false);
    setUrlValue('');
    setPlatformInfo(null);
    onUrlSubmit(trimmed);
  };

  const handleUrlKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleUrlSubmit();
    if (e.key === 'Escape') { setShowUrlInput(false); setUrlValue(''); setUrlError(null); }
  };

  // -------------------------------------------------------------------------
  // 渲染
  // -------------------------------------------------------------------------
  return (
    <div className="w-full max-w-xl mx-auto space-y-4">

      {/* ── 拖拽上传区 ─────────────────────────────────────── */}
      <div
        className={`
          relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
          transition-all duration-200 select-none
          ${isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30 scale-[1.01]'
            : 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 hover:border-blue-400 hover:bg-blue-50/50 dark:hover:bg-blue-950/20'
          }
          ${loading ? 'pointer-events-none opacity-60' : ''}
        `}
        onDragEnter={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !loading && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTS}
          className="hidden"
          onChange={handleInputChange}
        />

        {loading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
            <p className="text-gray-500 dark:text-gray-400">正在处理，请稍候…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
              {isDragging ? (
                <Upload className="w-8 h-8 text-blue-500 animate-bounce" />
              ) : (
                <Music className="w-8 h-8 text-blue-500" />
              )}
            </div>
            <div>
              {isDragging ? (
                <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                  松开手指开始上传
                </p>
              ) : (
                <>
                  <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">
                    拖拽音频文件到这里
                  </p>
                  <p className="text-sm text-gray-400 mt-1">或点击选择文件</p>
                </>
              )}
              {!isDragging && (
                <p className="text-xs text-gray-400 mt-3">
                  支持格式：MP3 · WAV · FLAC · M4A · OGG · MP4 · WebM
                  <span className="mx-2">·</span>
                  最大 50 MB
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── URL 输入入口 ────────────────────────────────────── */}
      {!loading && (
        <div className="flex justify-center">
          {showUrlInput ? (
            <div className="flex flex-col gap-2 w-full max-w-xl animate-in fade-in slide-in-from-top-2 duration-200">
              {/* 平台提示 */}
              {platformInfo && (
                <div className={`flex items-center gap-2 text-sm ${platformInfo.ok ? 'text-green-600 dark:text-green-400' : 'text-amber-500'}`}>
                  <span>{platformInfo.icon}</span>
                  <span>{platformInfo.name}</span>
                  {platformInfo.ok
                    ? <span className="text-xs text-green-500 dark:text-green-400 ml-1">✓ 支持</span>
                    : <span className="text-xs text-amber-500 ml-1">（暂不支持）</span>
                  }
                </div>
              )}

              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                  <input
                    autoFocus
                    type="url"
                    value={urlValue}
                    onChange={(e) => handleUrlChange(e.target.value)}
                    onKeyDown={handleUrlKeyDown}
                    placeholder="粘贴 B站 / YouTube 视频链接…"
                    className={`
                      w-full pl-9 pr-4 py-2.5 rounded-xl border text-sm bg-white dark:bg-gray-800
                      focus:outline-none focus:ring-2 transition-colors
                      ${urlError
                        ? 'border-red-400 dark:border-red-600 focus:ring-red-300 dark:focus:ring-red-700 text-red-700 dark:text-red-300'
                        : 'border-gray-300 dark:border-gray-600 focus:ring-blue-300 dark:focus:ring-blue-700 text-gray-800 dark:text-gray-100'
                      }
                    `}
                  />
                </div>
                <button
                  onClick={handleUrlSubmit}
                  disabled={!!urlError || !urlValue.trim()}
                  className="px-4 py-2.5 rounded-xl bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  开始解析
                </button>
                <button
                  onClick={() => { setShowUrlInput(false); setUrlValue(''); setUrlError(null); setPlatformInfo(null); }}
                  className="p-2.5 rounded-xl text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* 错误提示 */}
              {urlError && (
                <p className="text-xs text-red-500 dark:text-red-400 pl-1">{urlError}</p>
              )}
            </div>
          ) : (
            <button
              onClick={() => setShowUrlInput(true)}
              className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 hover:text-blue-500 transition-colors"
            >
              <Link2 className="w-4 h-4" />
              使用 B站 / YouTube 链接
            </button>
          )}
        </div>
      )}

      {/* ── 提示文字 ───────────────────────────────────────── */}
      <p className="text-center text-xs text-gray-400">
        音频将上传至服务器处理，请确保您有权使用该内容
      </p>
    </div>
  );
};

export default FileUploader;
