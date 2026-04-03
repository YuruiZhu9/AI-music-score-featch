/**
 * ChordViewer — 和弦时间轴 + 吉他指法图
 * ====================================
 * 展示和弦时间轴，支持点击播放音频预览，
 * 同时显示 BPM / 时间签名，鼠标悬停时渲染吉他指法 SVG 图。
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
// 吉他指法数据（标准调弦：E A D G B E）
// - positions[i] = 第(i+1)根弦的品位，-1 = 不用，0 = 空弦
// - finger[i]    = 左手手指编号（1=食指 2=中指 3=无名指 4=小指）
// - barre        = 横按品位（食指横按）
// ---------------------------------------------------------------------------
interface ChordShape {
  positions: number[]; // 6个元素，对应 e B G D A E
  finger?: number[];   // 左手手指
  barre?: number;      // 横按品位
  capo?: number;       // 变调夹品位（隐式）
  label?: string;       // 备注
}

const CHORD_SHAPES: Record<string, ChordShape> = {
  // 大三和弦
  C:  { positions: [-1, 3, 2, 0, 1, 0], finger: [0, 3, 2, 0, 1, 0] },
  D:  { positions: [-1, -1, 0, 2, 3, 2], finger: [0, 0, 0, 1, 3, 2] },
  Em: { positions: [0, 2, 2, 0, 0, 0], finger: [0, 2, 3, 0, 0, 0] },
  E:  { positions: [0, 2, 2, 1, 0, 0], finger: [0, 2, 3, 1, 0, 0] },
  F:  { positions: [1, 3, 3, 2, 1, 1], barre: 1, finger: [1, 3, 4, 2, 1, 1] },
  G:  { positions: [3, 2, 0, 0, 0, 3], finger: [2, 1, 0, 0, 0, 3] },
  A:  { positions: [-1, 0, 2, 2, 2, 0], finger: [0, 1, 2, 3, 4, 0] },
  B:  { positions: [-1, 2, 4, 4, 4, 2], barre: 2 },
  // 小三和弦
  Am: { positions: [0, 1, 2, 2, 1, 0], finger: [0, 1, 2, 3, 1, 0] },
  Dm: { positions: [-1, -1, 0, 2, 3, 1], finger: [0, 0, 0, 2, 3, 1] },
  Bm: { positions: [-1, 2, 4, 4, 3, 2], barre: 2 },
  // 七和弦
  Am7: { positions: [0, 1, 2, 0, 1, 0], finger: [0, 1, 2, 0, 3, 0] },
  Cmaj7: { positions: [-1, 3, 2, 0, 0, 0], finger: [0, 1, 2, 0, 0, 0] },
  Dm7: { positions: [-1, -1, 0, 2, 1, 1], finger: [0, 0, 0, 2, 1, 1] },
  D7:  { positions: [-1, -1, 0, 2, 1, 2], finger: [0, 0, 0, 2, 1, 3] },
  E7:  { positions: [0, 2, 0, 1, 0, 0], finger: [0, 2, 0, 1, 0, 0] },
  G7:  { positions: [3, 2, 0, 0, 0, 1], finger: [2, 1, 0, 0, 0, 1] },
  C7:  { positions: [-1, 3, 2, 3, 1, 0], finger: [0, 3, 2, 4, 1, 0] },
  Fmaj7: { positions: [-1, -1, 0, 2, 3, 0], finger: [0, 0, 0, 1, 3, 0] },
  A7:  { positions: [-1, 0, 2, 0, 2, 0], finger: [0, 1, 2, 0, 3, 0] },
  // 挂留和弦
  Dsus4: { positions: [-1, -1, 0, 2, 3, 3], finger: [0, 0, 0, 1, 3, 4] },
  Dsus2: { positions: [-1, -1, 0, 2, 3, 0], finger: [0, 0, 0, 1, 2, 0] },
  Asus2: { positions: [-1, 0, 2, 2, 0, 0], finger: [0, 1, 2, 3, 0, 0] },
  Asus4: { positions: [-1, 0, 2, 2, 3, 0], finger: [0, 1, 2, 3, 4, 0] },
  // 增/减和弦
  Adim: { positions: [-1, 1, 2, 1, 0, -1], finger: [0, 1, 2, 1, 0, 0] },
  Aaug: { positions: [-1, 0, 3, 2, 2, 1], finger: [0, 1, 3, 2, 2, 1] },
  // 六和弦
  A6: { positions: [-1, 0, 2, 2, 2, 2], finger: [0, 1, 2, 3, 4, 4] },
  Am6: { positions: [0, 1, 2, 2, 1, 2], finger: [0, 1, 2, 3, 1, 4] },
};

// 吉他弦名（从细弦到粗弦）
const STRING_NAMES = ['e', 'B', 'G', 'D', 'A', 'E'];
// 指板渲染范围（品位 1-5，共 5 品）
const FRET_RANGE = 5;

// ---------------------------------------------------------------------------
// 子组件：吉他指法 SVG 图
// ---------------------------------------------------------------------------
interface GuitarDiagramProps {
  chordName: string;
  width?: number;
  height?: number;
}

const GuitarDiagram: React.FC<GuitarDiagramProps> = ({
  chordName,
  width = 120,
  height = 140,
}) => {
  const shape = CHORD_SHAPES[chordName];
  const svgWidth = width;
  const svgHeight = height;

  // 指板区域
  const marginLeft = 28;
  const marginTop = 18;
  const marginBottom = 28;
  const fretAreaWidth = svgWidth - marginLeft - 8;
  const fretAreaHeight = svgHeight - marginTop - marginBottom;
  const numFrets = FRET_RANGE;
  const numStrings = 6;
  const stringGap = fretAreaWidth / (numStrings - 1);
  const fretGap = fretAreaHeight / numFrets;

  // 品位标注位置（品位线 x 坐标）
  const fretX = (fret: number) => marginLeft + fret * stringGap;

  // 品格线 y 坐标（第 n 品格 = 第 n 条横线）
  const fretY = (fret: number) => marginTop + fret * fretGap;

  // 手指颜色（1-4 对应不同颜色）
  const fingerColors = ['', '#3B82F6', '#10B981', '#F59E0B', '#EF4444'];
  const fingerLabels = ['', '1', '2', '3', '4'];

  return (
    <div className="flex flex-col items-center">
      <svg
        width={svgWidth}
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        className="overflow-visible"
      >
        {/* 琴头（左侧装饰） */}
        <rect
          x={marginLeft - stringGap - 6}
          y={marginTop - 4}
          width={8}
          height={fretAreaHeight + 8}
          rx={3}
          fill="#92400E"
          opacity={0.7}
        />

        {/* 品格横线 */}
        {Array.from({ length: numFrets + 1 }).map((_, i) => (
          <line
            key={`h${i}`}
            x1={marginLeft}
            y1={fretY(i)}
            x2={marginLeft + fretAreaWidth}
            y2={fretY(i)}
            stroke={i === 0 ? '#1F2937' : '#9CA3AF'}
            strokeWidth={i === 0 ? 3 : i === 1 ? 2 : 1.5}
          />
        ))}

        {/* 琴弦竖线 */}
        {Array.from({ length: numStrings }).map((_, i) => (
          <line
            key={`v${i}`}
            x1={fretX(i)}
            y1={fretY(0)}
            x2={fretX(i)}
            y2={fretY(numFrets)}
            stroke={i < 3 ? '#9CA3AF' : '#6B7280'}
            strokeWidth={i === 0 ? 1 : i < 4 ? 1.2 : 1.6}
          />
        ))}

        {/* 品位标注 */}
        <text
          x={marginLeft - 5}
          y={fretY(1) - 3}
          textAnchor="end"
          fontSize="8"
          fill="#9CA3AF"
          fontFamily="monospace"
        >
          {shape?.barre ?? 1}fr
        </text>

        {/* 横按弧线 */}
        {shape?.barre ? (
          <rect
            x={fretX(0) - 4}
            y={fretY(shape.barre) - fretGap / 2 + 2}
            width={fretAreaWidth + 8}
            height={fretGap - 4}
            rx={fretGap / 2}
            fill="#3B82F6"
            opacity={0.25}
          />
        ) : null}

        {/* 手指按弦 */}
        {shape &&
          shape.positions.map((pos, strIdx) => {
            if (pos === -1) return null; // 不用此弦
            const cx = fretX(strIdx);
            const cy = fretY(pos) - fretGap / 2;
            const color = shape.finger?.[strIdx]
              ? fingerColors[shape.finger[strIdx]]
              : '#3B82F6';
            const label = shape.finger?.[strIdx]
              ? fingerLabels[shape.finger[strIdx]]
              : '';
            return (
              <g key={`dot-${strIdx}`}>
                <circle cx={cx} cy={cy} r={7} fill={color} opacity={0.9} />
                {label && (
                  <text
                    x={cx}
                    y={cy + 1}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="8"
                    fontWeight="bold"
                    fill="white"
                    fontFamily="monospace"
                  >
                    {label}
                  </text>
                )}
              </g>
            );
          })}

        {/* 空弦标记（圆圈） */}
        {shape &&
          shape.positions.map((pos, strIdx) => {
            if (pos !== 0) return null;
            return (
              <circle
                key={`open-${strIdx}`}
                cx={fretX(strIdx)}
                cy={fretY(0) - fretGap / 2}
                r={5}
                fill="none"
                stroke="#9CA3AF"
                strokeWidth={1.5}
              />
            );
          })}

        {/* X 标记（不用的弦） */}
        {shape &&
          shape.positions.map((pos, strIdx) => {
            if (pos !== -1) return null;
            return (
              <text
                key={`x-${strIdx}`}
                x={fretX(strIdx)}
                y={marginTop - 2}
                textAnchor="middle"
                fontSize="10"
                fontWeight="bold"
                fill="#9CA3AF"
              >
                ✕
              </text>
            );
          })}
      </svg>

      {/* 和弦名标注 */}
      <div className="text-xs font-bold text-gray-600 dark:text-gray-300 mt-1 font-mono">
        {chordName}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// 子组件：单个和弦块
