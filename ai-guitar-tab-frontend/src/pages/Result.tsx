/**
 * Result.tsx — 扒谱结果展示页面（Guitar + Bass 双轨版）
 */
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient } from "../api/client";
import type { TaskStatus, AnalysisResult } from "../api/client";
import ChordViewer from "../components/ChordViewer";
import GTAViewer from "../components/GTAViewer";

export default function Result() {
  const [searchParams] = useSearchParams();
  const taskId = searchParams.get("taskId") || "";

  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"chords" | "bass" | "gta" | "export">("chords");

  useEffect(() => {
    if (!taskId) { setError("缺少 taskId 参数"); setLoading(false); return; }
    const poll = async () => {
      try {
        const st = await apiClient.getTaskStatus(taskId);
        setStatus(st);
        if (st.status === "done") {
          const res = await apiClient.getAnalysisResult(taskId);
          setResult(res.result);
          setLoading(false);
        } else if (st.status === "error") {
          setError(st.error || "处理出错");
          setLoading(false);
        }
      } catch { setError("查询失败"); setLoading(false); }
    };
    poll();
    const iv = setInterval(poll, 2000);
    return () => clearInterval(iv);
  }, [taskId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="text-5xl mb-4 animate-bounce">🎸</div>
        <h2 className="text-xl font-bold mb-2">扒谱中，请稍候...</h2>
        {status && (
          <div className="w-80 mt-4">
            <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 transition-all duration-500"
                style={{ width: `${(status.progress ?? 0) * 100}%` }} />
            </div>
            <p className="text-center text-sm text-gray-500 mt-2">{status.stage}</p>
          </div>
        )}
      </div>
    );
  }

  if (error) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="text-5xl mb-4">❌</div>
      <h2 className="text-xl font-bold text-red-600 mb-2">处理失败</h2>
      <p className="text-gray-600 mb-4">{error}</p>
      <a href="/" className="text-indigo-600 hover:underline">← 重新上传</a>
    </div>
  );

  const guitar = result?.guitar;
  const bass   = result?.bass;
  // 兼容旧版
  const chords = guitar?.chords ?? result?.chords ?? [];
  const bassNotes = bass?.notes ?? [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">✅ 扒谱完成！</h1>
          <p className="text-gray-500 text-sm mt-1">Task: {taskId.slice(0, 8)}...</p>
        </div>
        <a href="/" className="text-indigo-600 hover:underline text-sm">← 再来一首</a>
      </div>

      {/* 统计卡片 */}
      {result && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatCard label="BPM" value={result.bpm ?? "?"} color="indigo" />
          <StatCard label="Guitar 和弦" value={chords.length} color="green" />
          <StatCard label="Bass 音符" value={bassNotes.length} color="orange" />
          <StatCard label="拍号" value={result.time_signature ?? "4/4"} color="blue" />
        </div>
      )}

      {/* 和弦进行标签 */}
      {chords.length > 0 && (
        <div className="mb-4 px-4 py-3 bg-slate-800 rounded-xl">
          <span className="text-gray-400 text-xs mr-2">🎸 Guitar:</span>
          <span className="font-mono font-bold text-green-400">
            {chords.map((c) => c.chord).join(" → ")}
          </span>
          {bassNotes.length > 0 && (
            <>
              <div className="mt-1">
                <span className="text-gray-400 text-xs mr-2">🎸 Bass:</span>
                <span className="font-mono text-orange-400">
                  {Array.from(new Set(bassNotes.map((n) => n.note))).slice(0, 12).join(" → ")}
                </span>
              </div>
            </>
          )}
        </div>
      )}

      {/* 标签页 */}
      <div className="flex gap-1 mb-4 border-b">
        {[
          { key: "chords", label: "🎸 Guitar 和弦" },
          { key: "bass",   label: "🎸 Bass 音符" },
          { key: "gta",    label: "📋 GTA 文本谱" },
          { key: "export", label: "📥 导出下载" },
        ].map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key as typeof activeTab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === t.key ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* 面板 */}
      <div className="bg-white rounded-xl border shadow-sm p-4 min-h-[300px]">
        {activeTab === "chords" && <ChordViewer chords={chords} duration={result?.duration_sec ?? 0} />}
        {activeTab === "bass"   && <BassViewer notes={bassNotes} duration={result?.duration_sec ?? 0} />}
        {activeTab === "gta"   && result && <GTAViewer chords={chords} bpm={result.bpm ?? 120} songName="扒取乐谱" />}
        {activeTab === "export" && result && <ExportPanel taskId={taskId} />}
      </div>
    </div>
  );
}

