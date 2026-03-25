/**
 * GTAViewer — GTA 文本谱预览组件
 * ====================================
 * 展示 ASCII 格式六线谱，支持 Guitar 六线 + Bass 四线双轨显示。
 * 按小节自动换行着色，支持展开/折叠。
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Music2 } from 'lucide-react';

interface GTAViewerProps {
  /** GTA 文本谱内容（ASCII 六线谱） */
  gtaText: string;
  /** 可选：BPM 标注 */
  bpm?: number;
  /** 可选：时间签名 */
  timeSignature?: string;
  className?: string;
}

// ---------------------------------------------------------------------------
// 工具函数
// ---------------------------------------------------------------------------

/** 判断行是否为 TAB 行 */
function isTabLine(line: string): boolean {
  const prefixes = ['e|', 'B|', 'G|', 'D|', 'A|', 'E|', 'g|', 'd|', 'a|'];
  return prefixes.some(p => line.trimStart().startsWith(p));
}

/** 判断行是否为轨名标题 */
function isTrackHeader(line: string): boolean {
  return line.includes('[ GUITAR ]') || line.includes('[ BASS ]');
}

/** 判断行是否为图例/说明 */
function isLegendLine(line: string): boolean {
  return (
    line.startsWith('# ') ||
    line.startsWith('#') ||
    line.includes('Legend') ||
    line.includes('数字') ||
    line.includes('Technique')
  );
}

/** 分割 GTA 文本为可渲染的行块 */
function parseGTALines(text: string): Array<{ type: string; content: string }> {
  const lines = text.split('\n');
  const blocks: Array<{ type: string; content: string }> = [];

  for (const line of lines) {
    if (!line.trim()) {
      blocks.push({ type: 'empty', content: line });
    } else if (isTrackHeader(line)) {
      blocks.push({ type: 'header', content: line });
    } else if (isTabLine(line)) {
      blocks.push({ type: 'tab', content: line });
    } else if (isLegendLine(line)) {
      blocks.push({ type: 'legend', content: line });
    } else if (line.startsWith('━') || line.startsWith('─') || line.startsWith('=')) {
      blocks.push({ type: 'separator', content: line });
    } else if (line.startsWith('Chord:') || line.startsWith('Tempo:')) {
      blocks.push({ type: 'meta', content: line });
    } else if (line.includes('🎸') || line.includes('BASS')) {
      blocks.push({ type: 'title', content: line });
    } else {
      blocks.push({ type: 'text', content: line });
    }
  }

  return blocks;
}

// ---------------------------------------------------------------------------
// 子组件：单行渲染
// ---------------------------------------------------------------------------

function GTALine({ type, content }: { type: string; content: string }) {
  switch (type) {
    case 'header':
      return (
        <div className="bg-blue-50 dark:bg-blue-950/40 px-3 py-1.5 rounded-lg">
          <span className="text-sm font-bold text-blue-700 dark:text-blue-300 font-mono">
            {content}
          </span>
        </div>
      );
    case 'tab':
      return (
        <div className="font-mono text-sm leading-6 tracking-tight text-gray-800 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
          {content}
        </div>
      );
    case 'legend':
      return (
        <div className="font-mono text-xs text-gray-400 dark:text-gray-500 italic pl-2">
          {content}
        </div>
      );
    case 'separator':
      return (
        <div className="text-gray-300 dark:text-gray-600 font-mono text-xs select-none">
          {content}
        </div>
      );
    case 'meta':
      return (
        <div className="text-sm font-semibold text-amber-700 dark:text-amber-400">
          {content}
        </div>
      );
    case 'title':
      return (
        <div className="text-base font-bold text-gray-900 dark:text-white">
          {content}
        </div>
      );
    case 'empty':
      return <div className="h-1" />;
    default:
      return (
        <div className="text-sm text-gray-600 dark:text-gray-300">
          {content}
        </div>
      );
  }
}

// ---------------------------------------------------------------------------
// 主组件
// ---------------------------------------------------------------------------

const GTAViewer: React.FC<GTAViewerProps> = ({
  gtaText,
  bpm,
  timeSignature,
  className = '',
}) => {
  const [expanded, setExpanded] = useState(false);
  const lines = parseGTALines(gtaText);
  // 默认折叠超过 40 行的内容
  const PREVIEW_LINES = 40;
  const visibleLines = expanded ? lines : lines.slice(0, PREVIEW_LINES);

  return (
    <div className={`space-y-3 ${className}`}>
      {/* 头部信息栏 */}
      {(bpm || timeSignature) && (
        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          {bpm && (
            <span className="flex items-center gap-1">
              <Music2 className="w-3.5 h-3.5" />
              {bpm} BPM
            </span>
          )}
          {timeSignature && (
            <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 font-mono">
              {timeSignature}
            </span>
          )}
          <span className="ml-auto text-gray-400">
            {lines.filter(l => l.type === 'tab').length} 行TAB
          </span>
        </div>
      )}

      {/* GTA 文本区域 */}
      <div className="relative rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* 轨道颜色条 */}
        <div className="flex">
          <div className="flex-1 h-1 bg-gradient-to-r from-blue-500 to-blue-400" />
          <div className="w-8 h-1 bg-gradient-to-r from-amber-500 to-amber-400" />
        </div>

        {/* 内容 */}
        <div className="bg-gray-50 dark:bg-gray-900/50 p-4 overflow-x-auto">
          <pre className="whitespace-pre text-xs font-mono leading-relaxed">
            {visibleLines.map((block, i) => (
              <GTALine key={i} type={block.type} content={block.content} />
            ))}
          </pre>
        </div>

        {/* 折叠覆盖层 */}
        {!expanded && lines.length > PREVIEW_LINES && (
          <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-gray-50 dark:from-gray-900/80 to-transparent pointer-events-none" />
        )}
      </div>

      {/* 展开/折叠按钮 */}
      {lines.length > PREVIEW_LINES && (
        <button
          onClick={() => setExpanded(v => !v)}
          className="flex items-center gap-1.5 text-sm text-blue-500 hover:text-blue-600 transition-colors mx-auto"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              收起
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              展开全部 {lines.length} 行
            </>
          )}
        </button>
      )}

      {/* 使用说明 */}
      {expanded && (
        <div className="text-xs text-gray-400 dark:text-gray-500 space-y-1 pl-1">
          <p>📖 <strong>阅读方法：</strong>从左到右为时间推进，竖线 | 为小节分隔</p>
          <p>🎸 Guitar：e|B|G|D|A|E（细→粗弦）| 🎸 Bass：G|D|A|E（细→粗弦）</p>
          <p>
            记号：<span className="font-mono">数字</span>=品位
            <span className="mx-1">|</span>
            <span className="font-mono">h</span>=击弦
            <span className="mx-1">|</span>
            <span className="font-mono">p</span>=勾弦
            <span className="mx-1">|</span>
            <span className="font-mono">b</span>=推弦
            <span className="mx-1">|</span>
            <span className="font-mono">/</span>=上滑
            <span className="mx-1">|</span>
            <span className="font-mono">\</span>=下滑
          </p>
        </div>
      )}
    </div>
  );
};

export default GTAViewer;
