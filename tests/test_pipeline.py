"""
测试：Pipeline 主流程 + GTA 文本谱生成
==========================================
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestPipelineImports:
    """确保所有模块可导入"""

    def test_import_pipeline(self):
        from backend.core import pipeline
        assert hasattr(pipeline, "run_pipeline")

    def test_import_bpm(self):
        from backend.core import bpm_detector
        assert hasattr(bpm_detector, "detect_bpm")

    def test_import_chord(self):
        from backend.core import chord_recognizer
        assert hasattr(chord_recognizer, "recognize_chords")

    def test_import_score_gen(self):
        from backend.core import score_generator
        assert hasattr(score_generator, "build_gta_text")

    def test_import_schemas(self):
        from backend.models import schemas
        assert hasattr(schemas, "TaskRecord")


class TestGTAGenerator:
    """GTA 文本谱生成测试"""

    def test_generate_gta_text(self):
        from backend.core.score_generator import build_gta_text as generate_gta_text

        chords = [
            {"start": 0.0, "end": 1.92, "chord": "Am"},
            {"start": 1.92, "end": 3.84, "chord": "G"},
            {"start": 3.84, "end": 5.76, "chord": "C"},
        ]

        guitar_pitch = {"notes": [
            {"time": 0.1, "string": 5, "fret": 0, "note": "A3"},
            {"time": 0.5, "string": 3, "fret": 2, "note": "E4"},
        ]}

        bpm = {"bpm": 120, "time_signature": "4/4", "duration_sec": 10.0}

        text = generate_gta_text(
            chords=chords,
            guitar_pitch=guitar_pitch,
            bpm=bpm,
            song_name="测试歌曲",
            artist="测试艺术家",
        )

        assert isinstance(text, str)
        assert "测试歌曲" in text
        assert "Tempo: 120 BPM" in text
        assert "Am" in text
        assert "G" in text
        assert "C" in text
        print(f"\n✅ GTA 文本谱生成成功，共 {len(text)} 字符")


class TestScoreGenerator:
    """乐谱生成测试"""

    def test_build_gta_text_returns_multiline(self):
        from backend.core.score_generator import build_gta_text

        chords = [{"start": 0.0, "end": 1.92, "chord": "Am"}]
        guitar_pitch = {"notes": [{"time": 0.1, "string": 5, "fret": 0, "note": "A3"}]}
        bpm = {"bpm": 120, "time_signature": "4/4", "duration_sec": 5.0}
        text = build_gta_text(chords=chords, guitar_pitch=guitar_pitch, bpm=bpm, song_name="Test")
        # 验证是多行格式
        assert "\n" in text
        assert "e|" in text or "|0" in text
