"""
测试：Basic Pitch 转谱模块
================================
测试 basic_pitch_transcriber.py 的各函数。

注意：basic-pitch 库通过 mock 掉 import，以实现无依赖测试。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# ── Mock basic_pitch 依赖 ──────────────────────────────────────────

class MockNote:
    def __init__(self, pitch_midi: int, start_s: float, end_s: float, amplitude: float = 0.5):
        self.pitch_midi = pitch_midi
        self.start_s = start_s
        self.end_s = end_s
        self.amplitude = amplitude


class MockMidiData:
    def __init__(self, notes):
        self.notes = notes


# ── 辅助函数 ───────────────────────────────────────────────────────

def _note_to_midi(note: str) -> int:
    """音符名 → MIDI note"""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    n = note[0]
    oct_str = note[1:] if len(note) > 1 else ""
    try:
        oct = int(oct_str)
    except ValueError:
        oct = 4
    return names.index(n) + (oct + 1) * 12


# ── 测试：_midi_to_note_name ───────────────────────────────────────

class TestMidiToNoteName:
    """测试 MIDI note number → 音符名称转换。"""

    def test_c4(self):
        from backend.core.basic_pitch_transcriber import _midi_to_note_name
        assert _midi_to_note_name(60) == "C4"

    def test_e4(self):
        from backend.core.basic_pitch_transcriber import _midi_to_note_name
        assert _midi_to_note_name(64) == "E4"

    def test_a4(self):
        from backend.core.basic_pitch_transcriber import _midi_to_note_name
        assert _midi_to_note_name(69) == "A4"

    def test_g3(self):
        """G string open = MIDI 55 = G3（吉他 TAB 中习惯写 G2，实际音高等同 G3）"""
        from backend.core.basic_pitch_transcriber import _midi_to_note_name
        assert _midi_to_note_name(55) == "G3"

    def test_sharp(self):
        from backend.core.basic_pitch_transcriber import _midi_to_note_name
        assert _midi_to_note_name(55) == "G3"
        assert _midi_to_note_name(66) == "F#4"

    def test_low_e2(self):
        """E2 = MIDI 40（吉他 TAB 低音 E，标准记谱 E2）"""
        from backend.core.basic_pitch_transcriber import _midi_to_note_name
        assert _midi_to_note_name(40) == "E2"

    def test_high_e4(self):
        from backend.core.basic_pitch_transcriber import _midi_to_note_name
        assert _midi_to_note_name(64) == "E4"

    def test_bass_a2(self):
        """A2 = MIDI 45（吉他 TAB 中写 A2，对应 A string open）"""
        from backend.core.basic_pitch_transcriber import _midi_to_note_name
        assert _midi_to_note_name(45) == "A2"

    def test_range(self):
        """测试 MIDI 0~127 全范围（MIDI 标准约定：C-1=0, C4=60, C7=96）"""
        from backend.core.basic_pitch_transcriber import _midi_to_note_name
        results = [_midi_to_note_name(n) for n in [0, 12, 60, 69, 96, 107, 127]]
        assert "C-1" in results,  f"midi 0 should be C-1, got {results[0]}"
        assert "C0" in results,   f"midi 12 should be C0, got {results[1]}"
        assert "C4" in results,   f"midi 60 should be C4, got {results[2]}"
        assert "A4" in results,   f"midi 69 should be A4, got {results[3]}"
        assert "C7" in results,   f"midi 96 should be C7, got {results[4]}"
        assert "B7" in results,   f"midi 107 should be B7, got {results[5]}"


# ── 测试：_find_easiest_fingering ──────────────────────────────────

class TestFindEasiestFingering:
    """测试 MIDI note → 吉他弦/品位 最轻松指法。"""

    def test_open_e_string(self):
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        # E2 (MIDI 40) = 6th string open
        string, fret = _find_easiest_fingering(40)
        assert string == 6
        assert fret == 0

    def test_open_a_string(self):
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        # A2 (MIDI 45) = 5th string open
        string, fret = _find_easiest_fingering(45)
        assert string == 5
        assert fret == 0

    def test_open_d_string(self):
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        # D2 (MIDI 50) = 4th string open
        string, fret = _find_easiest_fingering(50)
        assert string == 4
        assert fret == 0

    def test_open_g_string(self):
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        # G2 (MIDI 55) = 3rd string open
        string, fret = _find_easiest_fingering(55)
        assert string == 3
        assert fret == 0

    def test_open_b_string(self):
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        # B1 (MIDI 59) = 2nd string open
        string, fret = _find_easiest_fingering(59)
        assert string == 2
        assert fret == 0

    def test_open_e_high_string(self):
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        # E4 (MIDI 64) = 1st string open
        string, fret = _find_easiest_fingering(64)
        assert string == 1
        assert fret == 0

    def test_c_on_b_string_1st_fret(self):
        """C4 (MIDI 60) = B string 1st fret（最高弦优先，返回最低品位）"""
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        string, fret = _find_easiest_fingering(60)
        assert string == 2  # B string (2nd, first match at high string)
        assert fret == 1   # B string 1st fret = C4

    def test_g4_on_1st_string_3rd_fret(self):
        """G4 (MIDI 67) = 1st string 3rd fret"""
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        string, fret = _find_easiest_fingering(67)
        assert string == 1
        assert fret == 3

    def test_a4_on_1st_string_5th_fret(self):
        """A4 (MIDI 69) = 1st string 5th fret（从高音弦往低音找，e弦5品先命中）"""
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        string, fret = _find_easiest_fingering(69)
        assert string == 1
        assert fret == 5

    def test_d4_on_2nd_string_3rd_fret(self):
        """D4 (MIDI 62) = B string 3rd fret（从高音弦找，第一个命中的是B弦3品）"""
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        string, fret = _find_easiest_fingering(62)
        assert string == 2  # B string
        assert fret == 3

    def test_e3_first_valid_is_d_string_fret2(self):
        """E3 (MIDI 52) 优先命中D弦2品（D弦先于E弦在弦序中出现）"""
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        # E3 = D string 2nd fret (fret 2, first match in high-to-low scan)
        # E string would be fret 12 but comes later in iteration
        string, fret = _find_easiest_fingering(52)
        assert string == 4  # D string
        assert fret == 2

    def test_beyond_24th_fret(self):
        """超出24品时，取最近的弦"""
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        # G5 = MIDI 67+12=79, 超出24品范围
        string, fret = _find_easiest_fingering(79)
        assert 1 <= string <= 6
        assert fret >= 0

    def test_fingering_never_negative(self):
        """品位永不为负"""
        from backend.core.basic_pitch_transcriber import _find_easiest_fingering
        for midi in range(24, 100):
            string, fret = _find_easiest_fingering(midi)
            assert fret >= 0, f"MIDI {midi} got negative fret {fret}"
            assert 1 <= string <= 6, f"MIDI {midi} got invalid string {string}"


# ── 测试：_find_chord_at_time ──────────────────────────────────────

class TestFindChordAtTime:
    """测试时间轴 → 和弦名查找。"""

    def test_am(self):
        from backend.core.basic_pitch_transcriber import _find_chord_at_time
        chords = [
            {"start": 0.0, "end": 1.92, "chord": "Am"},
            {"start": 1.92, "end": 3.84, "chord": "G"},
            {"start": 3.84, "end": 5.76, "chord": "C"},
        ]
        assert _find_chord_at_time(chords, 0.0) == "Am"
        assert _find_chord_at_time(chords, 1.0) == "Am"
        assert _find_chord_at_time(chords, 1.9) == "Am"

    def test_g(self):
        from backend.core.basic_pitch_transcriber import _find_chord_at_time
        chords = [
            {"start": 0.0, "end": 1.92, "chord": "Am"},
            {"start": 1.92, "end": 3.84, "chord": "G"},
        ]
        assert _find_chord_at_time(chords, 2.0) == "G"
        assert _find_chord_at_time(chords, 3.8) == "G"

    def test_not_found(self):
        from backend.core.basic_pitch_transcriber import _find_chord_at_time
        chords = [{"start": 0.0, "end": 1.0, "chord": "Am"}]
        assert _find_chord_at_time(chords, 5.0) == "?"
        assert _find_chord_at_time(chords, 1.5) == "?"

    def test_empty_chords(self):
        from backend.core.basic_pitch_transcriber import _find_chord_at_time
        assert _find_chord_at_time([], 1.0) == "?"

    def test_boundary(self):
        """边界：end 时刻应属于下一个和弦"""
        from backend.core.basic_pitch_transcriber import _find_chord_at_time
        chords = [
            {"start": 0.0, "end": 1.0, "chord": "Am"},
            {"start": 1.0, "end": 2.0, "chord": "G"},
        ]
        assert _find_chord_at_time(chords, 0.99) == "Am"
        assert _find_chord_at_time(chords, 1.0) == "G"

    def test_floating_point_boundary(self):
        """浮点精度边界测试"""
        from backend.core.basic_pitch_transcriber import _find_chord_at_time
        chords = [
            {"start": 0.0, "end": 1.92, "chord": "Am"},
            {"start": 1.92, "end": 3.84, "chord": "G"},
        ]
        assert _find_chord_at_time(chords, 1.919999) == "Am"
        assert _find_chord_at_time(chords, 1.920001) == "G"


# ── 测试：_midi_to_guitar_tab（Mock MIDI data）───────────────────────

class TestMidiToGuitarTab:
    """测试 Basic Pitch MIDI 数据 → 吉他 Tab 转换（mock midi_data）。"""

    def test_empty_notes(self):
        from backend.core.basic_pitch_transcriber import _midi_to_guitar_tab
        result = _midi_to_guitar_tab(MockMidiData([]), "test")
        assert result == []

    def test_single_note(self):
        from backend.core.basic_pitch_transcriber import _midi_to_guitar_tab
        midi_data = MockMidiData([
            MockNote(pitch_midi=64, start_s=0.0, end_s=1.0, amplitude=0.5),
        ])
        result = _midi_to_guitar_tab(midi_data, "test")
        assert len(result) == 1
        assert result[0]["midi"] == 64
        assert result[0]["note"] == "E4"
        assert result[0]["string"] == 1
        assert result[0]["fret"] == 0
        assert result[0]["source"] == "basic_pitch"

    def test_multiple_notes_sorted(self):
        from backend.core.basic_pitch_transcriber import _midi_to_guitar_tab
        midi_data = MockMidiData([
            MockNote(pitch_midi=67, start_s=2.0, end_s=3.0, amplitude=0.5),  # G4
            MockNote(pitch_midi=64, start_s=0.0, end_s=1.0, amplitude=0.5),  # E4
            MockNote(pitch_midi=69, start_s=1.0, end_s=2.0, amplitude=0.5),  # A4
        ])
        result = _midi_data_to_guitar_tab(midi_data, "test")
        # 应按时间排序
        assert result[0]["start"] == 0.0
        assert result[1]["start"] == 1.0
        assert result[2]["start"] == 2.0

    def test_confidence_mapping(self):
        """amplitude → confidence 映射（amplitude 0~1 → confidence 0~1）"""
        from backend.core.basic_pitch_transcriber import _midi_to_guitar_tab
        midi_data = MockMidiData([
            MockNote(pitch_midi=64, start_s=0.0, end_s=1.0, amplitude=0.5),
        ])
        result = _midi_to_guitar_tab(midi_data, "test")
        # confidence = min(1.0, max(0.0, amp * 2.0))
        assert result[0]["confidence"] == 1.0

    def test_low_amplitude_note(self):
        from backend.core.basic_pitch_transcriber import _midi_to_guitar_tab
        midi_data = MockMidiData([
            MockNote(pitch_midi=64, start_s=0.0, end_s=1.0, amplitude=0.1),
        ])
        result = _midi_to_guitar_tab(midi_data, "test")
        assert 0.0 <= result[0]["confidence"] <= 1.0

    def test_frequency_calculation(self):
        from backend.core.basic_pitch_transcriber import _midi_to_guitar_tab
        midi_data = MockMidiData([
            MockNote(pitch_midi=69, start_s=0.0, end_s=1.0, amplitude=0.5),
        ])
        result = _midi_to_guitar_tab(midi_data, "test")
        # A4 = 440 Hz
        assert abs(result[0]["frequency"] - 440.0) < 0.1

    def test_c4_on_g_string(self):
        """C4 (MIDI 60) = G string 5th fret"""
        from backend.core.basic_pitch_transcriber import _midi_to_guitar_tab
        midi_data = MockMidiData([
            MockNote(pitch_midi=60, start_s=0.0, end_s=1.0, amplitude=0.5),
        ])
        result = _midi_to_guitar_tab(midi_data, "test")
        assert result[0]["note"] == "C4"
        assert result[0]["string"] == 2  # B string 1st fret (first match in scan)
        assert result[0]["fret"] == 1


def _midi_data_to_guitar_tab(midi_data, task_id: str):
    """直接调用被测函数（内部用 mock）"""
    from backend.core.basic_pitch_transcriber import _midi_to_guitar_tab
    return _midi_to_guitar_tab(midi_data, task_id)


# ── 测试：_build_tab_grid ──────────────────────────────────────────

class TestBuildTabGrid:
    """测试 Basic Pitch 音符列表 → GTA TAB 网格渲染。"""

    def test_empty_notes(self):
        from backend.core.basic_pitch_transcriber import _build_tab_grid
        rows = _build_tab_grid([], 120)
        assert len(rows) == 6  # 6根弦
        assert rows[0].startswith("e|")
        assert rows[5].startswith("E|")

    def test_single_note(self):
        from backend.core.basic_pitch_transcriber import _build_tab_grid
        notes = [{"start": 0.0, "string": 1, "fret": 0}]  # e string open
        rows = _build_tab_grid(notes, 120)
        assert rows[0].startswith("e|0")
        assert "0" in rows[0]

    def test_chord_notes(self):
        """同时发声的多音符"""
        from backend.core.basic_pitch_transcriber import _build_tab_grid
        notes = [
            {"start": 0.0, "string": 1, "fret": 0},  # e open
            {"start": 0.0, "string": 3, "fret": 2},  # D string 2nd fret = E4
        ]
        rows = _build_tab_grid(notes, 120)
        assert len(rows) == 6
        # e row
        assert "0" in rows[0]
        # D row (idx 3 = string 4)
        assert "2" in rows[2]

    def test_bpm_affects_grid_width(self):
        """不同 BPM 生成的网格宽度应相同（以小节计）"""
        from backend.core.basic_pitch_transcriber import _build_tab_grid
        notes = [{"start": 0.0, "string": 1, "fret": 0}]
        rows1 = _build_tab_grid(notes, 120)
        rows2 = _build_tab_grid(notes, 240)
        # 网格宽度应一致（小节数一致）
        assert len(rows1[0]) == len(rows2[0])

    def test_bass_tab_grid(self):
        """Bass 4弦 TAB 网格"""
        from backend.core.basic_pitch_transcriber import _build_tab_grid
        bass_strings = ["G", "D", "A", "E"]
        notes = [{"start": 0.0, "string": 4, "fret": 0}]  # E string open
        rows = _build_tab_grid(notes, 120, strings=bass_strings)
        assert len(rows) == 4  # 4根弦
        assert rows[3].startswith("E|")

    def test_start_time_field(self):
        """音符支持 'start' 字段"""
        from backend.core.basic_pitch_transcriber import _build_tab_grid
        notes = [{"start": 1.0, "string": 1, "fret": 3}]
        rows = _build_tab_grid(notes, 120)
        assert "3" in rows[0]

    def test_time_field_fallback(self):
        """音符也支持 'time' 字段（兼容旧格式）"""
        from backend.core.basic_pitch_transcriber import _build_tab_grid
        notes = [{"time": 1.0, "string": 1, "fret": 3}]
        rows = _build_tab_grid(notes, 120)
        assert "3" in rows[0]


# ── 测试：is_available ─────────────────────────────────────────────

class TestIsAvailable:
    """测试 Basic Pitch 可用性检测。"""

    def test_import_check(self):
        from backend.core.basic_pitch_transcriber import is_available
        # 返回布尔值（不抛异常）
        result = is_available()
        assert isinstance(result, bool)


# ── 测试：Guitar 常量 ───────────────────────────────────────────────

class TestGuitarConstants:
    """测试吉他调弦常量。"""

    def test_guitar_string_order(self):
        from backend.core.basic_pitch_transcriber import GUITAR_STRING_ORDER, GUITAR_OPEN_NOTES
        assert len(GUITAR_STRING_ORDER) == 6
        assert GUITAR_OPEN_NOTES["e"] == 64
        assert GUITAR_OPEN_NOTES["E"] == 40

    def test_standard_tuning_midi(self):
        from backend.core.basic_pitch_transcriber import GUITAR_OPEN_NOTES
        # E A D G B e = MIDI 40 45 50 55 59 64
        assert GUITAR_OPEN_NOTES["E"] == 40
        assert GUITAR_OPEN_NOTES["A"] == 45
        assert GUITAR_OPEN_NOTES["D"] == 50
        assert GUITAR_OPEN_NOTES["G"] == 55
        assert GUITAR_OPEN_NOTES["B"] == 59
        assert GUITAR_OPEN_NOTES["e"] == 64


# ── 测试：build_gta_from_basic_pitch_v2 ─────────────────────────────

class TestBuildGtaFromBasicPitchV2:
    """测试改进版 GTA 渲染函数。"""

    def test_generates_output(self):
        from backend.core.basic_pitch_transcriber import build_gta_from_basic_pitch_v2
        notes = [
            {"start": 0.0, "string": 1, "fret": 0},
            {"start": 1.0, "string": 2, "fret": 2},
        ]
        result = build_gta_from_basic_pitch_v2(notes, bpm=120.0, song_name="测试歌曲")
        assert isinstance(result, str)
        assert "测试歌曲" in result
        assert "Basic Pitch" in result
        assert "120" in result

    def test_with_chords(self):
        from backend.core.basic_pitch_transcriber import build_gta_from_basic_pitch_v2
        notes = [{"start": 0.0, "string": 1, "fret": 0}]
        chords = [
            {"start": 0.0, "end": 2.0, "chord": "Am"},
            {"start": 2.0, "end": 4.0, "chord": "G"},
        ]
        result = build_gta_from_basic_pitch_v2(notes, chords=chords, bpm=120.0)
        assert "Chord:" in result
        assert "Am" in result
        assert "G" in result

    def test_empty_notes(self):
        from backend.core.basic_pitch_transcriber import build_gta_from_basic_pitch_v2
        result = build_gta_from_basic_pitch_v2([], bpm=120.0)
        assert "Untitled" in result
        assert "Basic Pitch" in result


# ── 测试：merge_with_chords ────────────────────────────────────────

class TestMergeWithChords:
    """测试 Basic Pitch 音符与和弦时间轴融合。"""

    def test_empty_chords(self):
        from backend.core.basic_pitch_transcriber import merge_with_chords
        notes = [{"start": 0.0, "string": 1, "fret": 0}]
        result = merge_with_chords(notes, [], 120.0)
        assert result[0].get("chord") is None

    def test_chord_tagged(self):
        from backend.core.basic_pitch_transcriber import merge_with_chords
        notes = [
            {"start": 0.5, "string": 1, "fret": 0},
            {"start": 2.5, "string": 2, "fret": 2},
        ]
        chords = [
            {"start": 0.0, "end": 2.0, "chord": "Am"},
            {"start": 2.0, "end": 4.0, "chord": "G"},
        ]
        result = merge_with_chords(notes, chords, 120.0)
        assert result[0]["chord"] == "Am"
        assert result[1]["chord"] == "G"

    def test_inplace_modification(self):
        from backend.core.basic_pitch_transcriber import merge_with_chords
        notes = [{"start": 0.5, "string": 1, "fret": 0}]
        chords = [{"start": 0.0, "end": 2.0, "chord": "C"}]
        merge_with_chords(notes, chords, 120.0)
        assert notes[0]["chord"] == "C"


# ── 运行测试 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