// ─── 统计卡片 ──────────────────────────────────────────────────

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  const colors: Record<string, string> = {
    indigo: "bg-indigo-50 text-indigo-700",
    green:  "bg-green-50 text-green-700",
    orange: "bg-orange-50 text-orange-700",
    blue:   "bg-blue-50 text-blue-700",
  };
  return (
    <div className={`rounded-xl p-4 text-center ${colors[color] ?? colors.indigo}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs opacity-75 mt-1">{label}</div>
    </div>
  );
}

// ─── Bass 音符展示面板 ──────────────────────────────────────────

function BassViewer({ notes, duration }: { notes: any[]; duration: number }) {
  if (!notes || notes.length === 0) return (
    <div className="flex flex-col items-center justify-center h-48 text-gray-400">
      <div className="text-4xl mb-2">🎸</div>
      <p>暂无 Bass 音符数据</p>
      <p className="text-xs mt-1">Bass 轨道需要在完整 GPU 模式下由 Demucs 分离后检测</p>
    </div>
  );

  const unique = Array.from(new Set(notes.map((n) => n.note))).slice(0, 16);
  const duration_sec = duration > 0 ? duration : (notes[notes.length - 1]?.end ?? 60);

  return (
    <div className="space-y-4">
      {/* Bass 音符统计 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-orange-50 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-orange-700">{notes.length}</div>
          <div className="text-xs text-gray-500">音符数</div>
        </div>
        <div className="bg-orange-50 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-orange-700">{unique.length}</div>
          <div className="text-xs text-gray-500">不同音符</div>
        </div>
        <div className="bg-orange-50 rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-orange-700">{duration_sec.toFixed(1)}s</div>
          <div className="text-xs text-gray-500">时长</div>
        </div>
      </div>

      {/* 根音序列 */}
      <div>
        <p className="text-xs text-gray-500 mb-2">根音序列（Bass Line）:</p>
        <div className="flex flex-wrap gap-2">
          {unique.map((note) => (
            <span key={note}
              className="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm font-mono font-bold">
              {note}
            </span>
          ))}
        </div>
      </div>

      {/* 时间轴 */}
      <div>
        <p className="text-xs text-gray-500 mb-2">时间轴:</p>
        <div className="relative h-20 bg-slate-100 rounded-lg overflow-hidden">
          <div className="absolute inset-0 flex items-end px-1">
            {notes.map((n, i) => {
              const left = (n.start / duration_sec) * 100;
              const w    = Math.max(0.5, ((n.end - n.start) / duration_sec) * 100);
              return (
                <div key={i} title={`${n.note} (${n.start}s–${n.end}s)`}
                  className="absolute bottom-1 bg-orange-500 rounded-sm flex items-center justify-center overflow-hidden"
                  style={{ left: `${left}%`, width: `${Math.min(w, 100 - left)}%`, height: "40%" }}>
                  <span className="text-white text-xs font-bold truncate px-0.5">{n.note}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── 导出面板 ──────────────────────────────────────────────────

function ExportPanel({ taskId }: { taskId: string }) {
  const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const downloads = [
    { format: "gta",  label: "📄 GTA 文本谱",   desc: "ASCII 双轨乐谱（Guitar + Bass），任意编辑器可打开" },
    { format: "pdf",  label: "📕 PDF 乐谱",      desc: "可打印的双轨乐谱文档" },
    { format: "midi", label: "🎹 MIDI 文件",     desc: "Guitar + Bass 双轨 MIDI，导入 Guitar Pro / DAW" },
    { format: "json", label: "📊 JSON 数据",      desc: "原始分析数据（含和弦、音符、MIDI 参数）" },
  ];
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {downloads.map((d) => (
        <a key={d.format}
          href={`${BASE}/api/download/${taskId}?format=${d.format}`}
          className="block p-4 rounded-xl bg-gray-50 hover:bg-indigo-50 hover:border-indigo-200 border border-transparent transition-colors"
          download>
          <div className="font-bold mb-1">{d.label}</div>
          <div className="text-sm text-gray-500">{d.desc}</div>
        </a>
      ))}
    </div>
  );
}
