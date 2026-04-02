"""
测试：Pydantic 数据模型 — backend/models/schemas.py
====================================================
验证所有枚举、BaseModel 能正确序列化/反序列化。
"""

import sys
import pytest
import pydantic
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from backend.models.schemas import (
    TaskStatus,
    ScoreFormat,
    TaskRecord,
    TaskStatusResponse,
    ChordEvent,
    NoteEvent,
    BpmInfo,
    PitchResult,
    ScoreFiles,
    GuitarTrackResult,
    BassNoteEvent,
    BassTrackResult,
    AnalysisResult,
    ApiResponse,
    UploadResponse,
    ErrorResponse,
)


# ─── 枚举 ──────────────────────────────────────────────────────

class TestTaskStatus:
    def test_task_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.DONE.value == "done"
        assert TaskStatus.ERROR.value == "error"

    def test_task_status_is_string_enum(self):
        # TaskStatus 是 str 的子类，可以直接做比较
        s: str = TaskStatus.DONE
        assert s == "done"


class TestScoreFormat:
    def test_score_format_values(self):
        assert ScoreFormat.PDF.value == "pdf"
        assert ScoreFormat.MIDI.value == "midi"
        assert ScoreFormat.GP.value == "gp"
        assert ScoreFormat.JSON.value == "json"
        assert ScoreFormat.GTA.value == "gta"


# ─── TaskRecord ───────────────────────────────────────────────

class TestTaskRecord:
    def test_default_values(self):
        rec = TaskRecord(task_id="test-123")
        assert rec.task_id == "test-123"
        assert rec.status == TaskStatus.PENDING
        assert rec.progress == 0.0
        assert rec.stage == "等待上传"
        assert rec.song_name is None
        assert rec.input_url is None
        assert rec.input_path is None
        assert rec.result is None
        assert rec.error is None

    def test_full_init(self):
        rec = TaskRecord(
            task_id="abc",
            status=TaskStatus.PROCESSING,
            progress=0.5,
            stage="正在分离音轨...",
            song_name="晴天",
            input_url="https://bilibili.com/video/BV123",
            input_path="/uploads/abc.mp3",
            result={"bpm": 128},
        )
        assert rec.task_id == "abc"
        assert rec.status == TaskStatus.PROCESSING
        assert rec.progress == 0.5
        assert rec.song_name == "晴天"
        assert rec.result == {"bpm": 128}

    def test_serialization(self):
        rec = TaskRecord(task_id="x", status=TaskStatus.DONE, progress=1.0)
        data = rec.model_dump()
        assert data["task_id"] == "x"
        assert data["status"] == "done"
        assert data["progress"] == 1.0

    def test_progress_bounds(self):
        # progress 必须在 0~1
        rec = TaskRecord(task_id="x", progress=0.75)
        assert rec.progress == 0.75


# ─── TaskStatusResponse ───────────────────────────────────────

class TestTaskStatusResponse:
    def test_basic(self):
        r = TaskStatusResponse(
            task_id="t1",
            status=TaskStatus.PROCESSING,
            progress=0.42,
            stage="正在检测BPM",
        )
        assert r.task_id == "t1"
        assert r.status == TaskStatus.PROCESSING
        assert r.progress == 0.42

    def test_with_error(self):
        r = TaskStatusResponse(
            task_id="t2",
            status=TaskStatus.ERROR,
            progress=0.1,
            stage="失败",
            error="音频文件损坏",
        )
        assert r.error == "音频文件损坏"


# ─── ChordEvent ───────────────────────────────────────────────

class TestChordEvent:
    def test_basic(self):
        c = ChordEvent(start=0.0, end=1.92, chord="Am")
        assert c.start == 0.0
        assert c.end == 1.92
        assert c.chord == "Am"

    def test_complex_chord(self):
        c = ChordEvent(start=3.84, end=5.76, chord="Cmaj7")
        assert c.chord == "Cmaj7"

    def test_serialization(self):
        c = ChordEvent(start=0.0, end=1.0, chord="G")
        data = c.model_dump()
        assert data["chord"] == "G"
        assert data["start"] == 0.0

    def test_negative_start_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            ChordEvent(start=-0.1, end=1.0, chord="C")


# ─── NoteEvent ────────────────────────────────────────────────

class TestNoteEvent:
    def test_required_fields(self):
        n = NoteEvent(time=0.5, note="A3")
        assert n.time == 0.5
        assert n.note == "A3"
        assert n.confidence == 0.0  # 默认值

    def test_full_fields(self):
        n = NoteEvent(
            time=1.2,
            frequency=440.0,
            note="A4",
            string=1,
            fret=5,
            duration="quarter",
            confidence=0.95,
        )
        assert n.fret == 5
        assert n.string == 1
        assert n.confidence == 0.95

    def test_string_bounds(self):
        n = NoteEvent(time=0.0, note="E2", string=6, fret=0)
        assert n.string == 6  # Guitar 6弦

    def test_string_zero_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            NoteEvent(time=0.0, note="E2", string=0)  # 弦号 1-6

    def test_confidence_above_one_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            NoteEvent(time=0.0, note="C4", confidence=1.5)


# ─── BpmInfo ─────────────────────────────────────────────────

class TestBpmInfo:
    def test_basic(self):
        b = BpmInfo(bpm=128, duration_sec=180.5)
        assert b.bpm == 128
        assert b.time_signature == "4/4"  # 默认值
        assert b.beat_times == []

    def test_with_beat_times(self):
        b = BpmInfo(
            bpm=120,
            duration_sec=60.0,
            beat_times=[0.0, 0.5, 1.0, 1.5],
        )
        assert len(b.beat_times) == 4

    def test_bpm_too_low_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            BpmInfo(bpm=10, duration_sec=60.0)  # >= 30

    def test_negative_duration_rejected(self):
        with pytest.raises(pydantic.ValidationError):
            BpmInfo(bpm=120, duration_sec=-1.0)


