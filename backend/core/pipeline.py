"""
Audio Transcription Pipeline
============================
Main processing pipeline: upload → separate → pitch/chord detect → score generation.
Each stage updates the task record in-place.
"""

import os
import logging
from pathlib import Path
from typing import Optional

# Import from sibling modules (made available via __init__.py)
from backend.core.separator import separate_audio
from backend.core.pitch_detector import detect_pitch
from backend.core.chord_recognizer import recognize_chords
from backend.core.bpm_detector import detect_bpm
from backend.core.score_generator import generate_score

logger = logging.getLogger(__name__)


# ─── Shared task registry access ────────────────────────────────
# (In production, replace with Redis-backed store)

from backend.main import tasks, TaskStatus, TaskRecord

def _update(task_id: str, **kwargs):
    """Update task fields safely."""
    task = tasks.get(task_id)
    if task:
        for k, v in kwargs.items():
            setattr(task, k, v)


# ─── Main Pipeline ───────────────────────────────────────────────

def run_pipeline(task_id: str, input_path: Path):
    """
    Execute the full transcription pipeline for `task_id`.
    Runs synchronously in a background thread (Celery worker in production).
    
    Pipeline stages:
      1. 音频分离 (Demucs)
      2. 音符检测 (CREPE)
      3. 和弦识别 (Omnizart)
      4. BPM检测 (librosa)
      5. 乐谱生成 (music21)
    """
    try:
        # ── Stage 1: Separate audio ──────────────────────────────
        _update(task_id, status=TaskStatus.PROCESSING, progress=0.05, stage="正在分离音轨...")
        logger.info(f"[{task_id}] Starting pipeline: {input_path}")
        
        separated = separate_audio(input_path, task_id)
        _update(task_id, progress=0.35, stage="音轨分离完成")

        # ── Stage 2: Pitch detection ─────────────────────────────
        _update(task_id, progress=0.40, stage="正在检测音高...")
        pitch_data = detect_pitch(separated["guitar"], task_id)
        _update(task_id, progress=0.55, stage="音高检测完成")

        # ── Stage 3: Chord recognition ───────────────────────────
        _update(task_id, progress=0.60, stage="正在识别和弦...")
        chords = recognize_chords(separated["guitar"], task_id)
        _update(task_id, progress=0.75, stage="和弦识别完成")

        # ── Stage 4: BPM detection ───────────────────────────────
        _update(task_id, progress=0.80, stage="正在分析节拍...")
        bpm_info = detect_bpm(input_path, task_id)
        _update(task_id, progress=0.85, stage="节拍分析完成")

        # ── Stage 5: Score generation ─────────────────────────────
        _update(task_id, progress=0.90, stage="正在生成乐谱...")
        output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs"))
        score_files = generate_score(
            chords=chords,
            pitch=pitch_data,
            bpm=bpm_info,
            task_id=task_id,
            output_dir=output_dir,
        )
        _update(task_id, progress=1.0, stage="完成！")

        # ── Done ──────────────────────────────────────────────────
        result = {
            "bpm": bpm_info["bpm"],
            "time_signature": bpm_info.get("time_signature", "4/4"),
            "chords": chords,
            "pitch": pitch_data,
            "score_files": score_files,
        }
        _update(task_id, status=TaskStatus.DONE, result=result)
        logger.info(f"[{task_id}] Pipeline done! BPM={bpm_info['bpm']}, chords={len(chords)}")

    except Exception as exc:
        logger.exception(f"[{task_id}] Pipeline error: {exc}")
        _update(task_id, status=TaskStatus.ERROR, error=str(exc))
