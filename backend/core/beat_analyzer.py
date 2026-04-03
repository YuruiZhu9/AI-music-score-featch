"""
Beat Analyzer — 节拍模式分析与 Downbeat 检测
=============================================
基于 librosa 的深度节拍分析：
1. Beat strength（节拍强度）曲线
2. Downbeat（强拍/小节首拍）检测
3. Beat regularity（节拍稳定性）评分
4. Tempo drift（速度漂移）分析

用途：
- 为和弦识别提供节拍同步参考
- 提升 Guitar Pro 导出的演奏动态表现
- 用于乐谱的小节划分（自动检测 4/4 vs 3/4 vs 6/8）
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict

logger = logging.getLogger(__name__)

# ─── 返回类型定义 ────────────────────────────────────────────────

class BeatEvent(TypedDict, total=False):
    """单个节拍事件"""
    time: float           # 时间（秒）
    strength: float       # 强度 0.0~1.0
    is_downbeat: bool     # 是否为小节首拍
    bar: int              # 小节编号（从1开始）
    beat_in_bar: int      # 拍在小节内的位置（1-based）


class BeatAnalysisResult(TypedDict, total=False):
    """完整节拍分析结果"""
    bpm: float
    time_signature: str
    beat_events: List[BeatEvent]   # 所有节拍事件（含强度和 downbeat 标记）
    downbeats: List[float]         # 仅 downbeat 时间点
    regularity_score: float        # 节拍稳定性评分 0.0~1.0
    tempo_drift: float            # BPM 漂移（标准差）
    avg_strength: float           # 平均节拍强度
    num_bars: int                 # 检测到的总小节数
    duration_sec: float


# ─── 主函数 ────────────────────────────────────────────────────

def analyze_beat_pattern(
    audio_path: Path,
    bpm: Optional[float] = None,
    time_signature: str = "4/4",
    task_id: str = "",
) -> BeatAnalysisResult:
    """
    深度节拍模式分析：beat strength + downbeat detection。

    参数:
        audio_path:      音频文件路径
        bpm:             已知 BPM（由 detect_bpm 提供），可加速分析
        time_signature:  拍号（4/4, 3/4, 6/8 等）
        task_id:         任务ID（用于日志）

    返回:
        BeatAnalysisResult，包含所有节拍事件（含强度、downbeat标记），
        以及节拍稳定性评分。
    """
    try:
        import librosa
        import numpy as np
    except ImportError as exc:
        logger.warning(f"librosa 未安装: {exc}，返回空结果")
        return _empty_beat_result(time_signature)

    try:
        # 加载音频
        y, sr = librosa.load(str(audio_path), sr=None, mono=True)
        duration = float(len(y)) / sr
        logger.info(f"[{task_id}] 节拍分析: 时长={duration:.1f}s, BPM={bpm}, ts={time_signature}")

        # ── 1. 节拍跟踪 ─────────────────────────────────────────
        if bpm is not None and 40 <= bpm <= 240:
            tempo_est, beats = librosa.beat.beat_track(y=y, sr=sr, bpm=float(bpm), start_bpm=float(bpm))
        else:
            tempo_est, beats = librosa.beat.beat_track(y=y, sr=sr)

        bpm_actual = float(np.array(tempo_est).flatten()[0])
        beat_times = librosa.frames_to_time(beats, sr=sr)

        # ── 2. Beat Strength（节拍强度） ────────────────────────
        # 使用 onset_strength 获取每个时刻的"冲击感"
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
        hop_seconds = 512 / sr

        # 在每个 beat 时间点采样强度
        strength_at_beats = []
        for bt in beat_times:
            frame = int(bt / hop_seconds)
            frame = min(frame, len(onset_env) - 1)
            strength_at_beats.append(float(onset_env[frame]))

        # 归一化到 0~1
        if strength_at_beats:
            max_s = max(strength_at_beats)
            min_s = min(strength_at_beats)
            if max_s > min_s:
                strength_at_beats = [
                    (s - min_s) / (max_s - min_s) for s in strength_at_beats
                ]
            else:
                strength_at_beats = [0.5] * len(strength_at_beats)

        # ── 3. Downbeat 检测 ───────────────────────────────────
        downbeats, bar_starts = _detect_downbeats_from_beats(
            beat_times, strength_at_beats, time_signature
        )

        # ── 4. Beat regularity 评分 ─────────────────────────────
        regularity = _compute_regularity(beat_times)

        # ── 5. Tempo drift ─────────────────────────────────────
        drift = _compute_tempo_drift(beat_times)

        # ── 6. 构建 BeatEvent 列表 ─────────────────────────────
        beat_events: List[BeatEvent] = []
        bar_num = 1
        beat_in_bar = 1

        for i, bt in enumerate(beat_times):
            is_down = bool(bt in downbeats)
            if is_down:
                bar_num = beat_in_bar  # 实际 downbeat 的 bar_num
                beat_in_bar = 1
            else:
                beat_in_bar += 1

            beat_events.append(BeatEvent(
                time=float(bt),
                strength=strength_at_beats[i] if i < len(strength_at_beats) else 0.5,
                is_downbeat=is_down,
                bar=bar_num,
                beat_in_bar=min(beat_in_bar, _beats_per_bar(time_signature)),
            ))

        result: BeatAnalysisResult = {
            "bpm": round(bpm_actual, 2),
            "time_signature": time_signature,
            "beat_events": beat_events,
            "downbeats": [float(d) for d in downbeats],
            "regularity_score": round(regularity, 3),
            "tempo_drift": round(drift, 3),
            "avg_strength": round(float(np.mean(strength_at_beats)), 3) if strength_at_beats else 0.5,
            "num_bars": bar_num,
            "duration_sec": round(duration, 2),
        }
        logger.info(
            f"[{task_id}] 节拍分析完成: {len(beat_events)} beats, "
            f"{len(downbeats)} downbeats, regularity={regularity:.2f}"
        )
        return result

    except Exception as exc:
        logger.exception(f"[{task_id}] 节拍分析失败: {exc}")
        return _empty_beat_result(time_signature)


def detect_downbeats(
    audio_path: Path,
    bpm: Optional[float] = None,
    time_signature: str = "4/4",
    task_id: str = "",
) -> List[float]:
    """
    快速检测音频中的所有 downbeat 时间点。

    参数:
        audio_path: 音频路径
        bpm: 已知 BPM（可加速分析）
        time_signature: 拍号
        task_id: 任务ID

    返回:
        List[float]: downbeat 时间点列表（秒）
    """
    result = analyze_beat_pattern(audio_path, bpm, time_signature, task_id)
    return result["downbeats"]


# ─── 内部函数 ─────────────────────────────────────────────────

def _detect_downbeats_from_beats(
    beat_times,  # np.ndarray
    strengths: List[float],
    time_signature: str,
) -> tuple:
    """
    根据节拍强度分布推断 downbeat。

    思路：
    - downbeat 通常是每小节最强的那一拍
    - 对连续小节的对应拍位强度做平均，找出每小节的"第一强拍"
    - 该拍即为 downbeat（前提拍）

    返回: (downbeats, bar_starts) — 均为 numpy array
    """
    import numpy as np

    beats = np.asarray(beat_times)
    if len(beats) < 4:
        # 节拍太少，无法做 downbeat 检测
        return beats[[0]], beats[[0]]

    bpb = _beats_per_bar(time_signature)
    n_bars = len(beats) // bpb

    if n_bars < 1:
        return beats[[0]], beats[[0]]

    # 计算每小节内各拍的平均强度
    strength_by_position = [0.0] * bpb
    count_by_position = [0] * bpb

    for bar in range(n_bars):
        for pos in range(bpb):
            idx = bar * bpb + pos
            if idx < len(strengths):
                strength_by_position[pos] += strengths[idx]
                count_by_position[pos] += 1

    avg_strength = [
        s / c if c > 0 else 0.0
        for s, c in zip(strength_by_position, count_by_position)
    ]

    # 找出最强拍位（通常是第一拍）
    downbeat_position = int(np.argmax(avg_strength))

    # 所有该位置的节拍即为 downbeat
    downbeat_indices = list(range(downbeat_position, len(beats), bpb))
    downbeats = beats[downbeat_indices] if len(downbeat_indices) > 0 else beats[[0]]
    bar_starts = downbeats  # 小节起点 = downbeat

    return downbeats, bar_starts


def _compute_regularity(beat_times) -> float:
    """
    计算节拍规律性评分（0.0~1.0）。

    方法：
    1. 计算相邻节拍间隔
    2. 计算间隔的标准差 / 均值（变异系数 CV）
    3. regularity = 1 - min(CV, 1.0)

    CV 越小 → 节拍越规律 → 评分越高
    """
    import numpy as np

    if len(beat_times) < 3:
        return 0.5

    intervals = np.diff(beat_times)
    intervals = intervals[intervals > 0.05]  # 过滤掉异常短的间隔

    if len(intervals) < 2:
        return 0.5

    mean_interval = float(np.mean(intervals))
    std_interval  = float(np.std(intervals))

    if mean_interval <= 0:
        return 0.5

    cv = std_interval / mean_interval
    regularity = max(0.0, 1.0 - min(cv, 1.0))
    return float(regularity)


def _compute_tempo_drift(beat_times) -> float:
    """
    计算 BPM 漂移（单位：BPM 的标准差）。

    方法：将节拍序列分段（每4小节一段），计算每段的有效 BPM，
    返回各段 BPM 的标准差。
    """
    import numpy as np

    if len(beat_times) < 8:
        return 0.0

    intervals = np.diff(beat_times)
    intervals = intervals[intervals > 0.05]

    if len(intervals) < 2:
        return 0.0

    # 每 4 个间隔为一个 BPM 采样点（近似 4/4 拍的 1 小节）
    window = 4
    bpm_samples = []
    for i in range(0, len(intervals) - window + 1, window):
        chunk = intervals[i:i + window]
        mean_interval = float(np.mean(chunk))
        if mean_interval > 0:
            bpm_samples.append(60.0 / mean_interval)

    if len(bpm_samples) < 2:
        return 0.0

    return float(np.std(bpm_samples))


def _beats_per_bar(time_signature: str) -> int:
    """从拍号字符串中提取每小节拍数。"""
    try:
        parts = time_signature.strip().split("/")
        return int(parts[0])
    except Exception:
        return 4


def _empty_beat_result(time_signature: str = "4/4") -> BeatAnalysisResult:
    """失败时的空结果。"""
    return BeatAnalysisResult(
        bpm=120.0,
        time_signature=time_signature,
        beat_events=[],
        downbeats=[],
        regularity_score=0.0,
        tempo_drift=0.0,
        avg_strength=0.5,
        num_bars=0,
        duration_sec=0.0,
    )
