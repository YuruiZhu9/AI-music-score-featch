/**
 * ChordViewer — 和弦时间轴
 * ================================
 * 展示和弦时间轴，支持点击播放音频预览，
 * 同时显示 BPM / 时间签名等基本信息。
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Pause, Clock, Music } from 'lucide-react';
import type { AnalysisResult } from '../api/client';

interface ChordViewerProps {
  result: AnalysisResult;
  /** 可选：音频 Blob URL（用于点击播放） */
  audioUrl?: string;
  className?: string;
}

// ---------------------------------------------------------------------------
// 工具函数
// ---------------------------------------------------------------------------
/** 吉他指法图 HTML 生成（用 CSS grid 模拟琴弦） */
function guitarDiagram(chord: string): string {
  // 常见和弦到指法的映射（简化版）
  const shapes: Record<string, { positions: number[]; finger?: number[]; barre?: number }> = {
    Am: { positions: [0, 1, 2, 2, 1, 0], finger: [0, 1, 2, 3, 1, 0] },
    G: { positions: [3, 2, 0, 0, 0, 3], finger: [2, 1, 0, 0, 0, 3] },
    C: { positions: [-1, 3, 2, 0, 1, 0], finger: [0, 3, 2, 0, 1, 0] },
    D: { positions: [-1, -1, 0, 2, 3, 2], finger: [0, 0, 0, 1, 3, 2] },
    Em: { positions: [0, 2, 2, 0, 0, 0], finger: [0, 2, 3, 0, 0, 0] },
    E: { positions: [0, 2, 2, 1, 0, 0], finger: [0, 2, 3, 1, 0, 0] },
    F: { positions: [1, 3, 3, 2, 1, 1], barre: 1 },
    Am7: { positions: [0, 1, 2, 0, 1, 0], finger: [0, 1, 2, 0, 3, 0] },
    Cmaj7: { positions: [-1, 3, 2, 0, 0, 0], finger: [0, 1, 2, 0, 0, 0] },
    Dm: { positions: [-1, -1, 0, 2, 3, 1], finger: [0, 0, 0, 2, 3, 1] },
  };

  const shape = shapes[chord] ?? { positions: [-1, -1, -1, -1, -1, -1] };
  return chord;
}

// ---------------------------------------------------------------------------
// 子组件：单个小节
// ---------------------------------------------------------------------------
interface ChordBlockProps {
  chord: string;
  start: number;
  end: number;
  isPlaying: boolean;
  onPlay: () => void;
}

const ChordBlock: React.FC<ChordBlockProps> = ({ chord, start, end, isPlaying, onPlay }) => {
  const width = Math.max(60, (end - start) * 60); // 粗略按秒换算宽度
  const label = chord || '?';

  return (
    <div
      className={`
        flex-shrink-0 flex flex-col items-center justify-center rounded-xl cursor-pointer
        transition-all duration-150 select-none
        ${isPlaying
          ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/40 scale-105'
          : 'bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 hover:border-blue-400 hover:shadow-md'
        }
      `}
      style={{ minWidth: `${width}px`, height: '80px' }}
      onClick={onPlay}
      title={`${label}  ${start.toFixed(1)}s - ${end.toFixed(1)}s`}
    >
      <span className={`text-lg font-bold ${isPlaying ? 'text-white' : 'text-gray-800 dark:text-white'}`}>
        {label}
      </span>
      <span className={`text-xs mt-1 ${isPlaying ? 'text-blue-100' : 'text-gray-400'}`}>
        {start.toFixed(1)}s
      </span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// 主组件
// ---------------------------------------------------------------------------
export const ChordViewer: React.FC<ChordViewerProps> = ({ result, audioUrl, className = '' }) => {
  const { bpm, time_signature, chords } = result;

  // 音频播放状态
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  // 初始化 audio
  useEffect(() => {
    if (!audioUrl) return;
    const audio = new Audio(audioUrl);
    audioRef.current = audio;

    audio.addEventListener('timeupdate', () => setCurrentTime(audio.currentTime));
    audio.addEventListener('ended', () => setPlaying(false));

    return () => {
      audio.pause();
      audio.src = '';
    };
  }, [audioUrl]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      audio.play().then(() => setPlaying(true)).catch(() => {});
    }
  }, [playing]);

  const handleChordClick = useCallback(
    (start: number) => {
      const audio = audioRef.current;
      if (!audio) return;
      audio.currentTime = start;
      if (!playing) {
        audio.play().then(() => setPlaying(true)).catch(() => {});
      }
    },
    [playing]
  );

  // 当前活跃的和弦 index
  const activeIndex = chords.findIndex(
    (c, i) => currentTime >= c.start && (i === chords.length - 1 || currentTime < chords[i + 1].start)
  );

  // ---------------------------------------------------------------------------
  // 渲染
  // ---------------------------------------------------------------------------
  return (
    <div className={`space-y-4 ${className}`}>

      {/* 顶部信息栏 */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
          <Music className="w-4 h-4 text-blue-500" />
          <span className="font-medium">{bpm} BPM</span>
        </div>
        <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
          <Clock className="w-4 h-4 text-blue-500" />
          <span>{time_signature} 拍</span>
        </div>
        <div className="text-xs text-gray-400">
          共识别 {chords.length} 个和弦
        </div>

        {/* 播放按钮 */}
        {audioUrl && (
          <button
            onClick={togglePlay}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors"
          >
            {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {playing ? '暂停' : '播放预览'}
          </button>
        )}
      </div>

      {/* 和弦时间轴（横向滚动） */}
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-2 min-w-max px-1 py-2">
          {chords.map((chord, i) => (
            <ChordBlock
              key={`${chord.chord}-${i}`}
              chord={chord.chord}
              start={chord.start}
              end={chord.end}
              isPlaying={i === activeIndex}
              onPlay={() => handleChordClick(chord.start)}
            />
          ))}
        </div>
      </div>

      {/* 当前播放位置指示线（简化版） */}
      {audioUrl && (
        <div className="relative h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className="absolute left-0 top-0 h-full bg-blue-500 rounded-full transition-all duration-200"
            style={{
              width: audioRef.current
                ? `${(currentTime / (audioRef.current.duration || 1)) * 100}%`
                : '0%',
            }}
          />
        </div>
      )}
    </div>
  );
};

export default ChordViewer;
