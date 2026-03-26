"""
Guitar Pro 7 (MusicXML) 乐谱生成器
=====================================
将 Guitar + Bass 双轨音符/和弦数据转换为 MusicXML 格式，
可直接导入 Guitar Pro 7 / 6 / 5，以及 MuseScore、FL Studio 等 DAW。

MusicXML 是 W3C 标准，Guitar Pro 7 完全支持导入。
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ─── 音符名映射 ─────────────────────────────────────────────────
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Guitar 标准调弦 MIDI（第1弦到第6弦，细到粗）
GUITAR_TUNING = [64, 59, 55, 50, 45, 40]  # e4, B3, G3, D3, A2, E2

# Bass 标准调弦 MIDI（第1弦到第4弦，细到粗）
BASS_TUNING = [43, 38, 33, 28]  # G2, D2, A1, E1


def midi_to_step(midi: int) -> tuple[str, int]:
    """MIDI note → (音名, 八度)"""
    pitch_class = NOTE_NAMES[midi % 12]
    octave = (midi // 12) - 1
    return pitch_class, octave


def guitar_midi_to_string_fret(midi: int, capo: int = 0) -> tuple[int, int]:
    """
    给定 MIDI pitch，计算 Guitar 指法（弦号 + 品位）。
    从低把位开始找（品位 0~24），返回 (string, fret)。

    capo > 0 时，所有空弦音自动升高半音数量。
    """
    effective = midi - capo  # 应用 capo 后的目标音
    best_string = 1
    best_fret = max(0, effective - GUITAR_TUNING[0])  # 默认第1弦品位
    best_dist = float("inf")

    for si, open_midi in enumerate(GUITAR_TUNING):
        string_num = si + 1  # 1-indexed
        fret = effective - open_midi
        if 0 <= fret <= 24:
            dist = abs(fret)  # 优先低品位
            if dist < best_dist or (dist == best_dist and fret < best_fret):
                best_dist = dist
                best_string = string_num
                best_fret = fret

    return best_string, max(0, best_fret)


def bass_midi_to_string_fret(midi: int) -> tuple[int, int]:
    """MIDI pitch → Bass (弦号 1-4, 品位 0-20)"""
    best_string = 1
    best_fret = max(0, midi - BASS_TUNING[0])
    best_dist = float("inf")

    for si, open_midi in enumerate(BASS_TUNING):
        string_num = si + 1
        fret = midi - open_midi
        if 0 <= fret <= 20:
            dist = abs(fret)
            if dist < best_dist:
                best_dist = dist
                best_string = string_num
                best_fret = fret

    return best_string, max(0, best_fret)


def build_musicxml(
    chords: List[Dict[str, Any]],
    guitar_notes: List[Dict[str, Any]],
    bass_notes: List[Dict[str, Any]],
    bpm: int,
    time_signature: str = "4/4",
    title: str = "Untitled",
    artist: str = "AI Transcription",
    capo: int = 0,
    transpose: int = 0,
) -> str:
    """
    生成完整的 MusicXML 文档（Guitar + Bass 双轨）。

    参数:
        chords:         Guitar 和弦列表 [{"start": float, "end": float, "chord": str}, ...]
        guitar_notes:   Guitar 音符列表 [{"start": float, "end": float, "pitch": int, ...}, ...]
        bass_notes:     Bass 音符列表（格式同上）
        bpm:            节拍速度
        time_signature: 如 "4/4"
        title:          曲目标题
        artist:         艺术家
        capo:           Capo 品位（0=None）
        transpose:      半音转调值（正值=升，负值=降）
    """
    divisions = 480  # 每个四分音符的 ticks 数
    beats_str, beat_type = time_signature.split("/")

    # ─── XML 片段生成 ────────────────────────────────────────────

    def xml_header() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" '
            '"http://www.musicxml.org/dtds/partwise.dtd">\n'
        )

    def part_list_xml() -> str:
        s = '  <part-list>\n'
        s += '    <score-part id="P1"><part-name>Guitar</part-name></score-part>\n'
        s += '    <score-part id="P2"><part-name>Bass</part-name></score-part>\n'
        s += '  </part-list>\n'
        return s

    def _chord_symbol(chord_name: str) -> str:
        """简单化和弦名（如 Am7→A, Cmaj7→C）"""
        return chord_name.rstrip("0123456789majminaddsusdomaugb")

    def _make_duration(start: float, end: float, bpm_val: int, divs: int) -> tuple[int, str]:
        """秒 → MusicXML duration (ticks) + type"""
        dur_sec = max(0.01, end - start)
        qnotes = dur_sec * bpm_val / 60.0
        ticks = int(round(qnotes * divs))
        # type: whole/half/quarter/eighth/16th/32nd
        types = ["whole", "half", "quarter", "eighth", "16th", "32nd"]
        dur_log = max(0, min(5, int(round(-(dur_sec * bpm_val / 60.0 - 1).bit_length() + 3))))
        # simpler: derive from divisions ratio
        types_by_div = [
            (divs * 4, "whole"),
            (divs * 2, "half"),
            (divs, "quarter"),
            (divs // 2, "eighth"),
            (divs // 4, "16th"),
            (divs // 8, "32nd"),
        ]
        chosen = "quarter"
        for threshold, tname in types_by_div:
            if ticks >= threshold:
                chosen = tname
                break
        return max(1, ticks), chosen

    def guitar_measure(chord_obj: Dict[str, Any], gn_list: List[Dict[str, Any]], meas_num: int) -> str:
        """生成单个 Guitar 小节（和弦 + 音符）"""
        dur_ticks, dur_type = _make_duration(chord_obj["start"], chord_obj["end"], bpm, divisions)
        symbol = _chord_symbol(chord_obj["chord"])

        notes_xml = ""
        # 和弦休止
        notes_xml += f'      <note>\n        <pitch>\n          <step>G</step>\n          <alter>0</alter>\n          <octave>5</octave>\n        </pitch>\n        <duration>{dur_ticks}</duration>\n        <type>{dur_type}</type>\n        <rest/>\n      </note>\n'

        # 吉他音符（该小节时间段内的）
        for gn in gn_list:
            if gn["start"] >= chord_obj["start"] and gn["start"] < chord_obj["end"]:
                pitch_midi = gn.get("pitch", 60) + transpose
                step, octave = midi_to_step(pitch_midi)
                alter = 1 if "#" in step or "♯" in step else (-1 if "b" in step else 0)
                step = step.replace("#", "").replace("b", "").replace("♯", "").replace("♭", "")
                g_string, g_fret = guitar_midi_to_string_fret(pitch_midi, capo)
                n_dur, n_type = _make_duration(gn["start"], min(gn["end"], chord_obj["end"]), bpm, divisions)
                notes_xml += (
                    f'      <note>\n'
                    f'        <pitch>\n'
                    f'          <step>{step}</step>\n'
                    f'          <alter>{alter}</alter>\n'
                    f'          <octave>{octave}</octave>\n'
                    f'        </pitch>\n'
                    f'        <duration>{n_dur}</duration>\n'
                    f'        <type>{n_type}</type>\n'
                    f'        <notations>\n'
                    f'          <technical>\n'
                    f'            <string>{g_string}</string>\n'
                    f'            <fret>{g_fret}</fret>\n'
                    f'          </technical>\n'
                    f'        </notations>\n'
                    f'      </note>\n'
                )

        chord_xml = (
            f'    <measure number="{meas_num}">\n'
            f'      <direction placement="above">\n'
            f'        <direction-type>\n'
            f'          <harmony>\n'
            f'            <root>\n'
            f'              <root-step>{symbol}</root-step>\n'
            f'            </root>\n'
            f'          </harmony>\n'
            f'        </direction-type>\n'
            f'      </direction>\n'
            + notes_xml +
            f'    </measure>\n'
        )
        return chord_xml

    def bass_measure_note(note_obj: Dict[str, Any], meas_num: int, is_first: bool) -> str:
        """生成 Bass 音符"""
        pitch_midi = note_obj.get("pitch", 40)
        step, octave = midi_to_step(pitch_midi)
        alter = 1 if "#" in step else (-1 if "b" in step else 0)
        step = step.replace("#", "").replace("b", "")
        dur_ticks, dur_type = _make_duration(note_obj["start"], note_obj["end"], bpm, divisions)
        b_string, b_fret = bass_midi_to_string_fret(pitch_midi)
        attrs = ""
        if is_first:
            attrs = (
                f'      <attributes>\n'
                f'        <divisions>{divisions}</divisions>\n'
                f'        <key><fifths>0</fifths></key>\n'
                f'        <time><beats>{beats_str}</beats><beat-type>{beat_type}</beat-type></time>\n'
                f'        <clef sign="TAB" line="5"/>\n'
                f'      </attributes>\n'
            )
        return (
            f'    <measure number="{meas_num}">\n'
            + attrs +
            f'      <note>\n'
            f'        <pitch>\n'
            f'          <step>{step}</step>\n'
            f'          <alter>{alter}</alter>\n'
            f'          <octave>{octave}</octave>\n'
            f'        </pitch>\n'
            f'        <duration>{dur_ticks}</duration>\n'
            f'        <type>{dur_type}</type>\n'
            f'        <notations>\n'
            f'          <technical>\n'
            f'            <string>{b_string}</string>\n'
            f'            <fret>{b_fret}</fret>\n'
            f'          </technical>\n'
            f'        </notations>\n'
            f'      </note>\n'
            f'    </measure>\n'
        )

    # ─── Guitar Part ────────────────────────────────────────────
    guitar_xml = '  <part id="P1">\n'
    guitar_xml += '    <measure number="1">\n'
    guitar_xml += (
        f'      <attributes>\n'
        f'        <divisions>{divisions}</divisions>\n'
        f'        <key><fifths>0</fifths></key>\n'
        f'        <time><beats>{beats_str}</beats><beat-type>{beat_type}</beat-type></time>\n'
        f'        <clef sign="TAB" line="6">\n'
        f'          <staff-tuning line="1" tuning-step="E" tuning-octave="4" tuning-alter="0" tuning-step="B" tuning-octave="3" tuning-alter="0" tuning-step="G" tuning-octave="3" tuning-alter="0" tuning-step="D" tuning-octave="3" tuning-alter="0" tuning-step="A" tuning-octave="2" tuning-alter="0" tuning-step="E" tuning-octave="2" tuning-alter="0"/>\n'
        f'        </clef>\n'
        f'      </attributes>\n'
        f'      <direction placement="above">\n'
        f'        <direction-type>\n'
        f'          <metronome><beat-unit>quarter</beat-unit><per-minute>{bpm}</per-minute></metronome>\n'
        f'        </direction-type>\n'
        f'      </direction>\n'
    )
    if capo > 0:
        guitar_xml += (
            f'      <direction placement="above">\n'
            f'        <direction-type>\n'
            f'          <words>Capo {capo} fret</words>\n'
            f'        </direction-type>\n'
            f'      </direction>\n'
        )
    guitar_xml += '    </measure>\n'

    for i, chord_obj in enumerate(chords):
        guitar_xml += guitar_measure(chord_obj, guitar_notes, i + 2)
    guitar_xml += '  </part>\n'

    # ─── Bass Part ───────────────────────────────────────────────
    bass_xml = '  <part id="P2">\n'
    bass_added_attrs = False
    for i, note_obj in enumerate(bass_notes):
        if not bass_added_attrs:
            bass_xml += (
                f'    <measure number="{i+1}">\n'
                f'      <attributes>\n'
                f'        <divisions>{divisions}</divisions>\n'
                f'        <key><fifths>0</fifths></key>\n'
                f'        <time><beats>{beats_str}</beats><beat-type>{beat_type}</beat-type></time>\n'
                f'        <clef sign="TAB" line="5">\n'
                f'          <staff-tuning line="1" tuning-step="G" tuning-octave="2" tuning-alter="0" tuning-step="D" tuning-octave="2" tuning-alter="0" tuning-step="A" tuning-octave="1" tuning-alter="0" tuning-step="E" tuning-octave="1" tuning-alter="0"/>\n'
                f'        </clef>\n'
                f'      </attributes>\n'
                f'    </measure>\n'
            )
            bass_added_attrs = True
        bass_xml += bass_measure_note(note_obj, i + 2, i == 0)
    bass_xml += '  </part>\n'

    # ─── 完整文档 ────────────────────────────────────────────────
    xml = (
        xml_header()
        + '<score-partwise version="3.1">\n'
        + f'  <work><work-title>{esc_xml(title)}</work-title></work>\n'
        + f'  <identification><creator type="composer">AI Transcription</creator>'
        + f'<encoding><software>AI Guitar Tab Transcriber</software>'
        + f'<encoding-date>2026</encoding-date></encoding></identification>\n'
        + part_list_xml()
        + guitar_xml
        + bass_xml
        + '</score-partwise>\n'
    )
    return xml


def esc_xml(s: str) -> str:
    """转义 XML 特殊字符"""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))


def build_musicxml_file(
    chords: List[Dict[str, Any]],
    guitar_notes: List[Dict[str, Any]],
    bass_notes: List[Dict[str, Any]],
    bpm: int,
    output_path: Path,
    title: str = "Guitar Tab",
    time_signature: str = "4/4",
    capo: int = 0,
    transpose: int = 0,
) -> Path:
    """生成 MusicXML 文件并写入磁盘"""
    xml_content = build_musicxml(
        chords=chords,
        guitar_notes=guitar_notes,
        bass_notes=bass_notes,
        bpm=bpm,
        time_signature=time_signature,
        title=title,
        capo=capo,
        transpose=transpose,
    )
    output_path.write_text(xml_content, encoding="utf-8")
    logger.info(f"MusicXML 已生成: {output_path}")
    return output_path
