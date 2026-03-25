/**
 * Result — 结果预览页面
 * 分析结果展示 + 多格式导出
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Download, FileText, Music2, Loader2,
  AlertCircle, Github, Play, Pause,
} from 'lucide-react';
import { api, AnalysisResult } from '../api/client';
import ChordViewer from '../components/ChordViewer';

const EXPORT_OPTIONS = [
  { format: 'pdf' as const, label: 'PDF 乐谱', suffix: '.pdf' },
  { format: 'gta' as const, label: 'GTA 文本谱', suffix: '.txt' },
  { format: 'gp' as const, label: 'Guitar Pro', suffix: '.gp' },
  { format: 'midi' as const, label: 'MIDI', suffix: '.mid' },
];

function downloadBlob(url: string, filename: string) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function renderGTA(result: AnalysisResult): string[] {
  const lines: string[] = [];
  const { bpm, time_signature, chords } = result;
  lines.push(`AI Guitar Tab — Generated`);
  lines.push(`BPM: ${bpm}  |  Time: ${time_signature}`);
  lines.push('─'.repeat(50));
  lines.push('');
  // 六线谱 ASCII 表头
  ['e|---', 'B|---', 'G|---', 'D|---', 'A|---', 'E|---'].forEach(l => lines.push(l));
  lines.push('');
  // 和弦进程（每4拍一块）
  const measures: string[] = [];
  for (let i = 0; i < chords.length; i++) {
    const ch = chords[i];
    if (i % 4 === 0) measures.push(`[${Math.floor(i / 4) + 1}] `);
    measures.push(`${ch.chord.padEnd(4)}`);
    if ((i + 1) % 4 === 0) {
      lines.push(measures.join('  '));
      measures.length = 0;
    }
  }
  if (measures.length) lines.push(measures.join('  '));
  lines.push('');
  lines.push('─'.repeat(50));
  lines.push(`共 ${chords.length} 个和弦`);
  return lines;
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

  useEffect(() => {
    if (!taskId) return;
    api.getResult(taskId)
      .then(data => { setResult(data); setLoadState('done'); })
      .catch((err: any) => { setErrorMsg(err?.message ?? '加载失败'); setLoadState('error'); });
  }, [taskId]);

  const handleExport = useCallback(async (format: 'pdf' | 'gta' | 'gp' | 'midi') => {
    if (!taskId) return;
    setExporting(format);
    try {
      const blobUrl = await api.downloadExport(taskId, format);
      downloadBlob(blobUrl, `guitar-tab-${taskId}.${format === 'gta' ? 'txt' : format}`);
    } catch (err: any) { alert(`导出失败: ${err?.message}`); }
    finally { setExporting(null); }
  }, [taskId]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      {/* 顶部导航 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate('/')} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition-colors">
            <ArrowLeft className="w-4 h-4" />重新上传
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <Music2 className="w-6 h-6 text-blue-500" />
            <span className="font-bold text-gray-800 dark:text-white">AI Guitar Tab</span>
          </div>
          <div className="flex-1" />
          <a href="https://github.com/YuruiZhu9/AI-music-score-featch" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <Github className="w-5 h-5" />
          </a>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8 space-y-8">

        {/* 加载中 */}
        {loadState === 'loading' && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
            <p className="text-gray-500">正在加载分析结果…</p>
          </div>
        )}

        {/* 错误 */}
        {loadState === 'error' && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <AlertCircle className="w-10 h-10 text-red-400" />
            <p className="text-red-500">{errorMsg ?? '加载失败'}</p>
            <button onClick={() => navigate('/')} className="px-4 py-2 rounded-xl bg-blue-500 text-white text-sm hover:bg-blue-600 transition-colors">返回上传</button>
          </div>
        )}

        {/* 结果 */}
        {loadState === 'done' && result && (
          <>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">分析结果</h1>
              <p className="text-sm text-gray-500 mt-1">{result.bpm} BPM · {result.chords.length} 个和弦 · {result.time_signature} 拍</p>
            </div>

            {/* 和弦时间轴 */}
            <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
              <h2 className="text-base font-semibold text-gray-700 dark:text-gray-200 mb-4">和弦时间轴</h2>
              <ChordViewer result={result} />
            </section>

            {/* 六线谱预览 */}
            <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-gray-700 dark:text-gray-200">六线谱预览</h2>
                <button onClick={() => setShowGTA(v => !v)} className="text-sm text-blue-500 hover:underline">
                  {showGTA ? '收起' : '展开'} GTA 文本谱
                </button>
              </div>
              {showGTA && (
                <pre className="font-mono text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-900 rounded-xl p-4 overflow-x-auto leading-relaxed">
                  {renderGTA(result).join('\n')}
                </pre>
              )}
            </section>

            {/* 导出 */}
            <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
              <h2 className="text-base font-semibold text-gray-700 dark:text-gray-200 mb-4">导出乐谱</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {EXPORT_OPTIONS.map(({ format, label, suffix }) => (
                  <button
                    key={format}
                    onClick={() => handleExport(format)}
                    disabled={!!exporting}
                    className="flex flex-col items-center gap-2 p-4 rounded-xl border-2 border-gray-200 dark:border-gray-600 hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {exporting === format
                      ? <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                      : <FileText className="w-4 h-4 text-blue-500" />
                    }
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{label}</span>
                    <span className="text-xs text-gray-400">{suffix}</span>
                  </button>
                ))}
              </div>
            </section>

            <div className="text-center">
              <button onClick={() => navigate('/')} className="text-sm text-gray-400 hover:text-blue-500 transition-colors">分析另一首 →</button>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default Result;
