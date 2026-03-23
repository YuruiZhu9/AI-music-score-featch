"""
BPM / 节拍检测 — librosa
===========================
使用 librosa 进行音频节拍跟踪和 BPM 检测。
支持时间签名分析，返回节拍时间点序列。
"""

import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def detect_bpm(audio_path: Path, task_id: str) -> Dict[str, Any]:
    """
    检测音频的 BPM（每分钟节拍数）和节拍时间点。

    参数:
        audio_path: 音频文件路径（MP3/WAV/FLAC）
        task_id:    任务ID（用于日志）

    返回:
        {
            "bpm": int,              # 检测到的BPM值
            "time_signature": str,   # 时间签名，默认 "4/4"
            "beat_times": list[float],  # 每个节拍的时间点（秒）
            "duration_sec": float,  # 音频总时长
        }
    """
    try:
        import librosa
        import numpy as np
    except ImportError as e:
        logger.warning(f"librosa 未安装: {e}，使用默认 BPM=120")
        return _default_bpm()

    try:
        # 加载音频
        y, sr = librosa.load(str(audio_path), sr=None, mono=True)
        duration = float(len(y)) / sr

        logger.info(f"[{task_id}] 运行 librosa 节拍跟踪... 时长={duration:.1f}s")

        # ── 节拍跟踪 ──────────────────────────────────────────────
        # tempo, beats = librosa.beat.beat_track(y=y, sr=sr, bpm=120)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

        # 获取 BPM（librosa 返回的 tempo 可能是浮点数组）
        bpm_value = float(np.array(tempo).flatten()[0])
        # BPM 通常在 60-200 之间，如果超出说明检测可能有问题
        if bpm_value < 60 or bpm_value > 220:
            logger.warning(f"[{task_id}] BPM={bpm_value:.1f} 超出正常范围，使用默认值 120")
            bpm_value = 120.0

        # 将帧索引转换为时间（秒）
        beat_times = librosa.frames_to_time(beats, sr=sr).tolist()
        beat_times = [round(t, 3) for t in beat_times]

        logger.info(f"[{task_id}] 节拍检测完成: BPM={bpm_value:.1f}, 节拍数={len(beat_times)}")

        # ── 拍号分析（简化版：默认 4/4） ──────────────────────────────
        # TODO: 后续可分析小节结构判断拍号
        time_signature = "4/4"

        return {
            "bpm": int(round(bpm_value)),
            "time_signature": time_signature,
            "beat_times": beat_times,
            "duration_sec": round(duration, 2),
        }

    except Exception as exc:
        logger.exception(f"[{task_id}] BPM检测失败: {exc}")
        return _default_bpm()


def _default_bpm() -> Dict[str, Any]:
    """BPM 检测失败时的默认返回值。"""
    return {
        "bpm": 120,
        "time_signature": "4/4",
        "beat_times": [],
        "duration_sec": 0.0,
    }


def estimate_time_signature(beat_times: list[float]) -> str:
    """
    根据节拍间隔估算时间签名（简化实现）。

    计算连续节拍之间的间隔分布，判断是否符合 4/4 或 3/4 等。

    参数:
        beat_times: 节拍时间点列表

    返回:
        时间签名字符串，如 "4/4" 或 "3/4"
    """
    if len(beat_times) < 8:
        return "4/4"  # 默认

    # 计算相邻节拍的间隔
    intervals = [beat_times[i+1] - beat_times[i] for i in range(len(beat_times)-1)]

    # 简单统计：取中位数间隔
    import numpy as np
    median_interval = float(np.median(intervals))

    # 判断是否有明显的强弱拍模式（简化）
    # 3/4 拍：每3拍形成一个完整小节
    # 4/4 拍：每4拍形成一个完整小节
    # 这里只做简单返回，实际可结合小节结构分析
    return "4/4"
