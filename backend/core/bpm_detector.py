"""
BPM / 节拍检测 — librosa
===========================
使用 librosa 进行音频节拍跟踪和 BPM 检测。
支持时间签名分析，返回节拍时间点序列。

与 beat_analyzer.py 配合使用：
- detect_bpm() → 获取 BPM + beat_times
- analyze_beat_pattern() → 获取 beat_strength + downbeats + regularity
"""

import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def detect_bpm(audio_path: Path, task_id: str = "") -> Dict[str, Any]:
    """
    检测音频的 BPM（每分钟节拍数）和节拍时间点。

    参数:
        audio_path: 音频文件路径（MP3/WAV/FLAC）
        task_id:    任务ID（用于日志）

    返回:
        {
            "bpm": int,               # 检测到的BPM值（60~220）
            "time_signature": str,     # 时间签名：4/4, 3/4, 6/8 等
            "beat_times": list[float], # 每个节拍的时间点（秒）
            "duration_sec": float,     # 音频总时长（秒）
        }
    """
    try:
        import librosa
        import numpy as np
    except ImportError as exc:
        logger.warning(f"librosa 未安装: {exc}，使用默认 BPM=120")
        return _default_bpm()

    try:
        # 加载音频（单声道，降低计算量）
        y, sr = librosa.load(str(audio_path), sr=None, mono=True)
        duration = float(len(y)) / sr
        logger.info(f"[{task_id}] 节拍检测: 时长={duration:.1f}s")

        # ── 节拍跟踪 ──────────────────────────────────────────────
        tempo_est, beats = librosa.beat.beat_track(y=y, sr=sr)

        # 获取 BPM（librosa 返回的 tempo 可能是浮点数组）
        bpm_raw = float(np.array(tempo_est).flatten()[0])

        # ── BPM 修正：双重校验 ────────────────────────────────────
        bpm_value = _correct_bpm(bpm_raw)
        logger.info(f"[{task_id}] 原始BPM={bpm_raw:.1f} → 修正后={bpm_value}")

        # ── 将帧索引转换为时间（秒） ──────────────────────────────
        beat_times = librosa.frames_to_time(beats, sr=sr).tolist()
        beat_times = [round(t, 3) for t in beat_times]

        # ── 时间签名分析 ──────────────────────────────────────────
        time_signature = estimate_time_signature(beat_times, sr)

        logger.info(
            f"[{task_id}] 节拍检测完成: "
            f"BPM={bpm_value}, 拍号={time_signature}, 节拍数={len(beat_times)}"
        )

        return {
            "bpm": bpm_value,
            "time_signature": time_signature,
            "beat_times": beat_times,
            "duration_sec": round(duration, 2),
        }

    except Exception as exc:
        logger.exception(f"[{task_id}] BPM检测失败: {exc}")
        return _default_bpm()


def _correct_bpm(bpm_raw: float) -> int:
    """
    librosa 的 BPM 检测结果有时会得到 2x / 0.5x 的值，
    这里通过区间判断做修正。

    规则：
    - BPM > 200 → 认为是实际 BPM 的 0.5 倍
    - BPM < 50 → 认为是实际 BPM 的 2 倍
    - 否则直接取整
    """
    if bpm_raw > 200:
        bpm = bpm_raw * 0.5
    elif bpm_raw < 50:
        bpm = bpm_raw * 2.0
    else:
        bpm = bpm_raw

    bpm = max(40, min(220, bpm))  # 限制在合理区间
    return int(round(bpm))


