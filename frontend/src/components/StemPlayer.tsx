/**
 * StemPlayer — 分离音轨播放器
 * ====================================
 * 展示 Demucs 分离后的 Guitar / Bass / Drums / Vocals 四条音轨，
 * 支持独立播放、混音开关、音量调节。
 *
 * 依赖 API：GET /api/separate/{taskId}?track={guitar|bass|drums|vocals}
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Volume2, VolumeX, Play, Pause, Loader2 } from 'lucide-react';
import { api } from '../api/client';

interface Stem {
  id: 'guitar' | 'bass' | 'drums' | 'vocals';
  label: string;
  emoji: string;
  color: string;
  colorBg: string;
  colorBorder: string;
  colorActive: string;
}

const STEMS: Stem[] = [
  {
    id: 'guitar',
    label: '吉他',
    emoji: '🎸',
    color: 'text-blue-600',
    colorBg: 'bg-blue-50 dark:bg-blue-950/30',
    colorBorder: 'border-blue-200 dark:border-blue-800',
    colorActive: 'bg-blue-100 dark:bg-blue-900/50 border-blue-400',
  },
  {
    id: 'bass',
    label: '贝斯',
    emoji: '🎸',
    color: 'text-amber-600',
    colorBg: 'bg-amber-50 dark:bg-amber-950/30',
    colorBorder: 'border-amber-200 dark:border-amber-800',
    colorActive: 'bg-amber-100 dark:bg-amber-900/50 border-amber-400',
  },
  {
    id: 'drums',
    label: '鼓组',
    emoji: '🥁',
    color: 'text-red-600',
    colorBg: 'bg-red-50 dark:bg-red-950/30',
    colorBorder: 'border-red-200 dark:border-red-800',
    colorActive: 'bg-red-100 dark:bg-red-900/50 border-red-400',
  },
  {
    id: 'vocals',
    label: '人声',
    emoji: '🎤',
    color: 'text-green-600',
    colorBg: 'bg-green-50 dark:bg-green-950/30',
    colorBorder: 'border-green-200 dark:border-green-800',
    colorActive: 'bg-green-100 dark:bg-green-900/50 border-green-400',
  },
];

interface StemPlayerProps {
  taskId: string;
  /** 是否默认展开 */
  defaultExpanded?: boolean;
}

