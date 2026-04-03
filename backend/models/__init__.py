"""
backend/models/__init__.py
导出所有 Pydantic 数据模型。
"""

from .schemas import (
    # Enums
    TaskStatus,
    ScoreFormat,
    # Task
    TaskRecord,
    TaskCreate,
    TaskStatusResponse,
    UploadResponse,
    ErrorResponse,
    ApiResponse,
    # Analysis
    ChordEvent,
    NoteEvent,
    BpmInfo,
    PitchResult,
    ScoreFiles,
    GuitarTrackResult,
    BassNoteEvent,
    BassTrackResult,
    AnalysisResult,
    # Beat analysis
    BeatEventModel,
    BeatAnalysisResultModel,
)

__all__ = [
    "TaskStatus",
    "ScoreFormat",
    "TaskRecord",
    "TaskCreate",
    "TaskStatusResponse",
    "UploadResponse",
    "ErrorResponse",
    "ApiResponse",
    "ChordEvent",
    "NoteEvent",
    "BpmInfo",
    "PitchResult",
    "ScoreFiles",
    "GuitarTrackResult",
    "BassNoteEvent",
    "BassTrackResult",
    "AnalysisResult",
    "BeatEventModel",
    "BeatAnalysisResultModel",
]