def estimate_time_signature(
    beat_times: list[float],
    sr: int = 22050,
) -> str:
    """
    根据节拍间隔分布估算时间签名。

    分析方法：
    1. 计算相邻节拍之间的间隔
    2. 使用 KMeans 聚类找出两个主要间隔模式（对应强拍间格和弱拍间格）
    3. 计算间隔比值，推断分子（每小节拍数）

    支持的拍号：4/4, 3/4, 6/8, 2/4, 5/4, 7/8

    参数:
        beat_times: 节拍时间点列表
        sr: 采样率（用于估算置信度）

    返回:
        时间签名字符串
    """
    import numpy as np

    if len(beat_times) < 6:
        return "4/4"  # 默认

    # 计算相邻节拍的间隔
    beat_times_arr = np.asarray(beat_times)
    intervals = np.diff(beat_times_arr)
    intervals = intervals[intervals > 0.1]  # 过滤异常值

    if len(intervals) < 4:
        return "4/4"

    median_interval = float(np.median(intervals))

    # 检测是否有明显的快慢拍交替（6/8 拍的三连音模式）
    if len(intervals) >= 3:
        triplets = _detect_triplet_pattern(intervals)
        if triplets:
            return "6/8"

    # 计算节拍密度的聚类模式
    bpb = _infer_beats_per_bar_by_clustering(intervals)

    # 映射到已知拍号
    ts_map = {
        2: "2/4",
        3: "3/4",
        4: "4/4",
        5: "5/4",
        6: "6/8",
        7: "7/8",
    }
    return ts_map.get(bpb, "4/4")


def _detect_triplet_pattern(intervals) -> bool:
    """
    检测是否为 6/8 拍的 三连音模式。
    6/8 拍的特征：小节内三个音一组，每组内两个音较近（形成三连音感觉）。
    简化判断：若间隔序列中存在连续 3:2 的比值模式，则认为是 6/8。
    """
    import numpy as np

    intervals = np.asarray(intervals)
    if len(intervals) < 3:
        return False

    # 找局部最小值（可能的慢拍间隔）
    local_mins = []
    for i in range(1, len(intervals) - 1):
        if float(intervals[i]) < float(intervals[i - 1]) and float(intervals[i]) < float(intervals[i + 1]):
            local_mins.append(i)

    if len(local_mins) < 2:
        return False

    # 检验是否有规律性的慢拍间隔
    if len(local_mins) >= 2:
        # 计算小节长度（相邻慢拍之间的间隔）
        bar_lengths = [float(intervals[local_mins[i]]) + float(intervals[local_mins[i] + 1])
                       for i in range(len(local_mins) - 1)]
        # 加上最后一个慢拍到下一个快拍的间隔
        if len(intervals) > local_mins[-1] + 1:
            bar_lengths.append(
                float(intervals[local_mins[-1]]) + float(intervals[local_mins[-1] + 1])
            )
        if bar_lengths:
            # 6/8 拍每小节约等于 3 倍的基础间隔
            mean_interval = float(np.mean(intervals))
            bar_mean = float(np.mean(bar_lengths))
            ratio = bar_mean / mean_interval if mean_interval > 0 else 0
            # 如果 bar_mean ≈ 3 * mean_interval → 6/8
            return 2.5 <= ratio <= 3.5

    return False


def _infer_beats_per_bar_by_clustering(intervals) -> int:
    """
    通过间隔聚类推断每小节的拍数。

    方法：
    1. 计算间隔序列的均值和标准差
    2. 统计间隔的分布
    3. 根据间隔分布推断小节结构
    """
    import numpy as np

    intervals = np.asarray(intervals)
    mean_i = float(np.mean(intervals))
    std_i  = float(np.std(intervals))

    # 如果标准差很小（< 均值的 10%），说明节拍非常规律
    if mean_i > 0 and std_i / mean_i < 0.1:
        return 4  # 高度规律 → 假设 4/4

    # 使用中位数间隔估算小节长度
    median_i = float(np.median(intervals))
    total_beats = len(intervals) + 1  # N 个间隔 → N+1 个节拍
    estimated_bars = total_beats / 4   # 假设 4/4，每小节4拍

    # 四舍五入到最近的整数拍
    nearest_int = round(estimated_bars * 4)
    nearest_int = max(2, min(8, nearest_int))  # 限制在 2~8

    return nearest_int


def _default_bpm() -> Dict[str, Any]:
    """BPM 检测失败时的默认返回值。"""
    return {
        "bpm": 120,
        "time_signature": "4/4",
        "beat_times": [],
        "duration_sec": 0.0,
    }
