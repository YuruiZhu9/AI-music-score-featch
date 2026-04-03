"""
backend/core/__init__.py
导出所有音频处理核心模块。
"""

from .bpm_detector import detect_bpm, estimate_time_signature, _default_bpm
from .beat_analyzer import (
    analyze_beat_pattern,
    detect_downbeats,
    BeatAnalysisResult,
    BeatEvent,
)
from .chord_recognizer import recognize_chords, recognize_bass_notes
from .pitch_detector import detect_pitch
from .score_generator import (
    generate_score,
    build_gta_text,
    build_pdf_score,
)
from .separator import separate_audio
from .downloader import is_supported_url, extract_audio_from_url, get_video_metadata
from .pipeline import run_pipeline
from .config import Settings, get_settings

__all__ = [
    # BPM & Beat
    "detect_bpm",
    "estimate_time_signature",
    "_default_bpm",
    "analyze_beat_pattern",
    "detect_downbeats",
    "BeatAnalysisResult",
    "BeatEvent",
    # Chord
    "recognize_chords",
    "recognize_bass_notes",
    # Pitch
    "detect_pitch",
    # Score
    "generate_score",
    "build_gta_text",
    "build_pdf_score",
    # Separation
    "separate_audio",
    # Download
    "is_supported_url",
    "extract_audio_from_url",
    "get_video_metadata",
    # Pipeline
    "run_pipeline",
    # Config
    "Settings",
    "get_settings",
]
