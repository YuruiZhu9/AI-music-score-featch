/**
 * Home — 首页 / 上传页面
 * ================================
 * 音频上传入口，支持文件上传和 URL 分析，
 * 展示实时处理进度，完成后跳转结果页。
 */

import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Music2, Github, Zap } from 'lucide-react';

import { api, TaskRecord } from '../api/client';
import FileUploader from '../components/FileUploader';
import ProgressBar from '../components/ProgressBar';

// ---------------------------------------------------------------------------
// 处理阶段定义
// ---------------------------------------------------------------------------
interface Stage {
  id: string;
  label: string;
  done: boolean;
  active: boolean;
  error?: boolean;
}

const PIPELINE_STAGES: Stage[] = [
  { id: 'upload', label: '上传音频', done: false, active: false },
  { id: 'separate', label: '分离音轨', done: false, active: false },
  { id: 'pitch', label: '检测音高', done: false, active: false },
  { id: 'chord', label: '识别和弦', done: false, active: false },
  { id: 'bpm', label: '分析节拍', done: false, active: false },
  { id: 'score', label: '生成乐谱', done: false, active: false },
];

function stagesFromProgress(stageLabel?: string): Stage[] {
  const order = ['上传音频', '分离音轨', '检测音高', '识别和弦', '分析节拍', '生成乐谱'];
  const activeIndex = stageLabel ? order.indexOf(stageLabel) : 0;
  return PIPELINE_STAGES.map((s, i) => ({
    ...s,
    done: i < activeIndex,
    active: i === activeIndex,
  }));
}

// ---------------------------------------------------------------------------
// 组件
// ---------------------------------------------------------------------------
const Home: React.FC = () => {
  const navigate = useNavigate();

  // 状态
  const [phase, setPhase] = useState<'idle' | 'uploading' | 'processing'>('idle');
  const [progress, setProgress] = useState(0);
  const [stageLabel, setStageLabel] = useState<string>('上传音频');
  const [stages, setStages] = useState<Stage[]>(PIPELINE_STAGES);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // 文件上传 → 开始轮询
  // -------------------------------------------------------------------------
  const handleFileSelected = useCallback(async (file: File) => {
    setErrorMsg(null);
    setPhase('uploading');
    setProgress(0);
    setStages(stagesFromProgress('上传音频'));

    try {
      // 1. 上传文件
      const { task_id } = await api.uploadAudio(file);
      setTaskId(task_id);
      setPhase('processing');
      setProgress(10);
      setStageLabel('分离音轨');
      setStages(stagesFromProgress('分离音轨'));

      // 2. 轮询任务状态
      await api.pollTask(
        task_id,
        (task: TaskRecord) => {
          setProgress(Math.round(task.progress * 100));
          if (task.stage) {
            setStageLabel(task.stage);
            setStages(stagesFromProgress(task.stage));
          }
        },
        2000
      );

      // 3. 完成 → 跳转结果页
      setProgress(100);
      setStageLabel('生成乐谱');
      setStages(stagesFromProgress('生成乐谱').map(s => ({ ...s, done: true })));
      navigate(`/result/${task_id}`);
    } catch (err: any) {
      setPhase('idle');
      setErrorMsg(err?.message ?? '处理失败，请重试');
      setStages(stages.map(s => ({ ...s, error: false, done: false, active: false })));
    }
  }, [navigate]);

  // -------------------------------------------------------------------------
  // URL 提交 → 开始分析
  // -------------------------------------------------------------------------
  const handleUrlSubmit = useCallback(async (url: string) => {
    setErrorMsg(null);
    setPhase('uploading');
    setProgress(0);
    setStages(stagesFromProgress('上传音频'));

    try {
      const { task_id } = await api.analyzeUrl(url);
      setTaskId(task_id);
      setPhase('processing');
      setProgress(10);
      setStageLabel('分离音轨');
      setStages(stagesFromProgress('分离音轨'));

      await api.pollTask(
        task_id,
        (task: TaskRecord) => {
          setProgress(Math.round(task.progress * 100));
          if (task.stage) {
            setStageLabel(task.stage);
            setStages(stagesFromProgress(task.stage));
          }
        },
        2000
      );

      setProgress(100);
      setStages(stagesFromProgress('生成乐谱').map(s => ({ ...s, done: true })));
      navigate(`/result/${task_id}`);
    } catch (err: any) {
      setPhase('idle');
      setErrorMsg(err?.message ?? '处理失败，请重试');
    }
  }, [navigate]);

  // -------------------------------------------------------------------------
  // 渲染
  // -------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-900 dark:to-gray-800 flex flex-col">

      {/* 顶部导航 */}
      <header className="flex items-center justify-between px-6 py-4 max-w-5xl mx-auto w-full">
        <div className="flex items-center gap-2">
          <Music2 className="w-7 h-7 text-blue-500" />
          <span className="text-xl font-bold text-gray-800 dark:text-white">
            AI Guitar Tab
          </span>
        </div>
        <a
          href="https://github.com/YuruiZhu9/AI-music-score-featch"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
        >
          <Github className="w-4 h-4" />
          GitHub
        </a>
      </header>

      {/* 主内容 */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12 gap-10">

        {/* 标题区 */}
        <div className="text-center space-y-3">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white tracking-tight">
            AI 智能吉他扒谱
          </h1>
          <p className="text-lg text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            上传演奏音频，自动识别和弦、节拍，生成 Guitar Pro 格式乐谱
          </p>
        </div>

        {/* 上传 / 进度区 */}
        <div className="w-full max-w-2xl bg-white dark:bg-gray-800 rounded-2xl shadow-xl shadow-blue-100/30 dark:shadow-none p-8 space-y-8">

          {phase === 'idle' ? (
            <>
              {/* 乐器选择（预留） */}
              <div className="flex gap-3 justify-center flex-wrap">
                {['吉他', '贝斯', '鼓'].map((inst) => (
                  <button
                    key={inst}
                    className="px-4 py-2 rounded-xl text-sm font-medium border-2 border-blue-500 text-blue-500 bg-transparent hover:bg-blue-50 dark:hover:bg-blue-950 transition-colors"
                  >
                    {inst}
                  </button>
                ))}
              </div>

              <FileUploader
                onFileSelected={handleFileSelected}
                onUrlSubmit={handleUrlSubmit}
              />

              {/* 功能亮点 */}
              <div className="grid grid-cols-3 gap-4 text-center">
                {[
                  { icon: '🎸', label: '精准和弦识别' },
                  { icon: '⚡', label: 'BPM 自动检测' },
                  { icon: '📄', label: 'Guitar Pro 导出' },
                ].map(({ icon, label }) => (
                  <div key={label} className="text-sm text-gray-500 dark:text-gray-400">
                    <div className="text-2xl mb-1">{icon}</div>
                    {label}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="space-y-6">
              <ProgressBar
                progress={progress}
                stageLabel={stageLabel}
                stages={stages}
              />

              {errorMsg && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                  <p className="text-sm text-red-600 dark:text-red-400">{errorMsg}</p>
                  <button
                    onClick={() => setPhase('idle')}
                    className="mt-2 text-xs text-red-500 hover:underline"
                  >
                    重新上传
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 底部说明 */}
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Zap className="w-3 h-3" />
          处理全程在服务器完成，音频安全加密存储
        </div>
      </main>
    </div>
  );
};

export default Home;
