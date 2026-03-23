/**
 * App.tsx — AI Guitar Tab Transcriber
 * 主应用入口，含路由配置
 */
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Result from "./pages/Result";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-blue-50">
        {/* 全局导航栏 */}
        <nav className="border-b bg-white/80 backdrop-blur">
          <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-2">
            <span className="text-xl">🎸</span>
            <span className="font-bold text-gray-900">AI Guitar Tab Transcriber</span>
            <span className="ml-auto text-xs text-gray-400">AI 扒谱 · 输入视频，即得吉他谱</span>
          </div>
        </nav>

        {/* 路由 */}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/result" element={<Result />} />
        </Routes>

        {/* Footer */}
        <footer className="text-center text-xs text-gray-400 py-6">
          基于 Demucs + CREPE + librosa 构建 · GPL-3.0 开源
        </footer>
      </div>
    </BrowserRouter>
  );
}
