/**
 * Result — 结果预览页面
 * ================================
 * 展示分析结果（和弦/BPM/乐谱），支持多格式导出。
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Github, FileMusic, Loader2,
  AlertCircle, RefreshCw, Music2,
} from 'lucide-react';
import { api, AnalysisResult } from '../api/client';
import ChordViewer from '../components/ChordViewer';
import GTAViewer from '../components/GTAViewer';
import { ResultSkeleton } from '../components/LoadingSkeleton';

const EXPORT_OPTIONS = [
  { format: 'pdf' as const, label: 'PDF 乐谱', suffix: '.pdf', icon: '📄' },
  { format: 'gta' as const, label: 'GTA 文本谱', suffix: '.txt', icon: '🎸' },
  { format: 'gp' as const, label: 'Guitar Pro', suffix: '.gp', icon: '🎵' },
  { format: 'midi' as const, label: 'MIDI', suffix: '.mid', icon: '🎹' },
];

function downloadBlob(url: string, filename: string) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

/**
 * 根据分析结果生成 GTA 格式文本谱
 */
function buildGTAText(result: AnalysisResult): string {
  const { bpm, time_signature, chords } = result;
  const lines: string[] = [];

  lines.push('# AI Guitar Tab Transcriber — 自动生成');
  lines.push(`Tempo: ${bpm}`);
  lines.push(`TimeSignature: ${time_signature}`);
  lines.push('Legend: 0=空弦 1-24=品位 h=击弦 p=勾弦 b=推弦 /=上滑 \\\\=下滑');
  lines.push('━'.repeat(56));
  lines.push('');

  // Guitar 六线谱轨
  lines.push('[ GUITAR ]  (e B G D A E — 细弦到粗弦)');
  lines.push('━'.repeat(56));

  // 生成简单 TAB 格（每4个和弦为一小节）
  for (let bar = 0; bar < Math.ceil(chords.length / 4); bar++) {
    const slice = chords.slice(bar * 4, bar * 4 + 4);
    if (slice.length === 0) break;

    // 小节头
    lines.push(`[${bar + 1}] ` + slice.map(c => c.chord.padEnd(5)).join('|'));

    // 六线谱占位行（每和弦占4个半拍 '-'）
    const tabRows = ['e|', 'B|', 'G|', 'D|', 'A|', 'E|'];
    for (const chord of slice) {
      // 和弦名标注行（叠加在 TAB 上方）
      const beatWidth = '----'; // 每个半拍4字符
      tabRows[0] += chord.chord.padEnd(beatWidth.length + 1, '-').substring(0, beatWidth.length + 1);
      tabRows[1] += beatWidth;
      tabRows[2] += beatWidth;
      tabRows[3] += beatWidth;
      tabRows[4] += beatWidth;
      tabRows[5] += beatWidth;
    }
    // 小节线分隔
    for (const row of tabRows) {
      lines.push(row + '|');
    }
    lines.push('');
  }

  lines.push('━'.repeat(56));
  lines.push('');
  lines.push(`共识别 ${chords.length} 个和弦 | BPM: ${bpm} | 拍号: ${time_signature}`);
  lines.push('');
  lines.push('# 提示：数字表示品位，- 表示空拍，| 为小节分隔线');

  return lines.join('\n');
}

type LoadState = 'loading' | 'done' | 'error';

