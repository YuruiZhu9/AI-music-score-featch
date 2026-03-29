/**
 * LoadingSkeleton — 骨架屏加载占位
 * ================================
 * 在数据加载时显示骨架占位动画，提升感知加载速度。
 */

import React from 'react';

/** 单行骨架占位块 */
const SkeletonLine: React.FC<{ width?: string; height?: string; className?: string }> = ({
  width = '100%',
  height = '1rem',
  className = '',
}) => (
  <div
    className={`animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700 ${className}`}
    style={{ width, height }}
  />
);

/** 和弦块骨架 */
const ChordBlockSkeleton: React.FC = () => (
  <div className="flex-shrink-0 flex flex-col items-center justify-center rounded-xl border border-gray-200 dark:border-gray-600"
    style={{ minWidth: '80px', height: '80px' }}>
    <SkeletonLine width="48px" height="20px" className="mb-2" />
    <SkeletonLine width="36px" height="12px" />
  </div>
);

/** Result 页面完整骨架屏 */
export const ResultSkeleton: React.FC = () => (
  <div className="space-y-8 animate-pulse">

    {/* 概览标题 */}
    <div className="space-y-1">
      <SkeletonLine width="200px" height="2rem" />
      <SkeletonLine width="320px" height="1rem" />
    </div>

    {/* 和弦时间轴 */}
    <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 space-y-4">
      <SkeletonLine width="120px" height="1.25rem" />
      <div className="flex gap-2 overflow-hidden">
        {Array.from({ length: 12 }).map((_, i) => (
          <ChordBlockSkeleton key={i} />
        ))}
      </div>
    </div>

    {/* 六线谱预览 */}
    <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 space-y-4">
      <SkeletonLine width="140px" height="1.25rem" />
      <div className="h-40 bg-gray-100 dark:bg-gray-700 rounded-xl" />
    </div>

    {/* 和弦进程 */}
    <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 space-y-4">
      <SkeletonLine width="100px" height="1.25rem" />
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: 16 }).map((_, i) => (
          <SkeletonLine key={i} width="48px" height="32px" className="rounded-xl" />
        ))}
      </div>
    </div>

    {/* 导出按钮 */}
    <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
      <SkeletonLine width="100px" height="1.25rem" className="mb-4" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonLine key={i} height="80px" className="rounded-xl" />
        ))}
      </div>
    </div>
  </div>
);

export default ResultSkeleton;
