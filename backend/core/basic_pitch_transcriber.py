"""
Basic Pitch 转谱器 — Spotify 开源吉他专用转谱模型
================================================
集成来源：参考 Tabby 项目架构 https://github.com/JGodbold1/Tabby

功能：
  1. 输入隔离吉他音频 → Basic Pitch 转谱 → MIDI + Guitar Tab 事件
  2. 将 Basic Pitch 输出转换为项目统一的音符/和弦格式
  3. 作为 CREPE 的高精度替代方案（Basic Pitch 专为吉他优化）

依赖：basic-pitch（Spotify 开源）
  pip install basic-pitch

Basic Pitch vs CREPE 对比：
  - CREPE：通用深度学习音高检测（任何乐器）
  - Basic Pitch：Spotify 专用吉他转谱模型，输出 MIDI + tab 结构，精度更高
  - 策略：DEMO模式用 CREPE，GPU模式优先用 Basic Pitch，失败时 fallback 到 CREPE
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── 吉他调弦常量 ─────────────────────────────────────────────────
# 标准吉他 6 弦（E A D G B e）， MIDI note numbers
GUITAR_OPEN_NOTES: Dict[str, int] = {
    "e": 64,   # e1 (329.63 Hz)
    "B": 59,   # B1 (246.94 Hz)
    "G": 55,   # G2 (196.00 Hz)
    "D": 50,   # D2 (146.83 Hz)
    "A": 45,   # A2 (110.00 Hz)
    "E": 40,   # E2 (82.41 Hz)
}
GUITAR_STRING_ORDER = ["e", "B", "G", "D", "A", "E"]  # 细弦到粗弦


def is_available() -> bool:
    """检测 Basic Pitch 是否可用（已安装）。"""
    try:
        from basic_pitch import BasicPitch
        return True
    except ImportError:
        return False


def transcribe(
    audio_path: Path,
    task_id: str,
    output_dir: Optional[Path] = None,
    confident_lo: float = 0.25,
    frequency_lpf: float = 2500.0,
) -> Dict[str, Any]:
    """
    使用 Basic Pitch 对吉他音频进行转谱。

    参数:
        audio_path:     音频文件路径（支持 MP3/WAV/FLAC）
        task_id:        任务 ID（用于日志）
        output_dir:     输出目录（保存 MIDI 和 JSON）
        confident_lo:  置信度下限（默认 0.25，越低越敏感）
        frequency_lpf:  低通滤波频率（Hz，默认 2500，覆盖吉他频段）

    返回:
        {
            "notes": [  # 音符时间线
                {
                    "start": float,   # 秒
                    "end":   float,   # 秒
                    "string": int,    # 弦号（1=e, 6=E）
                    "fret":  int,    # 品位（0=空弦）
                    "midi":  int,    # MIDI note
                    "note":  str,    # 音符名如 "E2"
                    "frequency": float,# 频率 Hz
                    "confidence": float,
                }, ...
            ],
            "midi_path": str,   # MIDI 文件路径
            "json_path": str,   # JSON 结果路径
            "model": "basic_pitch",
        }
    """
    if not is_available():
        raise ImportError(
            "basic-pitch 未安装。请运行: pip install basic-pitch\n"
            "或参考 Tabby 项目架构: https://github.com/JGodbold1/Tabby"
        )

    from basic_pitch import BasicPitch
    from basic_pitch.inference import predict, model

    bp = BasicPitch()

    logger.info(f"[{task_id}] [BasicPitch] 开始转谱: {audio_path}")
    (
        midi_data,
        midi_path_saved,
        json_path_saved,
    ) = bp.predict(
        audio_path=str(audio_path),
        save_midi=True,                     # 自动保存 MIDI 文件
        save_outputs=True,
        output_dir=str(output_dir) if output_dir else None,
        confident_lo=confident_lo,
        frequency_lpf=frequency_lpf,
    )

    # ── 解析 Basic Pitch 的 MIDI → 吉他指法 ────────────────────
    notes = _midi_to_guitar_tab(midi_data, task_id)

    logger.info(
        f"[{task_id}] [BasicPitch] 转谱完成: "
        f"{len(notes)} 个音符, MIDI saved: {midi_path_saved}"
    )

    return {
        "notes": notes,
        "midi_data": midi_data,
        "midi_path": str(midi_path_saved) if midi_path_saved else None,
        "json_path": str(json_path_saved) if json_path_saved else None,
        "model": "basic_pitch",
    }


# ─── MIDI → Guitar Tab 指法转换 ─────────────────────────────────

def _midi_to_guitar_tab(midi_data, task_id: str) -> List[Dict[str, Any]]:
    """
    将 Basic Pitch 输出的 MIDI 数据转换为吉他六线谱指法。

    Basic Pitch 输出结构 (midi_data):
        - notes: List[Note]  (basic_pitch.note_formation.Note)
          Note 属性: pitch_midi, start_s, end_s, amplitude
    返回:
        List[Dict]: 音符时间线，含 string/fret/midi/note/frequency/confidence
    """
    try:
        notes_list = midi_data.notes
    except AttributeError:
        try:
            notes_list = list(midi_data)
        except Exception:
            logger.warning(f"[{task_id}] [BasicPitch] 无法解析 MIDI 数据结构")
            return []

    result: List[Dict[str, Any]] = []
    for note in notes_list:
        try:
            midi   = int(round(getattr(note, "pitch_midi", 60)))
            start  = float(getattr(note, "start_s", 0.0))
            end    = float(getattr(note, "end_s",   start + 0.5))
            amp    = float(getattr(note, "amplitude", 0.5))
        except Exception:
            continue

        # MIDI → 音符名
        note_name = _midi_to_note_name(midi)

        # MIDI → 吉他弦/品位（找最轻松的按法）
        string, fret = _find_easiest_fingering(midi)

        # 置信度：amplitude 0~1 映射为 confidence
        confidence = min(1.0, max(0.0, amp * 2.0))

        result.append({
            "start":      start,
            "end":        end,
            "string":     string,      # 1=e, 6=E
            "fret":       fret,        # 0=空弦
            "midi":       midi,
            "note":       note_name,
            "frequency":  round(440.0 * 2 ** ((midi - 69) / 12), 2),
            "confidence": round(confidence, 3),
            "source":     "basic_pitch",
        })

    # 按时间排序
    result.sort(key=lambda x: x["start"])
    return result


def _midi_to_note_name(midi: int) -> str:
    """MIDI note number → 音符名称（如 64 → 'E4'）。"""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    oct   = (midi // 12) - 1
    name  = names[midi % 12]
    return f"{name}{oct}"


def _find_easiest_fingering(midi: int) -> Tuple[int, int]:
    """
    给定 MIDI note，找出最易弹的弦+品位。

    策略：从低音弦往高音弦找，
    优先：空弦品位 0，然后低品位（0~5），避免高把位。
    返回: (string, fret)，string 1=e（细）, 6=E（粗）
    """
    # 在吉他 24 品范围内找
    for string_idx, (open_note_name, open_midi) in enumerate(reversed(GUITAR_STRING_ORDER)):
        # GUITAR_STRING_ORDER = ["e","B","G","D","A","E"]
        # reversed → ["E","A","D","G","B","e"] 低→高
        open_note_midi = GUITAR_OPEN_NOTES[open_note_name]
        fret = midi - open_note_midi
        if 0 <= fret <= 24:
            # string 编号：1=e（细弦）, 6=E（粗弦）
            string_num = 6 - string_idx
            return (string_num, fret)

    # 超出 24 品，取最近的弦
    best_string = 1
    best_fret   = 0
    min_dist    = 999
    for s_name, o_midi in GUITAR_OPEN_NOTES.items():
        f = midi - o_midi
        dist = abs(f)
        if dist < min_dist:
            min_dist  = dist
            best_fret = max(0, f)
            s_idx     = GUITAR_STRING_ORDER.index(s_name)
            best_string = 6 - s_idx
    return (best_string, best_fret)


# ─── 与 pipeline 整合的工具函数 ──────────────────────────────────

def build_gta_from_basic_pitch(
    notes: List[Dict[str, Any]],
    bpm: float,
    song_name: str = "Untitled",
) -> str:
    """
    将 Basic Pitch 音符列表渲染为 GTA 文本谱（纯 Guitar 六线谱）。
    用于与 pipeline 现有 build_gta_text 输出的 Guitar 部分对比验证。
    """
    lines: List[str] = []
    lines.append("=" * 64)
    lines.append(f"  🎸 {song_name}  [Basic Pitch Guitar Transcription]")
    lines.append("=" * 64)
    lines.append(f" Model: Spotify Basic Pitch  |  Tempo: {bpm} BPM")
    lines.append("")

    # 渲染 TAB 网格
    TAB_LINES = ["e|", "B|", "G|", "D|", "A|", "E|"]
    BEAT_CHAR = 2  # 每个字符 ≈ 16分音符
    eighth    = 60.0 / bpm / 2.0
    total      = BEAT_CHAR * 4 * 16  # 16 小节

    # 初始化网格
    grid: Dict[str, List[str]] = {s: ["-"] * total for s in TAB_LINES}

    for note in notes:
        start  = note.get("start", 0)
        sid    = note.get("string", 1)   # 1=e, 6=E
        fret   = note.get("fret", 0)
        # sid 1→TAB_LINES[0]="e|", sid 6→TAB_LINES[5]="E|"
        idx    = max(0, min(5, sid - 1))
        pos    = min(int(start / eighth), total - 1)
        fc     = str(fret)
        # 写入品位（最多2格）
        for j, ch in enumerate(fc[:2]):
            p = pos + j
            if p < total:
                grid[TAB_LINES[idx]][p] = ch

    for s in TAB_LINES:
        row = "".join(
            c + ("|" if (i + 1) % 16 == 0 else "")
            for i, c in enumerate(grid[s])
        )
        lines.append(f"{s}{row}|")

    lines.append("")
    lines.append("# Basic Pitch (Spotify)  —  https://github.comSpotify/basic-pitch")
    lines.append("# 数字=品位(0=open), -=rest, |=小节线")
    lines.append("=" * 64)
    return "\n".join(lines)


def merge_with_chords(
    basic_pitch_notes: List[Dict[str, Any]],
    chords: List[Dict[str, Any]],
    bpm: float,
) -> List[Dict[str, Any]]:
    """
    将 Basic Pitch 音符与和弦时间轴融合。

    策略：
    - 每个 Basic Pitch 音符标记其所属和弦（按时间对齐）
    - 有和弦时保留，无和弦时标记为 "N/A"
    """
    if not chords:
        return basic_pitch_notes

    for note in basic_pitch_notes:
        t = note.get("start", 0)
        chord = _find_chord_at_time(chords, t)
        note["chord"] = chord

    return basic_pitch_notes


def _find_chord_at_time(chords: List[Dict[str, Any]], time: float) -> str:
    """在和弦列表中找指定时间对应的和弦名。"""
    for c in chords:
        if c.get("start", 0) <= time < c.get("end", 999):
            return c.get("chord", "?")
    return "?"
