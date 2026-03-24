"""
乐谱生成器 — Guitar + Bass 双轨 GTA 文本谱 + PDF 输出
======================================================
将 Guitar 和 Bass 的音符/和弦 + BPM 数据转换为可读格式：
1. GTA 文本六线谱（ASCII 格式，Guitar 6弦 + Bass 4弦）
2. PDF 乐谱（使用 fpdf2 生成可打印 PDF）
3. JSON 格式（供前端展示）
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ─── 弦名常量 ─────────────────────────────────────────────────────
GUITAR_STRINGS = ["e", "B", "G", "D", "A", "E"]   # 吉他 6 弦（细→粗）
BASS_STRINGS   = ["G", "D", "A", "E"]             # Bass 4 弦（细→粗）

MAX_FRET       = 24
MAX_BASS_FRET  = 20

# ─── 吉他指法库 ───────────────────────────────────────────────────
# {弦号(1-6): 品位}，0=空弦，-1=不弹
# 调弦：E A D G B e
CHORD_FINGERINGS: Dict[str, Dict[int, int]] = {
    "C":    {1: 0,  2: 1,  3: 0,  4: 2,  5: 3,  6: -1},
    "Cm":   {1: 0,  2: 1,  3: 0,  4: 3,  5: 3,  6: -1},
    "D":    {1: 2,  2: 3,  3: 2,  4: 0,  5: -1, 6: -1},
    "Dm":   {1: 1,  2: 3,  3: 2,  4: 0,  5: -1, 6: -1},
    "E":    {1: 0,  2: 0,  3: 1,  4: 2,  5: 2,  6: 0},
    "Em":   {1: 0,  2: 0,  3: 0,  4: 2,  5: 2,  6: 0},
    "F":    {1: 1,  2: 1,  3: 2,  4: 3,  5: 3,  6: 1},
    "Fm":   {1: 1,  2: 1,  3: 3,  4: 3,  5: 1,  6: 1},
    "G":    {1: 3,  2: 0,  3: 0,  4: 0,  5: 2,  6: 3},
    "Gm":   {1: 3,  2: 3,  3: 3,  4: 5,  5: 5,  6: 3},
    "A":    {1: 0,  2: 2,  3: 2,  4: 2,  5: 0,  6: -1},
    "Am":   {1: 0,  2: 1,  3: 2,  4: 2,  5: 0,  6: -1},
    "B":    {1: 2,  2: 4,  3: 4,  4: 4,  5: 2,  6: -1},
    "Bm":   {1: 2,  2: 3,  3: 4,  4: 4,  5: 2,  6: -1},
    "A7":   {1: 0,  2: 2,  3: 0,  4: 2,  5: 0,  6: -1},
    "Am7":  {1: 0,  2: 1,  3: 0,  4: 2,  5: 0,  6: -1},
    "C7":   {1: 0,  2: 1,  3: 3,  4: 2,  5: 3,  6: -1},
    "D7":   {1: 2,  2: 1,  3: 2,  4: 0,  5: -1, 6: -1},
    "E7":   {1: 0,  2: 0,  3: 1,  4: 0,  5: 2,  6: 0},
    "G7":   {1: 1,  2: 0,  3: 0,  4: 0,  5: 2,  6: 3},
    "B7":   {1: 2,  2: 1,  3: 2,  4: 1,  5: 2,  6: -1},
    "F#m":  {1: 2,  2: 2,  3: 4,  4: 4,  5: 0,  6: 2},
    "Dsus4":{1: 3,  2: 3,  3: 2,  4: 0,  5: -1, 6: -1},
    "Asus4":{1: 0,  2: 3,  3: 2,  4: 2,  5: 0,  6: -1},
    "Esus4":{1: 0,  2: 0,  3: 2,  4: 2,  5: 2,  6: 0},
}

# ─── Bass 指法库 ─────────────────────────────────────────────────
# 标准 Bass 调弦：G2(98Hz) D2(73Hz) A1(55Hz) E1(41Hz)
# 4 弦，从细到粗编号 1-4
# 辅助：从音符名推断品位（快速查找）
BASS_OPEN_STRINGS: Dict[str, int] = {"G": 43, "D": 38, "A": 33, "E": 28}  # MIDI note


# ─── 主入口 ───────────────────────────────────────────────────────

def generate_score(
    chords: List[Dict[str, Any]],
    guitar_pitch: Dict[str, Any],
    bpm: Dict[str, Any],
    task_id: str,
    output_dir: Path,
    bass_notes: Optional[List[Dict[str, Any]]] = None,
    bass_chords: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Path]:
    """
    生成 Guitar + Bass 乐谱文件：GTA 文本谱 + PDF + JSON。

    参数:
        chords:       Guitar 和弦列表
        guitar_pitch: Guitar 音符数据 {"notes": [...]}
        bpm:          节拍信息 {"bpm": int, ...}
        task_id:      任务ID
        output_dir:   输出目录
        bass_notes:   Bass 音符列表（可选）
        bass_chords:  Bass 和弦列表（可选）
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. GTA 文本谱 ────────────────────────────────────────────
    gta_text = build_gta_text(
        chords, guitar_pitch, bpm,
        bass_notes=bass_notes,
        song_name="AI Guitar Tab",
    )
    gta_path = output_dir / f"{task_id}.gta.txt"
    gta_path.write_text(gta_text, encoding="utf-8")
    logger.info(f"[{task_id}] GTA 文本谱（含 Guitar+Bass）已生成")

    # ── 2. PDF ────────────────────────────────────────────────────
    pdf_path = output_dir / f"{task_id}.pdf"
    try:
        build_pdf_score(gta_text, bpm, pdf_path)
        logger.info(f"[{task_id}] PDF 乐谱已生成")
    except Exception as exc:
        logger.warning(f"[{task_id}] PDF 生成失败: {exc}")
        pdf_path = _create_empty_pdf(output_dir, task_id)

    # ── 3. JSON ──────────────────────────────────────────────────
    result_json = {
        "task_id": task_id,
        "bpm": bpm.get("bpm", 120),
        "time_signature": bpm.get("time_signature", "4/4"),
        "guitar": {
            "chords": chords,
            "notes": guitar_pitch.get("notes", []),
        },
        "bass": {
            "notes": bass_notes or [],
            "chords": bass_chords or [],
        },
        "duration_sec": bpm.get("duration_sec", 0),
        "gta_text": gta_text,
    }
    json_path = output_dir / f"{task_id}.json"
    json_path.write_text(json.dumps(result_json, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"[{task_id}] JSON 结果已生成")

    return {"gta": gta_path, "pdf": pdf_path, "json": json_path}


def build_gta_text(
    chords: List[Dict[str, Any]],
    guitar_pitch: Dict[str, Any],
    bpm: Dict[str, Any],
    song_name: str = "Untitled",
    artist: str = "AI Guitar Tab",
    bass_notes: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    构建 Guitar + Bass 双轨 GTA ASCII 乐谱文本。
    """
    bpm_val = bpm.get("bpm", 120) if isinstance(bpm, dict) else int(bpm)

    lines: List[str] = []
    lines.append("=" * 64)
    lines.append(f"  🎸 {song_name} — {artist}")
    lines.append("  Generated by AI Guitar Tab Transcriber  |  Dual Track: Guitar + Bass")
    lines.append("=" * 64)
    lines.append(f" Tempo: {bpm_val} BPM   |   Time: {bpm.get('time_signature', '4/4')}")
    lines.append("")

    # ── Guitar 轨道 ───────────────────────────────────────────────
    lines.append("━" * 27 + " [ GUITAR ] " + "━" * 22)
    if chords:
        names = " — ".join(c.get("chord", "?") for c in chords[:8])
        lines.append(f"Chords: {names}")
    else:
        lines.append("Chords: (none)")
    lines.append("")

    guitar_notes = guitar_pitch.get("notes", [])
    if guitar_notes:
        tab = _build_tab_grid(guitar_notes, bpm_val, GUITAR_STRINGS)
        for row in tab:
            lines.append(row)
    else:
        tab = _build_chord_tab(chords, bpm_val)
        for row in tab:
            lines.append(row)
    lines.append("")

    # ── Bass 轨道 ─────────────────────────────────────────────────
    has_bass = bool(bass_notes and len(bass_notes) > 0)
    lines.append("━" * 27 + " [ BASS ] " + "━" * 26)
    if has_bass:
        uniq = list(dict.fromkeys(n.get("note", "?") for n in bass_notes[:16]))
        lines.append(f"Bass Line: {' — '.join(uniq)}")
        lines.append("(Standard Bass: G2 D2 A1 E1  |  4 strings)")
        lines.append("")
        bass_tab = _build_bass_tab_grid(bass_notes, bpm_val)
        for row in bass_tab:
            lines.append(row)
    else:
        lines.append("(Bass not detected — ensure Demucs separated the bass stem)")
    lines.append("")

    lines.append("=" * 64)
    lines.append("# Legend:")
    lines.append("# Guitar: e|B|G|D|A|E  |  Bass: G|D|A|E")
    lines.append("# 数字 = 品(0=open),  -=rest,  |=measure bar")
    lines.append("# h=hammer  p=pulloff  b=bend  /=slide-up  \\=slide-down")
    lines.append("=" * 64)
    return "\n".join(lines)


# ─── Guitar TAB 网格 ─────────────────────────────────────────────

def _build_tab_grid(
    notes: List[Dict[str, Any]],
    bpm_val: int,
    strings: Optional[List[str]] = None,
) -> List[str]:
    """将音符列表渲染为 GTA TAB 网格（通用，支持任意弦数）。"""
    string_list = strings or GUITAR_STRINGS
    n_strings = len(string_list)

    sorted_notes = sorted(notes, key=lambda x: x.get("time", 0))

    beat_char = 2                                  # 1 char ≈ 16th-note
    measures  = max(len(sorted_notes) // 4 + 1, 8)
    chars_per = beat_char * 4
    total     = measures * chars_per

    grid: Dict[str, List[str]] = {s: ["-"] * total for s in string_list}

    eighth = 60.0 / bpm_val / 2.0
    for note in sorted_notes:
        t   = note.get("time", 0)
        sid = note.get("string", n_strings)
        fret = note.get("fret", 0)
        # string 1→idx 0 (high), string 6→idx 5 (low) for guitar
        idx = max(0, min(n_strings - 1, n_strings - sid))
        pos = min(int(t / eighth), total - 1)
        fc  = str(fret) if fret is not None else "0"
        if len(fc) == 1:
            grid[string_list[idx]][pos] = fc

    result = []
    for s in string_list:
        row = "".join(c + ("|" if (i + 1) % 16 == 0 and i < total - 1 else "")
                      for i, c in enumerate(grid[s]))
        result.append(f"{s}|{row}|")
    return result


def _build_chord_tab(
    chords: List[Dict[str, Any]],
    bpm_val: int,
) -> List[str]:
    """无音符时，用和弦生成简化 TAB 谱。"""
    if not chords:
        return ["# No chord data"]
    beat_char  = 2
    total      = beat_char * 2 * min(len(chords), 16)
    grid: Dict[str, List[str]] = {s: ["-"] * total for s in GUITAR_STRINGS}

    for i, chord in enumerate(chords[:16]):
        name = chord.get("chord", "?")
        fing = CHORD_FINGERINGS.get(name, CHORD_FINGERINGS.get("C", {}))
        pos  = i * beat_char * 2
        for str_num, fret in fing.items():
            if fret < 0:
                continue
            idx = max(0, min(5, 6 - str_num))
            fc  = str(fret)
            for j, ch in enumerate(fc):
                p = pos + j
                if p < total:
                    grid[GUITAR_STRINGS[idx]][p] = ch

    result = []
    for s in GUITAR_STRINGS:
        row = "".join(c for i, c in enumerate(grid[s]))
        result.append(f"{s}|{row}|")
    return result


# ─── Bass TAB 网格 ───────────────────────────────────────────────

def _build_bass_tab_grid(
    bass_notes: List[Dict[str, Any]],
    bpm_val: int,
) -> List[str]:
    """
    将 Bass 音符列表渲染为 4 弦 GTA 谱。
    Bass 弦（细→粗）：G(1) D(2) A(3) E(4)
    """
    sorted_notes = sorted(bass_notes, key=lambda x: x.get("start", 0))

    beat_char = 2
    measures  = max(len(sorted_notes) // 4 + 1, 8)
    total     = measures * beat_char * 4

    grid: Dict[str, List[str]] = {s: ["-"] * total for s in BASS_STRINGS}

    eighth = 60.0 / bpm_val / 2.0

    for note in sorted_notes:
        start = note.get("start", 0)
        end   = note.get("end", start + 0.5)
        # string 1=G, 2=D, 3=A, 4=E  →  列表索引 0,1,2,3
        sid = note.get("string", 4)
        idx = max(0, min(3, sid - 1))
        fret = note.get("fret", 0)

        pos = min(int(start / eighth), total - 1)
        end_pos = min(int(end / eighth), total - 1)

        # 写品位数字（支持2位）
        fc = str(fret) if fret is not None else "0"
        if len(fc) == 1:
            grid[BASS_STRINGS[idx]][pos] = fc
        elif len(fc) == 2:
            grid[BASS_STRINGS[idx]][pos] = fc[0]
            if pos + 1 <= end_pos:
                grid[BASS_STRINGS[idx]][pos + 1] = fc[1]

        # 画时值（横杠）
        for p in range(pos + 1, min(end_pos + 1, total)):
            if grid[BASS_STRINGS[idx]][p] == "-":
                grid[BASS_STRINGS[idx]][p] = "-"

    result = []
    for s in BASS_STRINGS:
        row = "".join(c + ("|" if (i + 1) % 16 == 0 and i < total - 1 else "")
                      for i, c in enumerate(grid[s]))
        result.append(f"{s}|{row}|")
    return result


# ─── PDF 生成 ────────────────────────────────────────────────────

def build_pdf_score(gta_text: str, bpm: Dict[str, Any], output_path: Path) -> None:
    """使用 fpdf2 生成双轨乐谱 PDF。"""
    try:
        from fpdf import FPDF
    except ImportError:
        raise ImportError("fpdf2 未安装: pip install fpdf2")

    bpm_val = bpm.get("bpm", 120) if isinstance(bpm, dict) else int(bpm)

    class GuitarTabPDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 13)
            self.cell(0, 8, "AI Guitar Tab Transcriber  |  Guitar + Bass", ln=True, align="C")
            self.set_font("Helvetica", "", 9)
            self.cell(0, 5, f"Tempo: {bpm_val} BPM  |  Time: {bpm.get('time_signature','4/4')}", ln=True, align="C")
            self.ln(2)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 8, f"Page {self.page_no()}", align="C")

    pdf = GuitarTabPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Courier", size=7.5)

    for line in gta_text.split("\n"):
        if line.startswith("="):
            pdf.set_font("Courier", size=9)
            pdf.ln(1)
        elif line.startswith("#"):
            pdf.set_font("Helvetica", style="I", size=7)
            pdf.set_text_color(120, 120, 120)
        elif "GUITAR" in line or "BASS" in line:
            pdf.set_font("Helvetica", "B", size=9)
            pdf.set_text_color(50, 50, 180)
        else:
            pdf.set_font("Courier", size=7.5)
            pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 3.5, line, ln=True)

    pdf.output(str(output_path))


def _create_empty_pdf(output_dir: Path, task_id: str) -> Path:
    """PDF 生成失败时的占位文件。"""
    out = output_dir / f"{task_id}.pdf"
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=16)
        pdf.cell(0, 10, "AI Guitar Tab — PDF unavailable", ln=True, align="C")
        pdf.set_font("Courier", size=10)
        pdf.ln(5)
        pdf.cell(0, 6, "Use the .gta.txt file instead.", ln=True, align="C")
        pdf.output(str(out))
    except Exception:
        out.write_text("PDF not available. See .gta.txt for the score.")
    return out


# ─── MIDI 生成（含 Bass）─────────────────────────────────────────

def build_midi_file(
    guitar_chords: list,
    bass_notes: Optional[list],
    bpm: int,
    output_path: Path,
) -> Path:
    """
    生成含 Guitar + Bass 双轨的 MIDI 文件。
    Guitar Pro / REAPER 可直接导入。
    """
    try:
        import mido
        from mido import Message, MidiFile, MidiTrack, MetaMessage
    except ImportError:
        raise ImportError("mido 未安装: pip install mido")

    mid = MidiFile(ticks_per_beat=480)
    tpq = 480

    # Tempo track
    t_track = MidiTrack()
    t_track.append(MetaMessage("set_tempo", tempo=mido.bpm_to_ticktime(bpm, tpq, 500000)))
    t_track.append(MetaMessage("time_signature", numerator=4, denominator=4))
    mid.tracks.append(t_track)

    # Guitar track (channel 0, program 24 = nylon guitar)
    g_track = MidiTrack()
    g_track.append(Message("program_change", program=24, time=0, channel=0))
    _add_chords_to_track(g_track, guitar_chords, bpm, tpq, channel=0)
    mid.tracks.append(g_track)

    # Bass track (channel 1, program 33 = finger bass)
    b_track = MidiTrack()
    b_track.append(Message("program_change", program=33, time=0, channel=1))
    if bass_notes:
        _add_bass_notes_to_track(b_track, bass_notes, bpm, tpq, channel=1)
    else:
        _add_chords_to_track(b_track, guitar_chords, bpm, tpq, channel=1)
    mid.tracks.append(b_track)

    mid.save(str(output_path))
    logger.info(f"[MIDI] Dual-track MIDI saved: {output_path}")
    return output_path


def _add_chords_to_track(track, chords: list, bpm: int, tpq: int, channel: int):
    """将和弦列表转为 MIDI note_on/off 事件。"""
    tick_per_sec = tpq * bpm / 60.0

    # 开放和弦转 MIDI notes（eBGDAE）
    OPEN_CHORDS = {
        "C":  [(60, 80), (64, 75), (72, 70)],
        "Dm": [(62, 80), (65, 75), (74, 70)],
        "Em": [(64, 80), (67, 75), (71, 70)],
        "F":  [(65, 80), (69, 75), (74, 70), (77, 65)],
        "G":  [(67, 80), (71, 75), (74, 70)],
        "Am": [(69, 80), (72, 75), (76, 70)],
        "A":  [(69, 80), (73, 75), (76, 70)],
        "E":  [(64, 80), (67, 75), (71, 70)],
        "D":  [(62, 80), (66, 75), (69, 70)],
        "B":  [(71, 80), (75, 75), (78, 70)],
    }

    current_tick = 0
    for chord in chords:
        dur_ticks = max(1, int((chord["end"] - chord["start"]) * tick_per_sec))
        notes = OPEN_CHORDS.get(chord.get("chord", "Am"), [(69, 80), (72, 75), (76, 70)])
        for note, vel in notes:
            track.append(Message("note_on", note=note, velocity=vel, time=current_tick, channel=channel))
            track.append(Message("note_off", note=note, velocity=0, time=dur_ticks, channel=channel))
        current_tick = 0

    track.append(MetaMessage("end_of_track"))


def _add_bass_notes_to_track(track, bass_notes: list, bpm: int, tpq: int, channel: int):
    """将 Bass 音符列表转为 MIDI note_on/off 事件。"""
    tick_per_sec = tpq * bpm / 60.0
    current_tick = 0

    for note in bass_notes:
        start = note.get("start", 0)
        end   = note.get("end", start + 0.5)
        midi  = note.get("midi", 40)  # Default E1
        vel   = int(note.get("confidence", 0.8) * 90)

        start_ticks = int(start * tick_per_sec)
        dur_ticks   = max(1, int((end - start) * tick_per_sec))

        # 补上静音
        track.append(Message("note_on", note=midi, velocity=vel, time=start_ticks - current_tick, channel=channel))
        track.append(Message("note_off", note=midi, velocity=0, time=dur_ticks, channel=channel))
        current_tick = 0

    track.append(MetaMessage("end_of_track"))
