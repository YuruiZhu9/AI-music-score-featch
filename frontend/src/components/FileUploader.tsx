/**
 * FileUploader — 拖拽上传组件
 * ================================
 * 支持拖拽和点击上传音频文件，同时提供 URL 输入入口。
 */

import React, { useCallback, useRef, useState } from 'react';
import { Upload, Link2, X, Music, Loader2 } from 'lucide-react';

interface FileUploaderProps {
  /** 上传文件时的回调（外部负责调用 API） */
  onFileSelected: (file: File) => void;
  /** 提交 URL 时的回调 */
  onUrlSubmit: (url: string) => void;
  /** 是否正在处理（上传中） */
  loading?: boolean;
  /** 上传进度 0-100 */
  progress?: number;
}

const ACCEPTED_TYPES = ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/mp4', 'audio/x-m4a', 'audio/ogg'];
const ACCEPTED_EXTS = '.mp3 .wav .flac .m4a .ogg';

export const FileUploader: React.FC<FileUploaderProps> = ({
  onFileSelected,
  onUrlSubmit,
  loading = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [urlValue, setUrlValue] = useState('');
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // -------------------------------------------------------------------------
  // 文件处理
  // -------------------------------------------------------------------------
  const handleFile = useCallback(
    (file: File) => {
      if (!ACCEPTED_TYPES.includes(file.type) && !file.name.match(/\.(mp3|wav|flac|m4a|ogg)$/i)) {
        alert('不支持的文件格式，请上传 MP3 / WAV / FLAC / M4A / OGG 格式');
        return;
      }
      setFileName(file.name);
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  // -------------------------------------------------------------------------
  // URL 提交
  // -------------------------------------------------------------------------
  const handleUrlSubmit = () => {
    const trimmed = urlValue.trim();
    if (!trimmed) return;
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      alert('请输入以 http:// 或 https:// 开头的链接');
      return;
    }
    setShowUrlInput(false);
    setUrlValue('');
    onUrlSubmit(trimmed);
  };

  // -------------------------------------------------------------------------
  // 渲染
  // -------------------------------------------------------------------------
  return (
    <div className="w-full max-w-xl mx-auto space-y-4">

      {/* 拖拽上传区 */}
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
            <p className="text-gray-500 dark:text-gray-400">
              正在上传 {fileName ?? '音频文件'}…
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
              <Music className="w-8 h-8 text-blue-500" />
            </div>
            <div>
              <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">
                拖拽音频文件到这里
              </p>
              <p className="text-sm text-gray-400 mt-1">或点击选择文件</p>
              <p className="text-xs text-gray-400 mt-2">
                支持格式：MP3 · WAV · FLAC · M4A · OGG
              </p>
            </div>
          </div>
        )}
      </div>

      {/* URL 输入入口 */}
      {!loading && (
        <div className="flex justify-center">
          {showUrlInput ? (
            <div className="flex items-center gap-2 w-full max-w-xl animate-in fade-in slide-in-from-top-2 duration-200">
              <div className="relative flex-1">
                <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                <input
                  autoFocus
                  type="url"
                  value={urlValue}
                  onChange={(e) => setUrlValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleUrlSubmit()}
                  placeholder="粘贴 B站 / YouTube 链接…"
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={handleUrlSubmit}
                className="px-4 py-2.5 rounded-xl bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors"
              >
                提交
              </button>
              <button
                onClick={() => { setShowUrlInput(false); setUrlValue(''); }}
                className="p-2.5 rounded-xl text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
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

      {/* 提示文字 */}
      <p className="text-center text-xs text-gray-400">
        音频将上传至服务器处理，请确保您有权使用该内容
      </p>
    </div>
  );
};

export default FileUploader;
