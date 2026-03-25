/**
 * ProgressBar — 处理进度条
 * ================================
 * 展示音频处理各阶段实时进度，参考 Audio Jam 风格。
 */

import React from 'react';
import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react';

export interface Stage {
  /** 阶段唯一标识 */
  id: string;
  /** 阶段中文名称 */
  label: string;
  /** 是否已完成 */
  done: boolean;
  /** 当前是否活跃（正在执行） */
  active: boolean;
  /** 是否出错 */
  error?: boolean;
}

interface ProgressBarProps {
  /** 总进度 0-100 */
  progress: number;
  /** 当前处理阶段描述 */
  stageLabel?: string;
  /** 各阶段列表 */
  stages: Stage[];
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  stageLabel,
  stages,
  className = '',
}) => {
  return (
    <div className={`w-full max-w-lg mx-auto space-y-5 ${className}`}>

      {/* 顶部：百分比 + 当前阶段 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {progress >= 100 ? (
            <CheckCircle2 className="w-5 h-5 text-green-500" />
          ) : (
            <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
          )}
          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
            {progress >= 100 ? '处理完成' : stageLabel ?? '正在处理…'}
          </span>
        </div>
        <span className="text-sm font-mono text-gray-400">{Math.min(100, Math.round(progress))}%</span>
      </div>

      {/* 主进度条 */}
      <div className="relative h-2.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
        {/* 动画光效 */}
        <div
          className="absolute top-0 h-full w-8 bg-white/30 rounded-full blur-sm animate-pulse"
          style={{ left: `calc(${progress}% - 16px)`, opacity: progress < 100 ? 1 : 0 }}
        />
      </div>

      {/* 阶段列表 */}
      {stages.length > 0 && (
        <div className="space-y-2">
          {stages.map((stage, idx) => (
            <div key={stage.id} className="flex items-center gap-3">
              {/* 图标 */}
              <div className="flex-shrink-0">
                {stage.error ? (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                ) : stage.done ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : stage.active ? (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                ) : (
                  <Circle className="w-4 h-4 text-gray-300 dark:text-gray-600" />
                )}
              </div>

              {/* 标签 */}
              <span
                className={`text-sm ${
                  stage.done
                    ? 'text-green-600 dark:text-green-400'
                    : stage.active
                    ? 'text-blue-600 dark:text-blue-400 font-medium'
                    : stage.error
                    ? 'text-red-500'
                    : 'text-gray-400 dark:text-gray-500'
                }`}
              >
                {stage.label}
              </span>

              {/* 连接线（除最后一个） */}
              {idx < stages.length - 1 && (
                <div
                  className={`flex-1 h-px ml-2 ${
                    stage.done ? 'bg-green-400' : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProgressBar;
