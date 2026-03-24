"""
Pitch Detection — CREPE
========================
High-precision fundamental frequency (F0) detection using CREPE deep learning model.
CREPE is a convolutional neural network that predicts pitch from mel-spectrogram.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def detect_pitch(audio_path: Path, task_id: str) -> Dict[str, Any]:
    """
    Detect pitch (fundamental frequency) from an audio file using CREPE.
    
    Returns:
        {
            "notes": [
                {"time": 0.0, "frequency": 440.0, "note": "A4", "confidence": 0.99},
                ...
            ],
            "total_notes": 128,
            "duration_sec": 30.5,
        }
    """
    try:
        import crepe
    except ImportError:
        logger.warning("CREPE not installed, using librosa fallback for pitch detection.")
        return _librosa_fallback(audio_path)

    import numpy as np
    import soundfile as sf

    audio, sr = sf.read(str(audio_path))
    if audio.ndim > 1:
        audio = audio[:, 0]  # mono

    logger.info(f"[{task_id}] Running CREPE pitch detection...")
    # CREPE returns: time, frequency, confidence, activation
    time, frequency, confidence, _ = crepe.predict(
        audio, sr,
        model_capacity="full",   # "tiny" | "small" | "medium" | "large" | "full"
        viterbi=True,             # smooth predictions
    )

    # Filter low-confidence predictions
    threshold = 0.25
    notes = []
    for t, f, c in zip(time, frequency, confidence):
        if c < threshold or f < 20:  # skip silence / very low freq
            continue
        note_name = _freq_to_note_name(f)
        notes.append({"time": round(float(t), 3), "frequency": round(float(f), 2), "note": note_name, "confidence": round(float(c), 3)})

    logger.info(f"[{task_id}] Pitch detection done: {len(notes)} notes found")
    return {
        "notes": notes,
        "total_notes": len(notes),
        "duration_sec": round(float(len(audio)) / sr, 2),
    }


def _freq_to_note_name(freq: float) -> str:
    """Convert frequency in Hz to note name (e.g. 440.0 → 'A4')."""
    import numpy as np
    if freq <= 0:
        return "?"
    # MIDI note 69 = A4 = 440 Hz
    midi = 69 + 12 * np.log2(freq / 440.0)
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    n = int(round(midi))
    octave = n // 12 - 1
    name = note_names[n % 12]
    return f"{name}{octave}"


def _librosa_fallback(audio_path: Path) -> Dict[str, Any]:
    """Simple fallback using librosa pyin when CREPE unavailable."""
    return _detect_pitch_range(audio_path,
                                fmin=librosa.note_to_hz("E2"),
                                fmax=librosa.note_to_hz("E6"))


def _detect_pitch_range(audio_path: Path,
                        fmin: float,
                        fmax: float) -> Dict[str, Any]:
    """Pitch detection with custom frequency range (for guitar or bass)."""
    import librosa
    import numpy as np

    y, sr = librosa.load(str(audio_path))
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y, fmin=fmin, fmax=fmax, sr=sr
    )
    notes = []
    for i, (f, v) in enumerate(zip(f0, voiced_flag)):
        t = float(i * 512) / sr  # default hop_length=512
        if v and f > 0:
            notes.append({"time": round(t, 3), "frequency": round(float(f), 2), "note": _freq_to_note_name(float(f)), "confidence": round(float(voiced_probs[i]), 3)})

    return {"notes": notes, "total_notes": len(notes), "duration_sec": round(float(len(y)) / sr, 2)}


# ─── Bass 音高检测 ──────────────────────────────────────────────

def detect_bass_pitch(audio_path: Path, task_id: str) -> Dict[str, Any]:
    """
    Detect pitch from bass guitar audio using CREPE with bass-tuned frequency range.

    Bass guitar range: E1 (41 Hz) ~ G3 (196 Hz), occasionally up to C4 (261 Hz)
    We use librosa pyin with bass-appropriate range as fallback.

    Returns:
        {
            "notes": [{"time": 0.0, "frequency": 82.4, "note": "E2", "string": 4, "confidence": 0.95}, ...],
            "total_notes": int,
            "duration_sec": float,
        }
    """
    try:
        import crepe
        import numpy as np
        import soundfile as sf

        audio, sr = sf.read(str(audio_path))
        if audio.ndim > 1:
            audio = audio[:, 0]

        logger.info(f"[{task_id}] Running CREPE bass pitch detection (fmin=E1, fmax=G3)...")
        time, frequency, confidence, _ = crepe.predict(
            audio, sr,
            model_capacity="full",
            viterbi=True,
        )

        # Bass fundamental frequency range: E1=41Hz ~ G3=196Hz (5th fret of G string)
        # Allow up to C4=261Hz for occasional harmonic notes
        BASS_FMIN = 35.0   # slightly below E1 for safety
        BASS_FMAX = 300.0  # above C4 to catch harmonics

        notes = []
        for t, f, c in zip(time, frequency, confidence):
            if c < 0.25 or f < BASS_FMIN or f > BASS_FMAX:
                continue
            note_name = _freq_to_note_name(f)
            notes.append({
                "time": round(float(t), 3),
                "frequency": round(float(f), 2),
                "note": note_name,
                "confidence": round(float(c), 3),
            })

        logger.info(f"[{task_id}] Bass pitch detection done: {len(notes)} notes found")
        return {
            "notes": notes,
            "total_notes": len(notes),
            "duration_sec": round(float(len(audio)) / sr, 2),
        }

    except ImportError:
        logger.info(f"[{task_id}] CREPE unavailable, using librosa bass range fallback.")
        import librosa
        return _detect_pitch_range(
            audio_path,
            fmin=librosa.note_to_hz("E1"),
            fmax=librosa.note_to_hz("G3"),
        )
    except Exception as exc:
        logger.warning(f"[{task_id}] Bass pitch detection failed: {exc}")
        return {"notes": [], "total_notes": 0, "duration_sec": 0.0}
