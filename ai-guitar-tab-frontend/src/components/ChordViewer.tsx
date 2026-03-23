/**
 * 和弦时间轴组件
 * ===================
 * 可视化展示和弦进行的时间线，支持悬停查看详情。
 */
import { useMemo } from "react";
import type { ChordEvent } from "../api/client";

interface ChordViewerProps {
  chords: ChordEvent[];
  duration: number;
  onChordClick?: (chord: ChordEvent) => void;
}

// 默认导出，供 Result.tsx 直接 import ChordViewer 使用
export default function ChordViewer(props: ChordViewerProps) {
  const { chords, duration, onChordClick } = props;
  const totalDuration = duration || 1;

  // 合并重复和弦
  const uniqueChords = useMemo(() => {
    if (!chords.length) return [];
    const result: ChordEvent[] = [chords[0]];
    for (let i = 1; i < chords.length; i++) {
      if (chords[i].chord !== result[result.length - 1].chord) {
        result.push(chords[i]);
      }
    }
    return result;
  }, [chords]);

  // 为每个和弦分配颜色
  const chordColors = useMemo(() => {
    const colorMap: Record<string, string> = {};
    const palette = [
      "bg-blue-500", "bg-purple-500", "bg-pink-500",
      "bg-green-500", "bg-orange-500", "bg-teal-500",
      "bg-red-500", "bg-indigo-500", "bg-yellow-500",
    ];
    let colorIndex = 0;
    for (const c of uniqueChords) {
      if (!colorMap[c.chord]) {
        colorMap[c.chord] = palette[colorIndex % palette.length];
        colorIndex++;
      }
    }
    return colorMap;
  }, [uniqueChords]);

  const formatTime = (sec: number): string => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  if (uniqueChords.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8 text-sm">
        暂无和弦数据
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* 和弦名称序列 */}
      <div className="flex flex-wrap gap-2">
        {uniqueChords.map((chord, i) => (
          <button
            key={`${chord.chord}-${i}`}
            onClick={() => onChordClick?.(chord)}
            className={`${chordColors[chord.chord]} text-white px-3 py-1.5 rounded-xl
              text-sm font-semibold shadow-sm hover:shadow-md transition-all
              hover:scale-105 cursor-pointer`}
            title={`${chord.start.toFixed(1)}s - ${chord.end.toFixed(1)}s`}
          >
            {chord.chord}
          </button>
        ))}
      </div>

      {/* 时间线条 */}
      <div className="relative h-10 bg-gray-100 rounded-lg overflow-hidden">
        {/* 时间刻度 */}
        <div className="absolute inset-0 flex">
          {[0, 0.25, 0.5, 0.75].map((ratio) => (
            <div
              key={ratio}
              className="absolute top-0 bottom-0 border-l border-gray-300"
              style={{ left: `${ratio * 100}%` }}
            >
              <span className="absolute top-0 -translate-y-5 text-xs text-gray-400">
                {formatTime(totalDuration * ratio)}
              </span>
            </div>
          ))}
        </div>

        {/* 和弦块 */}
        <div className="absolute inset-0 flex">
          {uniqueChords.map((chord, i) => {
            const left = (chord.start / totalDuration) * 100;
            const width = ((chord.end - chord.start) / totalDuration) * 100;
            return (
              <div
                key={`${chord.chord}-bar-${i}`}
                className={`absolute top-1 bottom-1 ${chordColors[chord.chord]} opacity-80
                  hover:opacity-100 transition-opacity cursor-pointer flex items-center justify-center`}
                style={{ left: `${left}%`, width: `${Math.max(width, 1)}%` }}
                onClick={() => onChordClick?.(chord)}
                title={`${chord.chord} (${formatTime(chord.start)} - ${formatTime(chord.end)})`}
              >
                {width > 8 && (
                  <span className="text-white text-xs font-bold truncate px-1">
                    {chord.chord}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 时间轴标签 */}
      <div className="flex justify-between text-xs text-gray-400">
        <span>0:00</span>
        <span>{formatTime(totalDuration)}</span>
      </div>
    </div>
  );
}