const StemPlayer: React.FC<StemPlayerProps> = ({
  taskId,
  defaultExpanded = false,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [loadedStems, setLoadedStems] = useState<Record<string, string>>({});
  const [loadingStems, setLoadingStems] = useState<Record<string, boolean>>({});
  const [activeStems, setActiveStems] = useState<Record<string, boolean>>({
    guitar: true,
    bass: true,
    drums: true,
    vocals: false,
  });
  const [volumes, setVolumes] = useState<Record<string, number>>({
    guitar: 0.8,
    bass: 0.7,
    drums: 0.6,
    vocals: 0.8,
  });
  const [masterPlaying, setMasterPlaying] = useState(false);
  const audioRefs = useRef<Record<string, HTMLAudioElement | null>>({});
  const masterRef = useRef<HTMLDivElement>(null);

  // 加载单条音轨
  const loadStem = useCallback(async (stemId: string) => {
    if (loadedStems[stemId]) return; // 已加载
    setLoadingStems((prev) => ({ ...prev, [stemId]: true }));
    try {
      const blobUrl = await api.getSeparateTrack(taskId, stemId as 'guitar' | 'bass' | 'drums' | 'vocals');
      setLoadedStems((prev) => ({ ...prev, [stemId]: blobUrl }));
    } catch {
      // 音轨加载失败不影响主流程（可能是 demo 模式）
      console.warn(`Stem ${stemId} not available`);
    } finally {
      setLoadingStems((prev) => ({ ...prev, [stemId]: false }));
    }
  }, [loadedStems, taskId]);

  // 展开时懒加载所有音轨
  useEffect(() => {
    if (expanded) {
      STEMS.forEach((s) => loadStem(s.id));
    }
  }, [expanded, loadStem]);

  // 同步音频播放状态
  useEffect(() => {
    const refs = audioRefs.current;
    Object.entries(refs).forEach(([id, audio]) => {
      if (!audio) return;
      if (activeStems[id]) {
        audio.volume = volumes[id] ?? 0.8;
      } else {
        audio.volume = 0;
      }
    });
  }, [activeStems, volumes]);

  // 播放/暂停所有活跃音轨
  const toggleMasterPlay = useCallback(async () => {
    const refs = audioRefs.current;

    if (masterPlaying) {
      // 暂停所有
      Object.values(refs).forEach((audio) => {
        if (audio) audio.pause();
      });
      setMasterPlaying(false);
    } else {
      // 播放所有活跃音轨（从当前时间开始）
      const now = Date.now();
      const promises = Object.entries(refs).map(async ([id, audio]) => {
        if (!audio || !activeStems[id]) return;
        try {
          await audio.play();
        } catch {
          // ignore autoplay errors
        }
      });
      await Promise.allSettled(promises);
      setMasterPlaying(true);
    }
  }, [masterPlaying, activeStems]);

  // 同步各音轨时间
  const handleStemPlay = useCallback((playingId: string) => {
    const refs = audioRefs.current;
    const currentAudio = refs[playingId];
    if (!currentAudio) return;
    const currentTime = currentAudio.currentTime;

    Object.entries(refs).forEach(([id, audio]) => {
      if (id !== playingId && audio && activeStems[id]) {
        audio.currentTime = currentTime;
      }
    });
  }, [activeStems]);

  const handleStemPause = useCallback(() => {
    const refs = audioRefs.current;
    Object.values(refs).forEach((audio) => {
      if (audio) audio.pause();
    });
    setMasterPlaying(false);
  }, []);

  const toggleStem = (stemId: string) => {
    setActiveStems((prev) => ({ ...prev, [stemId]: !prev[stemId] }));
  };

  const handleVolume = (stemId: string, vol: number) => {
    setVolumes((prev) => ({ ...prev, [stemId]: vol }));
  };

  const activeCount = Object.values(activeStems).filter(Boolean).length;

  return (
    <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Volume2 className="w-5 h-5 text-blue-500" />
          <h2 className="text-base font-semibold text-gray-700 dark:text-gray-200">
            分离音轨
          </h2>
          <span className="text-xs text-gray-400 ml-1">
            Demucs AI 分离 · {activeCount}/4 轨活跃
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* 混音播放按钮 */}
          {expanded && Object.keys(loadedStems).length > 0 && (
            <button
              onClick={toggleMasterPlay}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                ${masterPlaying
                  ? 'bg-blue-500 text-white hover:bg-blue-600'
                  : 'border border-blue-300 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/30'
                }
              `}
            >
              {masterPlaying ? (
                <><Pause className="w-4 h-4" /> 暂停混音</>
              ) : (
                <><Play className="w-4 h-4" /> 混音播放</>
              )}
            </button>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-sm text-blue-500 hover:text-blue-600 transition-colors"
          >
            {expanded ? '收起' : '展开'}
          </button>
        </div>
      </div>

      {/* 音轨网格 */}
      {expanded && (
        <div className="space-y-3" ref={masterRef}>
          {/* 隐藏的 Audio 元素 */}
          <div className="hidden">
            {STEMS.map((stem) => {
              const url = loadedStems[stem.id];
              if (!url) return null;
              return (
                <audio
                  key={stem.id}
                  ref={(el) => { audioRefs.current[stem.id] = el; }}
                  src={url}
                  onPlay={() => handleStemPlay(stem.id)}
                  onPause={handleStemPause}
                  onEnded={handleStemPause}
                  crossOrigin="anonymous"
                  preload="metadata"
                />
              );
            })}
          </div>

          {/* 加载中占位 */}
          {Object.keys(loadedStems).length === 0 && (
            <div className="flex items-center gap-3 py-6 text-gray-400">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">正在加载分离音轨…</span>
            </div>
          )}

          {/* 4 条音轨 */}
          <div className="grid grid-cols-2 gap-3">
            {STEMS.map((stem) => {
              const isLoaded = !!loadedStems[stem.id];
              const isActive = activeStems[stem.id];
              const vol = volumes[stem.id] ?? 0.8;
              const isLoading = loadingStems[stem.id];

              return (
                <div
                  key={stem.id}
                  className={`
                    rounded-xl border-2 p-3 transition-all
                    ${isActive ? stem.colorActive : 'border-gray-200 dark:border-gray-600'}
                  `}
                >
                  {/* 音轨头部 */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1.5">
                      <span className="text-lg">{stem.emoji}</span>
                      <span className={`text-sm font-medium ${stem.color}`}>
                        {stem.label}
                      </span>
                    </div>
                    <button
                      onClick={() => toggleStem(stem.id)}
                      title={isActive ? '静音此轨' : '启用此轨'}
                      className={`
                        p-1 rounded-lg transition-colors
                        ${isActive ? 'text-gray-500 hover:text-gray-700' : 'text-gray-300'}
                      `}
                    >
                      {isActive ? (
                        <Volume2 className="w-4 h-4" />
                      ) : (
                        <VolumeX className="w-4 h-4" />
                      )}
                    </button>
                  </div>

                  {/* 加载状态 */}
                  {isLoading && (
                    <div className="flex items-center gap-2 py-2 text-xs text-gray-400">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      加载中…
                    </div>
                  )}

                  {/* 未加载 */}
                  {!isLoaded && !isLoading && (
                    <div className="flex items-center gap-2 py-2">
                      <button
                        onClick={() => loadStem(stem.id)}
                        className="text-xs text-blue-500 hover:text-blue-600 transition-colors"
                      >
                        加载 {stem.label} 轨
                      </button>
                    </div>
                  )}

                  {/* 已加载：音量条 */}
                  {isLoaded && (
                    <div className="space-y-2">
                      {/* 音量滑块 */}
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.05}
                        value={vol}
                        onChange={(e) => handleVolume(stem.id, parseFloat(e.target.value))}
                        className={`
                          w-full h-1.5 rounded-full appearance-none cursor-pointer
                          ${stem.id === 'guitar' ? 'accent-blue-500' :
                            stem.id === 'bass' ? 'accent-amber-500' :
                            stem.id === 'drums' ? 'accent-red-500' :
                            'accent-green-500'}
                        `}
                        style={{
                          background: `linear-gradient(to right, currentColor 0%, currentColor ${vol * 100}%, #e5e7eb ${vol * 100}%, #e5e7eb 100%)`,
                          color: stem.id === 'guitar' ? '#3b82f6' :
                                 stem.id === 'bass' ? '#f59e0b' :
                                 stem.id === 'drums' ? '#ef4444' : '#22c55e',
                        }}
                      />
                      <div className="flex justify-between text-xs text-gray-400">
                        <span>{Math.round(vol * 100)}%</span>
                        <span>{isActive ? '🔊' : '🔇'}</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* 说明 */}
          <p className="text-xs text-gray-400 mt-2">
            💡 拖动音量条可调节各轨音量，开启/关闭按钮可单独听某条音轨
          </p>
        </div>
      )}

      {/* 收起时显示摘要 */}
      {!expanded && (
        <div className="flex gap-2 flex-wrap">
          {STEMS.map((stem) => (
            <button
              key={stem.id}
              onClick={() => {
                setExpanded(true);
                loadStem(stem.id);
              }}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border transition-all
                ${stem.colorBg} ${stem.colorBorder} ${stem.color}
                hover:shadow-sm
              `}
            >
              <span>{stem.emoji}</span>
              <span>{stem.label}</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
};

export default StemPlayer;
