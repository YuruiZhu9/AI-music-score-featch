/**
 * Home — 首页 / 上传页面
 * ================================
 * 音频上传入口，支持文件上传和 URL 分析，
 * 展示实时处理进度，完成后跳转结果页。
 */

import React, { useCallback, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Music2, Github, Zap, Crown, X } from 'lucide-react';

import { api, TaskRecord } from '../api/client';
import FileUploader from '../components/FileUploader';
import ProgressBar from '../components/ProgressBar';

// ---------------------------------------------------------------------------
// Freemium 状态管理（localStorage）
// ---------------------------------------------------------------------------
const STORAGE_KEY = 'ai-guitar-tab-trials';
const FREE_TRIALS = 3;

function getRemainingTrials(): number {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === null) return FREE_TRIALS;
    return Math.max(0, parseInt(stored, 10));
  } catch {
    return FREE_TRIALS;
  }
}

function consumeTrial(): number {
  const remaining = getRemainingTrials();
  const newVal = Math.max(0, remaining - 1);
  localStorage.setItem(STORAGE_KEY, String(newVal));
  return newVal;
}

// ---------------------------------------------------------------------------
// Subscription Modal
// ---------------------------------------------------------------------------
interface SubscribeModalProps {
  onClose: () => void;
}

const SubscribeModal: React.FC<SubscribeModalProps> = ({ onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full p-8 relative animate-in zoom-in-95 fade-in duration-200">
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center">
          <Crown className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          解锁无限扒谱
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">
          订阅 Pro 会员，享受无限次扒谱、批量处理、AI智能润色、优先队列等高级功能。
        </p>

        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/40 dark:to-indigo-950/40 rounded-xl p-4 space-y-2">
          {[
            '🎸 无限次扒谱（不限时长）',
            '⚡ 优先处理队列',
            '🎨 AI 乐谱智能润色',
            '📦 批量导入多首歌曲',
            '📥 高清 PDF / Guitar Pro 导出',
          ].map((feature) => (
            <p key={feature} className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2">
              {feature}
            </p>
          ))}
        </div>

        <div className="pt-2">
          <p className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-indigo-600">
            ¥9.9 <span className="text-base font-normal text-gray-400">/ 月</span>
          </p>
          <p className="text-xs text-gray-400 mt-1">一杯奶茶的价格，无限创意</p>
        </div>

        <button
          onClick={onClose}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold hover:from-blue-600 hover:to-indigo-700 transition-all shadow-lg shadow-blue-500/30 active:scale-95"
        >
          即将推出，敬请期待
        </button>
        <p className="text-xs text-gray-400">免费试用剩余次数不受影响</p>
      </div>
    </div>
  </div>
);

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
// 乐器选项
// ---------------------------------------------------------------------------
const INSTRUMENTS = [
  { id: 'guitar', label: '吉他', icon: '🎸' },
  { id: 'bass',   label: '贝斯', icon: '🎸' },
  { id: 'drums',  label: '鼓',   icon: '🥁' },
];

// ---------------------------------------------------------------------------
// 组件
// ---------------------------------------------------------------------------
const Home: React.FC = () => {
  const navigate = useNavigate();

  // Freemium 状态
  const [remainingTrials, setRemainingTrials] = useState(FREE_TRIALS);
  const [showSubModal, setShowSubModal] = useState(false);

  useEffect(() => {
    setRemainingTrials(getRemainingTrials());
  }, []);

  // 状态
  const [phase, setPhase] = useState<'idle' | 'uploading' | 'processing'>('idle');
  const [progress, setProgress] = useState(0);
  const [stageLabel, setStageLabel] = useState<string>('上传音频');
  const [stages, setStages] = useState<Stage[]>(PIPELINE_STAGES);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [selectedInstrument, setSelectedInstrument] = useState('guitar');

  // 试用扣减 + 检查是否可继续
  const checkAndConsumeTrial = useCallback(() => {
    const remaining = getRemainingTrials();
    if (remaining <= 0) {
      setShowSubModal(true);
      return false;
    }
    consumeTrial();
    setRemainingTrials(Math.max(0, remaining - 1));
    return true;
  }, []);

  // -------------------------------------------------------------------------
  // 文件上传 → 开始轮询
  // -------------------------------------------------------------------------
  const handleFileSelected = useCallback(async (file: File) => {
    if (!checkAndConsumeTrial()) return;

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
  }, [checkAndConsumeTrial, navigate]);

  // -------------------------------------------------------------------------
  // URL 提交 → 开始分析
  // -------------------------------------------------------------------------
  const handleUrlSubmit = useCallback(async (url: string) => {
    if (!checkAndConsumeTrial()) return;

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
  }, [checkAndConsumeTrial, navigate]);

  // -------------------------------------------------------------------------
  // 渲染
  // -------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 dark:from-gray-900 dark:to-gray-800 flex flex-col">

      {/* Freemium Banner */}
      {phase === 'idle' && (
        <div className="w-full bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/30 border-b border-amber-200 dark:border-amber-800/50">
          <div className="max-w-5xl mx-auto px-6 py-2.5 flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400">
              <Crown className="w-4 h-4 flex-shrink-0" />
              <span>
                <strong>免费试用：</strong>
                剩余{' '}
                <span className={`font-bold ${remainingTrials === 0 ? 'text-red-500' : 'text-amber-600 dark:text-amber-300'}`}>
                  {remainingTrials}
                </span>{' '}
                / {FREE_TRIALS} 次
              </span>
              {remainingTrials === 0 && (
                <span className="text-red-500 text-xs font-medium ml-1">（已用完）</span>
              )}
            </div>
            <button
              onClick={() => setShowSubModal(true)}
              className="flex items-center gap-1.5 text-xs px-3 py-1 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 text-white font-medium hover:from-amber-500 hover:to-orange-600 transition-all shadow-sm"
            >
              <Crown className="w-3 h-3" />
              升级 Pro · 解锁无限扒谱
            </button>
          </div>
        </div>
      )}

      {/* 订阅弹窗 */}
      {showSubModal && <SubscribeModal onClose={() => setShowSubModal(false)} />}

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
              {/* 乐器选择 */}
              <div className="flex gap-3 justify-center flex-wrap">
                {INSTRUMENTS.map((inst) => (
                  <button
                    key={inst.id}
                    onClick={() => setSelectedInstrument(inst.id)}
                    className={`
                      px-4 py-2 rounded-xl text-sm font-medium border-2 transition-all
                      ${selectedInstrument === inst.id
                        ? 'border-blue-500 bg-blue-500 text-white shadow-md'
                        : 'border-gray-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 bg-transparent hover:border-blue-400 hover:text-blue-500'
                      }
                    `}
                  >
                    {inst.icon} {inst.label}
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
