"""
音频 Transcription Pipeline
===========================
主处理流程：音频 → 分离 → 和弦 → 节拍 → 音高 → 乐谱

无 GPU 时自动降级到 librosa 纯 CPU 模式，确保 MVP 能正常运行。
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ─── 共享任务状态 ──────────────────────────────────────────────
from backend.main import tasks, TaskStatus, TaskRecord

def _update(task_id: str, **kwargs):
    task = tasks.get(task_id)
    if task:
        for k, v in kwargs.items():
            setattr(task, k, v)


# ─── Demo 数据生成器（无 GPU 时使用）────────────────────────────

def _generate_demo_result(task_id: str) -> Dict[str, Any]:
    """当模型不可用时，生成演示结果（固定和弦进行）。"""
    import random

    # 经典的 Am-G-C-F 和弦进行（流行歌曲常见）
    demo_chords = [
        {"start": 0.0,  "end": 1.92, "chord": "Am"},
        {"start": 1.92, "end": 3.84, "chord": "G"},
        {"start": 3.84, "end": 5.76, "chord": "C"},
        {"start": 5.76, "end": 7.68, "chord": "F"},
        {"start": 7.68, "end": 9.60, "chord": "Am"},
        {"start": 9.60, "end": 11.52, "chord": "Em"},
        {"start": 11.52, "end": 13.44, "chord": "G"},
        {"start": 13.44, "end": 15.36, "chord": "D"},
    ]

    return {
        "bpm": 120,
        "time_signature": "4/4",
        "duration_sec": 15.36,
        "chords": demo_chords,
        "notes": [],
        "score_files": {},
        "is_demo": True,
    }


# ─── Demo 模式检测 ─────────────────────────────────────────────

def _is_demo_mode() -> bool:
    """检测是否应该使用 demo 模式（无重型依赖时）。"""
    # 如果环境变量 DEMO_MODE=1，强制 demo
    if os.getenv("DEMO_MODE", "0") == "1":
        return True
    # 自动检测：尝试导入关键依赖
    try:
        import torch; del torch  # 触发加载
        return False  # torch 可用，非 demo
    except ImportError:
        return True


# ─── 主 Pipeline ──────────────────────────────────────────────

def run_pipeline(task_id: str, audio_path: Path):
    """
    执行完整扒谱流程。
    
    优先使用 Demucs + CREPE + Omnizart，
    不可用时自动降级到 librosa CPU 模式。
    """
    try:
        _update(task_id, status=TaskStatus.PROCESSING,
                progress=0.05, stage="检查运行环境...")

        if _is_demo_mode():
            logger.info(f"[{task_id}] Demo 模式运行（无 GPU）")
            return _run_demo_pipeline(task_id, audio_path)

        return _run_full_pipeline(task_id, audio_path)

    except Exception as exc:
        logger.exception(f"[{task_id}] Pipeline error: {exc}")
        # 降级到 demo 模式
        logger.info(f"[{task_id}] 降级到 Demo 模式...")
        try:
            _run_demo_pipeline(task_id, audio_path)
        except Exception as demo_error:
            _update(task_id, status=TaskStatus.ERROR,
                   error=f"处理失败（Demo也出错）: {demo_error}")


def _run_demo_pipeline(task_id: str, audio_path: Path) -> None:
    """纯 CPU Demo Pipeline：无需 GPU 依赖。"""
    from backend.core.chord_recognizer import recognize_chords
    from backend.core.bpm_detector import detect_bpm
    from backend.core.score_generator import build_gta_text, build_pdf_score, build_midi_file

    _update(task_id, progress=0.1, stage="Demo: 分析音频...")

    try:
        chords = recognize_chords(audio_path, task_id)
    except Exception:
        chords = []

    try:
        bpm_info = detect_bpm(audio_path, task_id)
    except Exception:
        bpm_info = {"bpm": 120, "time_signature": "4/4", "beat_times": []}

    _update(task_id, progress=0.5, stage="Demo: 生成乐谱...")

    output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs")) / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    gta_text = build_gta_text(
        chords=chords or [
            {"start": 0.0, "end": 1.92, "chord": "Am"},
            {"start": 1.92, "end": 3.84, "chord": "G"},
            {"start": 3.84, "end": 5.76, "chord": "C"},
            {"start": 5.76, "end": 7.68, "chord": "F"},
        ],
        bpm=bpm_info.get("bpm", 120),
        song_name="演示歌曲",
        artist="AI Guitar Tab",
    )

    # 保存 GTA 文本文件
    gta_path = output_dir / "score.gta.txt"
    gta_path.write_text(gta_text, encoding="utf-8")
    logger.info(f"[{task_id}] GTA 文本谱已保存: {gta_path}")

    # 生成 PDF
    try:
        pdf_path = output_dir / "score.pdf"
        build_pdf_score(gta_text, bpm_info, pdf_path)
        logger.info(f"[{task_id}] PDF 乐谱已保存: {pdf_path}")
    except Exception as e:
        logger.warning(f"[{task_id}] PDF 生成失败: {e}")

    # MIDI 文件生成（Guitar Pro 可直接导入）
    try:
        midi_path = output_dir / "score.mid"
        build_midi_file(chords or [], bpm_info.get("bpm", 120), midi_path)
        logger.info(f"[{task_id}] MIDI 文件已保存: {midi_path}")
    except Exception as midi_err:
        logger.warning(f"[{task_id}] MIDI 生成失败: {midi_err}")

    _update(task_id, progress=1.0, stage="Demo 完成！")

    result = {
        "bpm": bpm_info.get("bpm", 120),
        "time_signature": bpm_info.get("time_signature", "4/4"),
        "duration_sec": 0,
        "chords": chords or [],
        "notes": [],
        "score_files": {
            "gta": str(gta_path),
            "pdf": str(output_dir / "score.pdf"),
            "mid": str(output_dir / "score.mid"),
        },
        "gta_text": gta_text,
        "is_demo": len(chords) == 0,
    }
    _update(task_id, status=TaskStatus.DONE, result=result)


def _run_full_pipeline(task_id: str, audio_path: Path) -> None:
    """完整 Pipeline：使用 Demucs + CREPE + Omnizart。"""
    from backend.core.separator import separate_audio
    from backend.core.pitch_detector import detect_pitch
    from backend.core.chord_recognizer import recognize_chords
    from backend.core.bpm_detector import detect_bpm
    from backend.core.score_generator import build_gta_text, build_pdf_score, build_midi_file

    # Stage 1: 音频分离
    _update(task_id, progress=0.05, stage="正在分离音轨...")
    try:
        separated = separate_audio(audio_path, task_id)
    except Exception as sep_err:
        logger.warning(f"[{task_id}] 音频分离失败，使用原文件: {sep_err}")
        separated = {"guitar": audio_path}

    _update(task_id, progress=0.35, stage="音轨分离完成")

    # Stage 2: 音高检测
    guitar_path = separated.get("guitar", audio_path)
    _update(task_id, progress=0.40, stage="正在检测音高...")
    try:
        pitch_data = detect_pitch(guitar_path, task_id)
    except Exception as e:
        logger.warning(f"[{task_id}] 音高检测失败: {e}")
        pitch_data = {"notes": [], "total_notes": 0}

    _update(task_id, progress=0.55, stage="音高检测完成")

    # Stage 3: 和弦识别
    _update(task_id, progress=0.60, stage="正在识别和弦...")
    try:
        chords = recognize_chords(guitar_path, task_id)
    except Exception as e:
        logger.warning(f"[{task_id}] 和弦识别失败: {e}")
        chords = []

    _update(task_id, progress=0.75, stage="和弦识别完成")

    # Stage 4: BPM 检测
    _update(task_id, progress=0.80, stage="正在分析节拍...")
    try:
        bpm_info = detect_bpm(audio_path, task_id)
    except Exception as e:
        logger.warning(f"[{task_id}] BPM 检测失败: {e}")
        bpm_info = {"bpm": 120, "time_signature": "4/4", "beat_times": []}

    _update(task_id, progress=0.85, stage="节拍分析完成")

    # Stage 5: 乐谱生成
    _update(task_id, progress=0.90, stage="正在生成乐谱...")
    output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs")) / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    gta_text = build_gta_text(
        chords=chords,
        bpm=bpm_info.get("bpm", 120),
        song_name="扒取乐谱",
    )
    gta_path = output_dir / "score.gta.txt"
    gta_path.write_text(gta_text, encoding="utf-8")

    try:
        pdf_path = output_dir / "score.pdf"
        build_pdf_score(gta_text, bpm_info, pdf_path)
    except Exception as e:
        logger.warning(f"[{task_id}] PDF 生成失败: {e}")

    # MIDI 文件生成
    try:
        midi_path = output_dir / "score.mid"
        build_midi_file(chords, bpm_info.get("bpm", 120), midi_path)
        logger.info(f"[{task_id}] MIDI 文件已保存: {midi_path}")
    except Exception as midi_err:
        logger.warning(f"[{task_id}] MIDI 生成失败: {midi_err}")

    _update(task_id, progress=1.0, stage="完成！")

    result = {
        "bpm": bpm_info.get("bpm", 120),
        "time_signature": bpm_info.get("time_signature", "4/4"),
        "duration_sec": pitch_data.get("duration_sec", 0),
        "chords": chords,
        "notes": pitch_data.get("notes", []),
        "pitch": pitch_data,
        "score_files": {
            "gta": str(gta_path),
            "pdf": str(output_dir / "score.pdf"),
            "mid": str(output_dir / "score.mid"),
        },
        "gta_text": gta_text,
        "is_demo": False,
    }
    _update(task_id, status=TaskStatus.DONE, result=result)
    logger.info(f"[{task_id}] Pipeline 完成! BPM={bpm_info['bpm']}, 和弦={len(chords)}")
