/**
 * 进度条组件 — 显示任务处理阶段和进度
 * ======================================
 * Props:
 *   progress: 0.0 ~ 1.0
 *   stage: 当前阶段描述文字
 */

import React from "react";

interface ProgressBarProps {
  progress: number;      // 0.0 ~ 1.0
  stage: string;          // 阶段描述，如 "正在识别和弦..."
}

const STAGES = [
  "等待上传",
  "文件已接收",
  "正在分离音轨...",
  "音轨分离完成",
  "正在检测音高...",
  "音高检测完成",
  "正在识别和弦...",
  "和弦识别完成",
  "正在分析节拍...",
  "节拍分析完成",
  "正在生成乐谱...",
  "完成！",
];

const STAGE_INDEX_MAP: Record<string, number> = {
  "等待上传": 0,
  "文件已接收": 1,
  "正在分离音轨...": 2,
  "音轨分离完成": 3,
  "正在检测音高...": 4,
  "音高检测完成": 5,
  "正在识别和弦...": 6,
  "和弦识别完成": 7,
  "正在分析节拍...": 8,
  "节拍分析完成": 9,
  "正在生成乐谱...": 10,
  "完成！": 11,
};

export const ProgressBar: React.FC<ProgressBarProps> = ({ progress, stage }) => {
  const currentIndex = STAGE_INDEX_MAP[stage] ?? 0;
  const totalStages = STAGES.length - 1;
  const percentage = Math.min(100, Math.round(progress * 100));

  // 阶段指示器
  const visibleStages = STAGES.filter((_, i) => {
    // 只显示当前阶段附近的状态
    return Math.abs(i - currentIndex) <= 2 || i === 0 || i === totalStages;
  });

  return (
    <div className="w-full max-w-lg mx-auto p-6 bg-white rounded-2xl shadow-md">
      {/* 标题 */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <span className="text-2xl">🎸</span>
          正在扒谱中...
        </h2>
        <span className="text-sm font-mono text-blue-600 font-bold">{percentage}%</span>
      </div>

      {/* 进度条 */}
      <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-4">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* 阶段描述 */}
      <p className="text-center text-gray-600 mb-6 text-sm">
        {stage}
      </p>

      {/* 阶段指示器 */}
      <div className="space-y-2">
        {STAGES.map((s, i) => {
          const isActive = i === currentIndex;
          const isDone = i < currentIndex;
          const isVisible = Math.abs(i - currentIndex) <= 2 || i === 0 || i === totalStages;

          if (!isVisible) return null;

          return (
            <div key={s} className="flex items-center gap-3 text-sm">
              {/* 状态图标 */}
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0
                  ${isDone ? "bg-green-500 text-white" : ""}
                  ${isActive ? "bg-blue-500 text-white animate-pulse" : ""}
                  ${!isDone && !isActive ? "bg-gray-200 text-gray-400" : ""}
                `}
              >
                {isDone ? "✓" : isActive ? "●" : "○"}
              </div>
              {/* 阶段文字 */}
              <span
                className={`transition-colors ${
                  isActive ? "text-blue-600 font-semibold" : isDone ? "text-green-600" : "text-gray-400"
                }`}
              >
                {s}
              </span>
            </div>
          );
        })}
      </div>

      {/* 预计剩余时间（估算） */}
      {progress > 0 && progress < 1 && (
        <p className="mt-4 text-xs text-gray-400 text-center">
          预计剩余时间约 {Math.max(1, Math.round((1 - progress) * 3))} 分钟
        </p>
      )}
    </div>
  );
};