# ─── ScoreFiles ───────────────────────────────────────────────

class TestScoreFiles:
    def test_all_paths(self):
        sf = ScoreFiles(
            gta="/outputs/abc/score.gta.txt",
            pdf="/outputs/abc/score.pdf",
            mid="/outputs/abc/score.mid",
            gp="/outputs/abc/score.gp",
            json_data="/outputs/abc/score.json",
        )
        assert sf.gta is not None
        assert sf.pdf is not None

    def test_partial_paths(self):
        sf = ScoreFiles(gta="/path/to/score.gta.txt")
        assert sf.gta == "/path/to/score.gta.txt"
        assert sf.pdf is None

    def test_alias_json(self):
        """json_data 字段通过 alias="json" 可用 json=xxx 构造"""
        sf = ScoreFiles(json="/path/to/score.json")
        assert sf.json_data == "/path/to/score.json"


# ─── GuitarTrackResult ────────────────────────────────────────

class TestGuitarTrackResult:
    def test_empty(self):
        g = GuitarTrackResult()
        assert g.chords == []
        assert g.notes == []

    def test_with_data(self):
        chords = [ChordEvent(start=0.0, end=1.0, chord="Am")]
        notes = [NoteEvent(time=0.1, note="A3", string=5, fret=0)]
        g = GuitarTrackResult(chords=chords, notes=notes)
        assert len(g.chords) == 1
        assert len(g.notes) == 1
        assert g.chords[0].chord == "Am"


# ─── BassNoteEvent ────────────────────────────────────────────

class TestBassNoteEvent:
    def test_required(self):
        b = BassNoteEvent(start=0.0, end=0.5, note="E1", midi=28, string=4, fret=0)
        assert b.midi == 28
        assert b.string == 4

    def test_full_fields(self):
        b = BassNoteEvent(
            start=0.0, end=0.5, note="A1", midi=33,
            frequency=55.0, string=3, fret=0,
            chord_root="A", confidence=0.88,
        )
        assert b.chord_root == "A"
        assert b.confidence == 0.88

    def test_bass_string_valid_range(self):
        # Bass 4弦，范围 1-4
        b = BassNoteEvent(start=0.0, end=0.5, note="G2", midi=43, string=1, fret=0)
        assert b.string == 1


# ─── BassTrackResult ─────────────────────────────────────────

class TestBassTrackResult:
    def test_empty(self):
        b = BassTrackResult()
        assert b.notes == []
        assert b.chords == []

    def test_with_notes(self):
        notes = [
            BassNoteEvent(start=0.0, end=0.5, note="E1", midi=28, string=4, fret=0),
            BassNoteEvent(start=0.5, end=1.0, note="A1", midi=33, string=3, fret=0),
        ]
        b = BassTrackResult(notes=notes)
        assert len(b.notes) == 2


# ─── AnalysisResult ──────────────────────────────────────────

class TestAnalysisResult:
    def test_required_fields(self):
        r = AnalysisResult(task_id="x", bpm=120, duration_sec=180.0)
        assert r.task_id == "x"
        assert r.bpm == 120
        assert r.time_signature == "4/4"
        assert r.chords == []  # 兼容字段

    def test_full_structure(self):
        chords = [ChordEvent(start=0.0, end=1.0, chord="Am")]
        notes = [NoteEvent(time=0.1, note="A3")]
        guitar = GuitarTrackResult(chords=chords, notes=notes)
        bass_notes = [BassNoteEvent(start=0.0, end=0.5, note="E1", midi=28, string=4, fret=0)]
        bass = BassTrackResult(notes=bass_notes)
        pitch = PitchResult(notes=notes, total_notes=1, duration_sec=0.1)
        score_files = ScoreFiles(gta="/path/gta.txt")

        r = AnalysisResult(
            task_id="t-abc",
            bpm=128,
            time_signature="4/4",
            duration_sec=60.0,
            guitar=guitar,
            bass=bass,
            chords=chords,
            notes=notes,
            pitch=pitch,
            score_files=score_files,
            gta_text="e|--0---|",
        )
        assert r.guitar is not None
        assert r.bass is not None
        assert r.guitar.chords[0].chord == "Am"
        assert r.bass.notes[0].note == "E1"

    def test_serialization_round_trip(self):
        r = AnalysisResult(
            task_id="round-trip-test",
            bpm=120,
            duration_sec=60.0,
        )
        data = r.model_dump()
        restored = AnalysisResult(**data)
        assert restored.task_id == "round-trip-test"
        assert restored.bpm == 120


# ─── ApiResponse / UploadResponse / ErrorResponse ─────────────

class TestResponses:
    def test_api_response_default(self):
        r = ApiResponse()
        assert r.success is True
        assert r.message == "操作成功"
        assert r.data is None

    def test_api_response_with_data(self):
        r = ApiResponse(success=True, message="OK", data={"key": "value"})
        assert r.data == {"key": "value"}

    def test_upload_response(self):
        r = UploadResponse(task_id="upload-1", message="上传成功", poll_url="/api/task/upload-1")
        assert r.task_id == "upload-1"
        assert r.status == "pending"
        assert "/api/task/upload-1" in r.poll_url

    def test_error_response(self):
        r = ErrorResponse(detail="文件过大", error_code="FILE_TOO_LARGE")
        assert r.detail == "文件过大"
        assert r.error_code == "FILE_TOO_LARGE"