// ---------------------------------------------------------------------------
interface ChordBlockProps {
  chord: string;
  start: number;
  end: number;
  isPlaying: boolean;
  onPlay: () => void;
}

const ChordBlock: React.FC<ChordBlockProps> = ({
  chord,
  start,
  end,
  isPlaying,
  onPlay,
}) => {
  const [hovered, setHovered] = useState(false);
  const width = Math.max(64, (end - start) * 55);

  return (
    <div
      className="relative flex-shrink-0 flex flex-col items-center justify-center rounded-xl cursor-pointer transition-all duration-150 select-none"
      style={{ minWidth: `${width}px` }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onPlay}
      title={`${chord}  ${start.toFixed(1)}s – ${end.toFixed(1)}s`}
    >
      <div
        className={`
          w-full flex flex-col items-center justify-center rounded-xl border-2 transition-all
          ${isPlaying
            ? 'bg-blue-500 border-blue-500 shadow-lg shadow-blue-500/40 scale-105'
            : hovered
            ? 'bg-blue-50 dark:bg-blue-950/40 border-blue-400 shadow-md'
            : 'bg-white dark:bg-gray-700 border-gray-200 dark:border-gray-600 hover:border-blue-300'
          }
        `}
        style={{ height: '80px' }}
      >
        <span
          className={`
            text-lg font-bold transition-colors
            ${isPlaying
              ? 'text-white'
              : hovered
              ? 'text-blue-600 dark:text-blue-400'
              : 'text-gray-800 dark:text-white'}
          `}
        >
          {chord}
        </span>
        <span
          className={`
            text-xs mt-1 transition-colors
            ${isPlaying ? 'text-blue-100' : 'text-gray-400'}
          `}
        >
          {start.toFixed(1)}s
        </span>
      </div>

      {/* 悬停：显示吉他指法图 */}
      {hovered && CHORD_SHAPES[chord] && (
        <div
          className="absolute -top-1 left-1/2 -translate-x-1/2 translate-y-[-100%] z-20
            bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700
            p-3 pointer-events-none animate-in fade-in zoom-in-95 duration-150"
        >
          <GuitarDiagram chordName={chord} width={110} height={130} />
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// 主组件
// ---------------------------------------------------------------------------
export const ChordViewer: React.FC<ChordViewerProps> = ({
  result,
  audioUrl,
  className = '',
}) => {
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
    if (playing) { audio.pause(); setPlaying(false); }
    else { audio.play().then(() => setPlaying(true)).catch(() => {}); }
  }, [playing]);

  const handleChordClick = useCallback(
    (start: number) => {
      const audio = audioRef.current;
      if (!audio) return;
      audio.currentTime = start;
      if (!playing) { audio.play().then(() => setPlaying(true)).catch(() => {}); }
    },
    [playing]
  );

  // 当前活跃和弦 index
  const activeIndex = chords.findIndex(
    (c, i) =>
      currentTime >= c.start &&
      (i === chords.length - 1 || currentTime < chords[i + 1].start)
  );

  // 和弦进行文字（首字母大写）
  const chordProgression = chords
    .map((c) => c.chord.replace(/m$/, 'ₘ').replace('m7', 'ₘ⁷').replace('maj7', 'M⁷').replace('7', '⁷').replace('sus', 'ₛ'))
    .filter((v, i, a) => v !== a[i - 1])
    .slice(0, 12)
    .join(' → ');

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 顶部信息栏 */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
          <Music className="w-4 h-4 text-blue-500" />
          <span className="font-semibold">{bpm} BPM</span>
        </div>
        <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
          <Clock className="w-4 h-4 text-blue-500" />
          <span>{time_signature}</span>
        </div>
        <div className="text-xs text-gray-400">
          共识别 {chords.length} 个和弦
        </div>

        {/* 和弦进行 */}
        {chordProgression && (
          <div className="hidden md:flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 ml-auto">
            <span className="font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded-lg">
              {chordProgression}{chords.length > 12 ? '…' : ''}
            </span>
          </div>
        )}

        {/* 播放按钮 */}
        {audioUrl && (
          <button
            onClick={togglePlay}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors active:scale-95"
          >
            {playing
              ? <><Pause className="w-4 h-4" /> 暂停</>
              : <><Play className="w-4 h-4" /> 播放预览</>}
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
              isPlaying={i === activeIndex && playing}
              onPlay={() => handleChordClick(chord.start)}
            />
          ))}
        </div>
      </div>

      {/* 播放进度条 */}
      {audioUrl && (
        <div className="relative h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className="absolute left-0 top-0 h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all duration-200"
            style={{
              width: audioRef.current
                ? `${(currentTime / (audioRef.current.duration || 1)) * 100}%`
                : '0%',
            }}
          />
        </div>
      )}

      {/* 悬停提示 */}
      <p className="text-xs text-gray-400">
        鼠标悬停和弦块查看指法图 · 点击跳转到对应时间点
      </p>
    </div>
  );
};

export default ChordViewer;
