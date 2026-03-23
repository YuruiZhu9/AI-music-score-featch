/**
 * Result.tsx — 扒谱结果展示页面
 * 展示和弦时间轴、GTA文本谱、导出下载
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
  const [activeTab, setActiveTab] = useState<"chords" | "gta" | "export">("chords");

  useEffect(() => {
    if (!taskId) {
      setError("缺少 taskId 参数");
      setLoading(false);
      return;
    }

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
      } catch {
        setError("查询失败，请检查网络");
        setLoading(false);
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [taskId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="text-4xl mb-4 animate-spin">🎵</div>
        <h2 className="text-xl font-bold mb-2">扒谱进行中...</h2>
        {status && (
          <div className="w-80">
            <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 transition-all duration-500"
                style={{ width: `${(status.progress || 0) * 100}%` }}
              />
            </div>
            <p className="text-center text-sm text-gray-500 mt-2">{status.stage}</p>
          </div>
        )}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="text-5xl mb-4">❌</div>
        <h2 className="text-xl font-bold text-red-600 mb-2">处理失败</h2>
        <p className="text-gray-600 mb-4">{error}</p>
        <a href="/" className="text-indigo-600 hover:underline">← 重新上传</a>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">✅ 扒谱完成！</h1>
          <p className="text-gray-500 text-sm mt-1">Task ID: {taskId.slice(0, 8)}...</p>
        </div>
        <a href="/" className="text-indigo-600 hover:underline text-sm">← 再来一首</a>
      </div>

      {result && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-indigo-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-indigo-700">{result.bpm ?? "?"}</div>
            <div className="text-sm text-gray-500">BPM</div>
          </div>
          <div className="bg-green-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-green-700">{result.chords?.length ?? 0}</div>
            <div className="text-sm text-gray-500">识别和弦数</div>
          </div>
          <div className="bg-orange-50 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-orange-700">{result.time_signature ?? "4/4"}</div>
            <div className="text-sm text-gray-500">拍号</div>
          </div>
        </div>
      )}

      {result?.chords && result.chords.length > 0 && (
        <div className="mb-4">
          <span className="text-gray-600 text-sm">和弦进行：</span>
          <span className="font-mono font-bold text-indigo-700 ml-2">
            {result.chords.map((c) => c.chord).join(" → ")}
          </span>
        </div>
      )}

      <div className="flex gap-2 mb-4 border-b">
        {[
          { key: "chords", label: "🎸 和弦时间轴" },
          { key: "gta", label: "📋 GTA文本谱" },
          { key: "export", label: "📥 导出下载" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as typeof activeTab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.key
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border shadow-sm p-4 min-h-[300px]">
        {activeTab === "chords" && result?.chords && (
          <ChordViewer chords={result.chords} />
        )}
        {activeTab === "gta" && result && (
          <GTAViewer
            chords={result.chords ?? []}
            bpm={result.bpm ?? 120}
            songName="扒取乐谱"
          />
        )}
        {activeTab === "export" && result && (
          <ExportPanel taskId={taskId} />
        )}
      </div>
    </div>
  );
}

function ExportPanel({ taskId }: { taskId: string }) {
  const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const downloads = [
    { format: "gta", label: "📄 GTA 文本谱", desc: "ASCII格式吉他谱，可用任何编辑器打开" },
    { format: "pdf", label: "📕 PDF 乐谱", desc: "可打印的乐谱文档" },
    { format: "gp", label: "🎸 Guitar Pro 文件", desc: ".gp5格式，用 Guitar Pro 7 打开" },
    { format: "midi", label: "🎹 MIDI 文件", desc: "标准MIDI文件，可导入DAW软件" },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {downloads.map((d) => (
        <a
          key={d.format}
          href={`${BASE}/api/download/${taskId}?format=${d.format}`}
          className="block p-4 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors"
          download
        >
          <div className="font-bold mb-1">{d.label}</div>
          <div className="text-sm text-gray-500">{d.desc}</div>
        </a>
      ))}
    </div>
  );
}