const Result: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);
  const [showGTA, setShowGTA] = useState(false);

  // 加载分析结果
  useEffect(() => {
    if (!taskId) return;
    api.getResult(taskId)
      .then((data) => {
        setResult(data);
        setLoadState('done');
      })
      .catch((err: any) => {
        setErrorMsg(err?.message ?? '加载失败，请检查网络后重试');
        setLoadState('error');
      });
  }, [taskId]);

  // 导出处理
  const handleExport = useCallback(async (format: 'pdf' | 'gta' | 'gp' | 'midi') => {
    if (!taskId) return;
    setExporting(format);
    try {
      const blobUrl = await api.downloadExport(taskId, format);
      const ext = format === 'gta' ? 'txt' : format;
      downloadBlob(blobUrl, `guitar-tab-${taskId}.${ext}`);
    } catch (err: any) {
      alert(`导出失败: ${err?.message ?? '请稍后重试'}`);
    } finally {
      setExporting(null);
    }
  }, [taskId]);

  // 生成 GTA 文本（用于 GTAViewer）
  const gtaText = result ? buildGTAText(result) : '';

  // ---------------------------------------------------------------------------
  // 渲染
  // ---------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">

      {/* 顶部导航 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            重新上传
          </button>

          <div className="flex items-center gap-2">
            <Music2 className="w-6 h-6 text-blue-500" />
            <span className="font-bold text-gray-800 dark:text-white">AI Guitar Tab</span>
          </div>

          <a
            href="https://github.com/YuruiZhu9/AI-music-score-featch"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <Github className="w-5 h-5" />
          </a>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8 space-y-8">

        {/* ── 加载中骨架屏 ──────────────────────────────────────── */}
        {loadState === 'loading' && <ResultSkeleton />}

        {/* ── 错误状态（可重试）──────────────────────────────────── */}
        {loadState === 'error' && (
          <div className="flex flex-col items-center justify-center py-28 gap-4">
            <AlertCircle className="w-12 h-12 text-red-400" />
            <p className="text-red-500 font-medium text-center max-w-sm">{errorMsg ?? '加载失败，请检查网络后重试'}</p>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  if (!taskId) return;
                  setLoadState('loading');
                  setErrorMsg(null);
                  api.getResult(taskId)
                    .then((data) => { setResult(data); setLoadState('done'); })
                    .catch((err: any) => { setErrorMsg(err?.message ?? '加载失败'); setLoadState('error'); });
                }}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                重试
              </button>
              <button
                onClick={() => navigate('/')}
                className="px-5 py-2.5 rounded-xl bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors"
              >
                返回上传页
              </button>
            </div>
          </div>
        )}

        {/* ── 结果展示 ────────────────────────────────────────────── */}
        {loadState === 'done' && result && (
          <>
            {/* 结果概览 */}
            <div className="space-y-1">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                🎸 扒谱完成！
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {result.bpm} BPM
                <span className="mx-2">·</span>
                {result.time_signature} 拍
                <span className="mx-2">·</span>
                {result.chords.length} 个和弦
                <span className="mx-2">·</span>
                {result.segments.length} 个音符
              </p>
            </div>

            {/* 和弦时间轴 */}
            <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <div className="flex items-center gap-2 mb-4">
                <FileMusic className="w-5 h-5 text-blue-500" />
                <h2 className="text-base font-semibold text-gray-700 dark:text-gray-200">
                  和弦时间轴
                </h2>
              </div>
              <ChordViewer result={result} />
            </section>

            {/* 六线谱预览（GTAViewer） */}
            <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Music2 className="w-5 h-5 text-blue-500" />
                  <h2 className="text-base font-semibold text-gray-700 dark:text-gray-200">
                    六线谱预览
                  </h2>
                </div>
                <button
                  onClick={() => setShowGTA((v) => !v)}
                  className="text-sm text-blue-500 hover:text-blue-600 hover:underline transition-colors"
                >
                  {showGTA ? '收起 GTA 文本谱' : '展开 GTA 文本谱'}
                </button>
              </div>

              {showGTA && (
                <GTAViewer
                  gtaText={gtaText}
                  bpm={result.bpm}
                  timeSignature={result.time_signature}
                />
              )}

              {!showGTA && (
                <div className="text-center py-8 text-gray-400 dark:text-gray-500">
                  <p className="text-sm">点击上方"展开 GTA 文本谱"预览乐谱</p>
                  <p className="text-xs mt-1">GTA 格式兼容 Guitar Pro，可下载后导入软件</p>
                </div>
              )}
            </section>

            {/* 和弦进程速览 */}
            <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <h2 className="text-base font-semibold text-gray-700 dark:text-gray-200 mb-4">
                和弦进程
              </h2>
              <div className="flex flex-wrap gap-2">
                {result.chords.map((chord, i) => (
                  <span
                    key={`${chord.chord}-${i}`}
                    className="px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-200"
                  >
                    {chord.chord}
                  </span>
                ))}
              </div>
            </section>

            {/* 多格式导出 */}
            <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
              <h2 className="text-base font-semibold text-gray-700 dark:text-gray-200 mb-4">
                导出乐谱
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {EXPORT_OPTIONS.map(({ format, label, suffix, icon }) => (
                  <button
                    key={format}
                    onClick={() => handleExport(format)}
                    disabled={!!exporting}
                    className="flex flex-col items-center gap-2 p-4 rounded-xl border-2 border-gray-200 dark:border-gray-600 hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {exporting === format ? (
                      <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                    ) : (
                      <span className="text-2xl">{icon}</span>
                    )}
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{label}</span>
                    <span className="text-xs text-gray-400">{suffix}</span>
                  </button>
                ))}
              </div>
            </section>

            {/* 底部操作 */}
            <div className="flex justify-center">
              <button
                onClick={() => navigate('/')}
                className="text-sm text-gray-400 hover:text-blue-500 transition-colors"
              >
                分析另一首 →
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default Result;
