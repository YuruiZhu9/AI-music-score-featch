"""
Audio Transcription Pipeline — Guitar + Bass 双轨扒谱
=======================================================
主处理流程：
  音频 → 分离（Demucs）→ Guitar 音高 + 和弦
                     → Bass 音高 + 根音
                  → Guitar + Bass 双轨乐谱

无 GPU 时自动降级到 librosa CPU 纯 CPU 模式。
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ─── 共享任务状态 ──────────────────────────────────────────────
from backend.main import tasks, TaskStatus


def _upd(task_id: str, **kw):
    t = tasks.get(task_id)
    if t:
        for k, v in kw.items():
            setattr(t, k, v)


# ─── Demo 数据 ─────────────────────────────────────────────────

def _make_demo_bass_notes() -> List[Dict[str, Any]]:
    """
    生成演示用 Bass 音符（跟随 Am-G-C-F 和弦进行）。
    标准 Bass 根音：Am→A, G→G, C→C, F→F（低八度）
    """
    import math
    bpm = 120
    beat = 60.0 / bpm
    patterns = [
        ("E1",  0.0,  1 * beat),   # Am → E1 (low E string open)
        ("A1",  1 * beat, 2 * beat),  # G  → A1 (low A string open)
        ("C2",  2 * beat, 3 * beat),  # C  → C2 (A string 3rd fret)
        ("F1",  3 * beat, 4 * beat),   # F  → F1 (low E string 1st fret)
        ("E1",  4 * beat, 5 * beat),
        ("G1",  5 * beat, 6 * beat),  # Em → G1
        ("D2",  6 * beat, 7 * beat),  # G  → D2
        ("A1",  7 * beat, 8 * beat),
    ]
    result = []
    for i, (note, s, e) in enumerate(patterns):
        midi = _note_to_midi(note)
        result.append({
            "start": s,
            "end": e,
            "note": note,
            "midi": midi,
            "frequency": round(440.0 * 2 ** ((midi - 69) / 12), 2),
            "string": _midi_to_bass_string(midi),
            "fret": _midi_to_bass_fret(midi),
            "chord_root": note[0],
            "confidence": 0.92,
        })
    return result


def _note_to_midi(note: str) -> int:
    names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    n = note[0]
    oct_str = note[1:] if len(note) > 1 else ""
    try:
        oct = int(oct_str)
    except ValueError:
        oct = 4
    return names.index(n) + (oct + 1) * 12


def _midi_to_bass_string(midi: int) -> int:
    """MIDI note → Bass 弦号 (1=G, 2=D, 3=A, 4=E)。"""
    # G2=43, D2=38, A1=33, E1=28
    strings = [(43, 1), (38, 2), (33, 3), (28, 4)]
    best = min(strings, key=lambda x: abs(x[0] - midi))
    return best[1]


def _midi_to_bass_fret(midi: int) -> int:
    strings = {"G": 43, "D": 38, "A": 33, "E": 28}
    open_notes = {"G": 43, "D": 38, "A": 33, "E": 28}
    # 找最近的空弦
    best_note = min(open_notes.values(), key=lambda x: abs(x - midi))
    best_name = [k for k, v in open_notes.items() if v == best_note][0]
    return max(0, midi - best_note)


# ─── Demo 模式检测 ──────────────────────────────────────────────

def _is_demo() -> bool:
    if __import__("os").getenv("DEMO_MODE") == "1":
        return True
    try:
        import torch; del torch
        return False
    except ImportError:
        return True


# ─── 主 Pipeline ──────────────────────────────────────────────

def run_pipeline(task_id: str, audio_path: Path):
    try:
        _upd(task_id, status=TaskStatus.PROCESSING, progress=0.05, stage="检查运行环境...")
        if _is_demo():
            logger.info(f"[{task_id}] Demo 模式运行")
            return _run_demo_pipeline(task_id, audio_path)
        return _run_full_pipeline(task_id, audio_path)
    except Exception as exc:
        logger.exception(f"[{task_id}] Pipeline error: {exc}")
        try:
            _run_demo_pipeline(task_id, audio_path)
        except Exception as de:
            _upd(task_id, status=TaskStatus.ERROR, error=f"处理失败: {de}")


# ─── Demo Pipeline ─────────────────────────────────────────────

def _run_demo_pipeline(task_id: str, audio_path: Path):
    from backend.core.chord_recognizer import recognize_chords, recognize_bass_notes
    from backend.core.bpm_detector   import detect_bpm
    from backend.core.pitch_detector  import detect_pitch, detect_bass_pitch
    from backend.core.score_generator import (
        build_gta_text, build_pdf_score,
        build_midi_file, generate_score,
    )

    _upd(task_id, progress=0.1, stage="分析 Guitar 和弦...")

    # Guitar 和弦
    try:
        chords = recognize_chords(audio_path, task_id)
    except Exception:
        chords = []

    # Guitar 音高
    try:
        guitar_pitch = detect_pitch(audio_path, task_id)
    except Exception:
        guitar_pitch = {"notes": []}

    # BPM
    try:
        bpm_info = detect_bpm(audio_path, task_id)
    except Exception:
        bpm_info = {"bpm": 120, "time_signature": "4/4", "beat_times": []}

    _upd(task_id, progress=0.4, stage="分析 Bass 线条...")

    # Bass 分析（使用 bass range pitch detection）
    bass_notes: List[Dict[str, Any]] = []
    try:
        # 优先用 bass range 的音高检测
        bass_pitch = detect_bass_pitch(audio_path, task_id)
        bass_notes = bass_pitch.get("notes", [])
        if not bass_notes:
            raise ValueError("No bass notes from pitch detector")
    except Exception:
        # fallback：直接用 chord recognizer 的 bass 版本
        try:
            bass_notes = recognize_bass_notes(audio_path, task_id)
        except Exception:
            bass_notes = _make_demo_bass_notes()

    _upd(task_id, progress=0.6, stage="生成双轨乐谱...")

    output_dir = Path(__import__("os").getenv("OUTPUT_DIR", "./outputs")) / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成 GTA 文本（Guitar + Bass）
    gta_text = build_gta_text(
        chords=chords or [
            {"start": 0.0, "end": 1.92, "chord": "Am"},
            {"start": 1.92, "end": 3.84, "chord": "G"},
            {"start": 3.84, "end": 5.76, "chord": "C"},
            {"start": 5.76, "end": 7.68, "chord": "F"},
        ],
        guitar_pitch=guitar_pitch,
        bpm=bpm_info,
        bass_notes=bass_notes or _make_demo_bass_notes(),
        song_name="演示歌曲",
    )

    gta_path = output_dir / "score.gta.txt"
    gta_path.write_text(gta_text, encoding="utf-8")
    logger.info(f"[{task_id}] GTA 已生成（含 Bass）")

    # PDF
    try:
        pdf_path = output_dir / "score.pdf"
        build_pdf_score(gta_text, bpm_info, pdf_path, song_name="演示歌曲")
    except Exception as e:
        logger.warning(f"[{task_id}] PDF 生成失败: {e}")

    # MIDI（Guitar + Bass 双轨）
    try:
        midi_path = output_dir / "score.mid"
        build_midi_file(
            guitar_chords=chords or [
                {"start": 0.0, "end": 1.92, "chord": "Am"},
                {"start": 1.92, "end": 3.84, "chord": "G"},
                {"start": 3.84, "end": 5.76, "chord": "C"},
                {"start": 5.76, "end": 7.68, "chord": "F"},
            ],
            bass_notes=bass_notes,
            bpm=bpm_info.get("bpm", 120),
            output_path=midi_path,
        )
        logger.info(f"[{task_id}] MIDI 已生成（Guitar+Bass）")
    except ImportError:
        logger.warning(f"[{task_id}] mido 未安装，跳过 MIDI")
    except Exception as e:
        logger.warning(f"[{task_id}] MIDI 生成失败: {e}")

    # Stage 7: LLM 智能纠错（可选，免费 API）
    llm_info: Dict[str, Any] = {"enabled": False}
    _upd(task_id, progress=0.92, stage="LLM 智能纠错...")
    try:
        from backend.core.llm_corrector import correct_transcription, detect_capo_and_key
        # Capo + 调性检测
        capo_info = detect_capo_and_key(
            chords=chords or [],
            guitar_notes=guitar_pitch.get("notes", []),
            bpm=bpm_info.get("bpm", 120),
        )
        # 构造临时 result 给纠错器
        _temp_result = {
            "bpm": bpm_info.get("bpm", 120),
            "time_signature": bpm_info.get("time_signature", "4/4"),
            "guitar": {"chords": chords or [], "notes": guitar_pitch.get("notes", [])},
            "bass": {"notes": bass_notes or _make_demo_bass_notes()},
        }
        corrected = correct_transcription(_temp_result)
        llm_info = {
            "enabled": True,
            "corrections": corrected.get("llm_corrected", {}).get("corrections", []),
            "detected_key": corrected.get("llm_corrected", {}).get("detected_key", "Unknown"),
            "suggested_capo": corrected.get("llm_corrected", {}).get("suggested_capo", 0),
            "summary": corrected.get("llm_corrected", {}).get("summary", ""),
            "capo_info": capo_info,
        }
        # 更新和弦（如果 LLM 有修正）
        if corrected.get("llm_corrected", {}).get("corrected_chords"):
            chords = corrected["llm_corrected"]["corrected_chords"]
        logger.info(f"[{task_id}] LLM 纠错完成: {llm_info.get('summary', '')}")
    except Exception as e:
        logger.warning(f"[{task_id}] LLM 纠错跳过: {e}")
        llm_info = {"enabled": False, "error": str(e)}

    # Stage 8: MusicXML 生成（Guitar Pro 7 导入格式）
    _upd(task_id, progress=0.96, stage="生成 Guitar Pro 乐谱...")
    xml_path = output_dir / "score.xml"
    try:
        from backend.core.gp7_generator import build_musicxml_file
        xml_path = build_musicxml_file(
            chords=chords or [],
            guitar_notes=guitar_pitch.get("notes", []),
            bass_notes=bass_notes or _make_demo_bass_notes(),
            bpm=bpm_info.get("bpm", 120),
            output_path=xml_path,
            title="演示歌曲",
            time_signature=bpm_info.get("time_signature", "4/4"),
            capo=llm_info.get("capo_info", {}).get("suggested_capo", 0),
        )
        logger.info(f"[{task_id}] MusicXML 已生成")
    except Exception as e:
        logger.warning(f"[{task_id}] MusicXML 生成失败: {e}")
        xml_path = None

    _upd(task_id, progress=1.0, stage="完成！")

    json_path = output_dir / "score.json"
    result = {
        "bpm": bpm_info.get("bpm", 120),
        "time_signature": bpm_info.get("time_signature", "4/4"),
        "duration_sec": bpm_info.get("duration_sec", 0),
        "guitar": {
            "chords": chords or [],
            "notes": guitar_pitch.get("notes", []),
        },
        "bass": {
            "notes": bass_notes or [],
        },
        "llm_corrected": llm_info,
        "score_files": {
            "gta": str(gta_path),
            "pdf": str(output_dir / "score.pdf"),
            "mid": str(output_dir / "score.mid"),
            "xml": str(xml_path) if xml_path else None,
            "json": str(json_path),
        },
        "gta_text": gta_text,
        "is_demo": len(chords) == 0,
    }
    # 统一保存为 score.json（与 score.gta.txt / score.pdf 命名一致）
    import json as _json
    json_path.write_text(_json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _upd(task_id, status=TaskStatus.DONE, result=result)
    logger.info(f"[{task_id}] Demo Pipeline 完成！ Guitar chords={len(chords)}, Bass notes={len(bass_notes)}")


# ─── 完整 Pipeline（GPU）───────────────────────────────────────

def _run_full_pipeline(task_id: str, audio_path: Path):
    from backend.core.separator       import separate_audio
    from backend.core.pitch_detector  import detect_pitch, detect_bass_pitch
    from backend.core.chord_recognizer import recognize_chords, recognize_bass_notes
    from backend.core.bpm_detector    import detect_bpm
    from backend.core.score_generator import build_gta_text, build_pdf_score, build_midi_file

    output_dir = Path(__import__("os").getenv("OUTPUT_DIR", "./outputs")) / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: 音频分离
    _upd(task_id, progress=0.05, stage="正在分离音轨（Demucs）...")
    try:
        stems = separate_audio(audio_path, task_id)
    except Exception as e:
        logger.warning(f"[{task_id}] 分离失败: {e}, 使用原音频")
        stems = {"guitar": audio_path, "bass": audio_path,
                 "vocals": audio_path, "drums": audio_path}

    guitar_path = stems.get("guitar", audio_path)
    bass_path   = stems.get("bass",   audio_path)

    # Stage 2: Guitar 音高（优先 Basic Pitch，fallback CREPE）
    _upd(task_id, progress=0.30, stage="Guitar 音高检测（Basic Pitch / CREPE）...")
    guitar_pitch: Dict[str, Any] = {"notes": []}
    try:
        from backend.core.basic_pitch_transcriber import is_available as bp_ok, transcribe as bp_transcribe
        if bp_ok():
            bp_result = bp_transcribe(guitar_path, task_id, output_dir=output_dir)
            guitar_pitch["notes"] = bp_result.get("notes", [])
            logger.info(f"[{task_id}] Basic Pitch 转谱成功: {len(guitar_pitch['notes'])} 个音符")
        else:
            raise ImportError("basic-pitch not installed")
    except ImportError as e:
        logger.warning(f"[{task_id}] Basic Pitch 不可用: {e}，使用 CREPE fallback")
        try:
            guitar_pitch = detect_pitch(guitar_path, task_id)
        except Exception as e2:
            logger.warning(f"[{task_id}] CREPE 音高检测也失败: {e2}")
            guitar_pitch = {"notes": []}
    except Exception as e:
        logger.warning(f"[{task_id}] Basic Pitch 转谱出错: {e}，使用 CREPE fallback")
        try:
            guitar_pitch = detect_pitch(guitar_path, task_id)
        except Exception as e2:
            logger.warning(f"[{task_id}] CREPE fallback 也失败: {e2}")
            guitar_pitch = {"notes": []}

    # Stage 3: Bass 音高
    _upd(task_id, progress=0.45, stage="Bass 音高检测...")
    bass_notes: List[Dict[str, Any]] = []
    try:
        bass_pitch = detect_bass_pitch(bass_path, task_id)
        bass_notes = bass_pitch.get("notes", [])
    except Exception as e:
        logger.warning(f"[{task_id}] Bass 音高检测失败: {e}")
        try:
            bass_notes = recognize_bass_notes(bass_path, task_id)
        except Exception:
            pass

    # Stage 4: Guitar 和弦
    _upd(task_id, progress=0.60, stage="Guitar 和弦识别...")
    try:
        chords = recognize_chords(guitar_path, task_id)
    except Exception as e:
        logger.warning(f"[{task_id}] Guitar 和弦识别失败: {e}")
        chords = []

    # Stage 5: BPM
    _upd(task_id, progress=0.75, stage="BPM 检测...")
    try:
        bpm_info = detect_bpm(audio_path, task_id)
    except Exception:
        bpm_info = {"bpm": 120, "time_signature": "4/4", "beat_times": []}

    # Stage 6: 乐谱生成
    _upd(task_id, progress=0.88, stage="生成 Guitar + Bass 乐谱...")
    gta_text = build_gta_text(
        chords, guitar_pitch, bpm_info,
        bass_notes=bass_notes,
        song_name="扒取乐谱",
    )
    gta_path = output_dir / "score.gta.txt"
    gta_path.write_text(gta_text, encoding="utf-8")

    try:
        build_pdf_score(gta_text, bpm_info, output_dir / "score.pdf", song_name="扒取乐谱")
    except Exception as e:
        logger.warning(f"[{task_id}] PDF 生成失败: {e}")

    try:
        build_midi_file(chords, bass_notes, bpm_info.get("bpm", 120), output_dir / "score.mid")
    except ImportError:
        logger.warning(f"[{task_id}] mido 未安装，跳过 MIDI")
    except Exception as e:
        logger.warning(f"[{task_id}] MIDI 生成失败: {e}")

    # Stage 7: LLM 智能纠错
    llm_info: Dict[str, Any] = {"enabled": False}
    _upd(task_id, progress=0.90, stage="LLM 智能纠错...")
    try:
        from backend.core.llm_corrector import correct_transcription, detect_capo_and_key
        capo_info = detect_capo_and_key(chords, guitar_pitch.get("notes", []), bpm_info.get("bpm", 120))
        _temp_result = {
            "bpm": bpm_info.get("bpm", 120),
            "time_signature": bpm_info.get("time_signature", "4/4"),
            "guitar": {"chords": chords, "notes": guitar_pitch.get("notes", [])},
            "bass": {"notes": bass_notes},
        }
        corrected = correct_transcription(_temp_result)
        llm_info = {
            "enabled": True,
            "corrections": corrected.get("llm_corrected", {}).get("corrections", []),
            "detected_key": corrected.get("llm_corrected", {}).get("detected_key", "Unknown"),
            "suggested_capo": corrected.get("llm_corrected", {}).get("suggested_capo", 0),
            "summary": corrected.get("llm_corrected", {}).get("summary", ""),
            "capo_info": capo_info,
        }
        if corrected.get("llm_corrected", {}).get("corrected_chords"):
            chords = corrected["llm_corrected"]["corrected_chords"]
        logger.info(f"[{task_id}] LLM 纠错完成: {llm_info.get('summary', '')}")
    except Exception as e:
        logger.warning(f"[{task_id}] LLM 纠错跳过: {e}")
        llm_info = {"enabled": False, "error": str(e)}

    # Stage 8: MusicXML 生成
    _upd(task_id, progress=0.95, stage="生成 Guitar Pro 乐谱...")
    xml_path = output_dir / "score.xml"
    try:
        from backend.core.gp7_generator import build_musicxml_file
        xml_path = build_musicxml_file(
            chords=chords,
            guitar_notes=guitar_pitch.get("notes", []),
            bass_notes=bass_notes,
            bpm=bpm_info.get("bpm", 120),
            output_path=xml_path,
            time_signature=bpm_info.get("time_signature", "4/4"),
            capo=llm_info.get("capo_info", {}).get("suggested_capo", 0),
        )
    except Exception as e:
        logger.warning(f"[{task_id}] MusicXML 生成失败: {e}")
        xml_path = None

    _upd(task_id, progress=1.0, stage="完成！")

    # 统一保存 score.json（与 score.gta.txt / score.pdf / score.mid 命名一致）
    import json as _json
    json_path = output_dir / "score.json"
    result = {
        "bpm": bpm_info.get("bpm", 120),
        "time_signature": bpm_info.get("time_signature", "4/4"),
        "duration_sec": guitar_pitch.get("duration_sec", 0),
        "guitar": {"chords": chords, "notes": guitar_pitch.get("notes", [])},
        "bass":  {"notes": bass_notes},
        "llm_corrected": llm_info,
        "score_files": {
            "gta": str(gta_path),
            "pdf": str(output_dir / "score.pdf"),
            "mid": str(output_dir / "score.mid"),
            "xml": str(xml_path) if xml_path else None,
            "json": str(json_path),
        },
        "gta_text": gta_text,
        "is_demo": False,
    }
    json_path.write_text(_json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _upd(task_id, status=TaskStatus.DONE, result=result)
    logger.info(f"[{task_id}] Pipeline 完成！ Guitar={len(chords)} chords, Bass={len(bass_notes)} notes")
