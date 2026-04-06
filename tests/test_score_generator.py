"""
测试：乐谱生成模块 — score_generator.py
========================================
测试 GTA 文本谱构建和 PDF 占位文件生成。
"""

import pytest
from pathlib import Path
from backend.core.score_generator import (
    build_gta_text,
    generate_score,
    GUITAR_STRINGS,
    BASS_STRINGS,
    CHORD_FINGERINGS,
)


class TestGTABuilder:
    """GTA 文本谱构建测试"""

    def test_build_gta_with_empty_chords(self):
        """空和弦列表时仍能生成 GTA 文本"""
        chords = []
        guitar_pitch = {"notes": []}
        bpm = {"bpm": 120, "time_signature": "4/4", "duration_sec": 10.0}

        result = build_gta_text(chords, guitar_pitch, bpm, song_name="Test Song")
        assert isinstance(result, str)
        assert "Test Song" in result
        assert "120" in result
        assert "GUITAR" in result

    def test_build_gta_with_chords(self):
        """和弦列表正常传入时生成包含和弦名的 GTA 文本"""
        chords = [
            {"start": 0.0, "end": 1.92, "chord": "Am"},
            {"start": 1.92, "end": 3.84, "chord": "G"},
            {"start": 3.84, "end": 5.76, "chord": "C"},
            {"start": 5.76, "end": 7.68, "chord": "F"},
        ]
        guitar_pitch = {"notes": []}
        bpm = {"bpm": 120, "time_signature": "4/4", "duration_sec": 10.0}

        result = build_gta_text(chords, guitar_pitch, bpm, song_name="Test")
        assert "Am" in result
        assert "G" in result
        assert "C" in result
        assert "F" in result

    def test_build_gta_with_guitar_notes(self):
        """Guitar 音符传入时生成 TAB 网格"""
        chords = []
        guitar_pitch = {
            "notes": [
                {"time": 0.0,  "string": 1, "fret": 0},
                {"time": 0.25, "string": 2, "fret": 1},
                {"time": 0.5,  "string": 3, "fret": 2},
                {"time": 0.75, "string": 1, "fret": 3},
            ]
        }
        bpm = {"bpm": 120, "time_signature": "4/4", "duration_sec": 10.0}

        result = build_gta_text(chords, guitar_pitch, bpm)
        assert isinstance(result, str)
        # TAB 网格行应该包含 e/B/G/D/A/E 弦标识
        assert any(s in result for s in GUITAR_STRINGS)

    def test_build_gta_with_bass_notes(self):
        """Bass 音符传入时生成 Bass 轨道"""
        chords = []
        guitar_pitch = {"notes": []}
        bass_notes = [
            {"start": 0.0, "end": 0.5, "note": "E1", "string": 4, "fret": 0},
            {"start": 0.5, "end": 1.0, "note": "A1", "string": 3, "fret": 0},
        ]
        bpm = {"bpm": 120, "time_signature": "4/4", "duration_sec": 10.0}

        result = build_gta_text(chords, guitar_pitch, bpm, bass_notes=bass_notes)
        assert "BASS" in result
        assert "E1" in result

    def test_gta_legend_present(self):
        """GTA 文本末尾包含图例说明"""
        result = build_gta_text([], {"notes": []}, {"bpm": 120, "time_signature": "4/4", "duration_sec": 1.0})
        assert "# Legend:" in result
        assert "h=hammer" in result


class TestConstants:
    """常量定义测试"""

    def test_guitar_strings_count(self):
        """吉他应有 6 根弦"""
        assert len(GUITAR_STRINGS) == 6
        assert GUITAR_STRINGS == ["e", "B", "G", "D", "A", "E"]

    def test_bass_strings_count(self):
        """Bass 应有 4 根弦"""
        assert len(BASS_STRINGS) == 4

    def test_chord_fingerings_not_empty(self):
        """和弦指法库不应为空"""
        assert len(CHORD_FINGERINGS) > 10
        assert "C" in CHORD_FINGERINGS
        assert "Am" in CHORD_FINGERINGS
        assert "G" in CHORD_FINGERINGS
        # C 和弦指法：e=0, B=1, G=0, D=2, A=3, 不弹=-1
        fing = CHORD_FINGERINGS["C"]
        assert fing.get(1) == 0  # e弦品格
        assert fing.get(2) == 1  # B弦品格
        assert fing.get(6) == -1 # A弦不弹


class TestGenerateScore:
    """generate_score 主入口测试"""

    def test_generate_score_creates_files(self, tmp_path):
        """generate_score 应在 output_dir 生成 gta / pdf / json 文件"""
        chords = [{"start": 0.0, "end": 1.92, "chord": "Am"}]
        guitar_pitch = {"notes": []}
        bpm = {"bpm": 120, "time_signature": "4/4", "duration_sec": 10.0}
        task_id = "test-123"

        result = generate_score(
            chords=chords,
            guitar_pitch=guitar_pitch,
            bpm=bpm,
            task_id=task_id,
            output_dir=tmp_path,
        )

        assert "gta" in result
        assert "pdf" in result
        assert "json" in result
        assert result["gta"].exists(), "GTA 文件应已创建"
        assert result["pdf"].exists(), "PDF 占位文件应已创建"
        assert result["json"].exists(), "JSON 文件应已创建"

        # 验证 GTA 文件内容非空
        gta_content = result["gta"].read_text(encoding="utf-8")
        assert len(gta_content) > 0
        assert "Am" in gta_content

        # 验证 JSON 文件可解析
        import json
        json_content = result["json"].read_text(encoding="utf-8")
        parsed = json.loads(json_content)
        assert parsed["task_id"] == task_id
        assert parsed["bpm"] == 120

    def test_generate_score_with_bass(self, tmp_path):
        """带 Bass 数据的 generate_score 应生成双轨 GTA"""
        chords = []
        guitar_pitch = {"notes": []}
        bass_notes = [
            {"start": 0.0, "end": 0.5, "note": "E1", "string": 4, "fret": 0},
        ]
        bpm = {"bpm": 120, "time_signature": "4/4", "duration_sec": 10.0}

        result = generate_score(
            chords=chords,
            guitar_pitch=guitar_pitch,
            bpm=bpm,
            task_id="bass-test",
            output_dir=tmp_path,
            bass_notes=bass_notes,
        )
        gta_content = result["gta"].read_text(encoding="utf-8")
        assert "BASS" in gta_content
        assert "E1" in gta_content
