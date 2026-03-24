"""
Chord Recognition — Omnizart + librosa
======================================
Automatic chord recognition from guitar/bass audio using Omnizart.
Omnizart is an open-source library specifically designed for music transcription.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# Standard chord vocabulary (Omnizart supports these)
CHORD_QUALITIES = [
    "N", "X",          # no chord / unknown
    "maj", "min", "dim", "aug", "maj7", "min7", "dom7", "hdim7", "dim7",
    "sus2", "sus4", "add9",
]
MINOR_BASS = ["min", "dim", "hdim7", "min7", "dim7"]

# 音符名称
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def recognize_chords(audio_path: Path, task_id: str) -> List[Dict[str, Any]]:
    """
    Recognize chord sequence from guitar audio.
    
    Returns:
        list of chord events:
        [{"start": 0.0, "end": 1.92, "chord": "Am"}, ...]
    """
    try:
        import omnizart
        from omnizart.module.chord import predict
        HAS_OMNIZART = True
    except Exception:
        logger.warning("Omnizart unavailable, using librosa chord detection fallback.")
        HAS_OMNIZART = False

    if HAS_OMNIZART:
        try:
            chords = predict(str(audio_path), output=False)
            return _parse_omnizart_output(chords)
        except Exception as e:
            logger.warning(f"Omnizart prediction failed ({e}), falling back to librosa.")
            return _librosa_fallback(audio_path)
    else:
        return _librosa_fallback(audio_path)


# ─── Bass 根音识别 ──────────────────────────────────────────────

def recognize_bass_notes(audio_path: Path, task_id: str) -> List[Dict[str, Any]]:
    """
    Recognize bass line (monophonic note sequence) from bass stem.
    
    Bass is typically played one note at a time, so instead of chord recognition
    we detect individual notes → then infer chord root from bass note sequence.
    
    Returns:
        list of bass note events:
        [{"start": 0.0, "end": 0.96, "note": "E2", "string": 4, "chord_root": "E"}, ...]
    """
    import librosa
    import numpy as np

    y, sr = librosa.load(str(audio_path), mono=True)
    
    # Bass range: E1 (41 Hz) ~ C4 (261 Hz)
    fmin = librosa.note_to_hz("E1")
    fmax = librosa.note_to_hz("C4")
    
    logger.info(f"[{task_id}] Bass note detection (fmin={fmin:.0f}Hz, fmax={fmax:.0f}Hz)...")
    
    # Use pyin for f0 detection (monophonic pitch tracking)
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y, fmin=fmin, fmax=fmax, sr=sr, hop_length=512
    )
    
    # Convert to note-level events using onset detection
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=512)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)
    
    # Bass standard tuning (E A D G from low to high)
    BASS_STRINGS = {  # string number (1=low E) -> open note MIDI
        1: 28,  # E1 = MIDI 28
        2: 33,  # A1 = MIDI 33
        3: 38,  # D2 = MIDI 38
        4: 43,  # G2 = MIDI 43
    }
    BASS_STRINGS_REVERSE = {v: k for k, v in BASS_STRINGS.items()}
    
    notes = []
    for i, (t, f, v, prob) in enumerate(zip(
            onset_times, f0, voiced_flag, voiced_probs)):
        if not v or f <= 0:
            continue
        # Skip very short notes (< 0.1s between onsets)
        if i + 1 < len(onset_times):
            duration = onset_times[i + 1] - t
        else:
            duration = len(y) / sr - t
        
        # Compute MIDI note number
        midi = int(round(69 + 12 * np.log2(f / 440.0)))
        note_name = NOTE_NAMES[midi % 12]
        octave = midi // 12 - 1
        note_full = f"{note_name}{octave}"
        
        # Guess which string based on MIDI note
        # Closest open string
        open_note_midi = BASS_STRINGS_REVERSE.get(
            min(BASS_STRINGS_REVERSE.keys(), key=lambda x: abs(x - midi)), 4
        )
        string_guess = BASS_STRINGS_REVERSE.get(
            min(BASS_STRINGS_REVERSE.keys(), key=lambda x: abs(x - midi)), 4
        )
        
        # Determine fret position relative to guessed open string
        # This is approximate — real implementation would need pitch tracking
        fret = max(0, midi - list(BASS_STRINGS.values())[string_guess - 1])
        if fret > 24:
            fret = midi - list(BASS_STRINGS.values())[min(string_guess, 3) - 1]
        
        # Chord root inferred from bass note
        chord_root = note_name
        
        notes.append({
            "start": round(float(t), 3),
            "end": round(float(t + duration), 3),
            "note": note_full,
            "midi": midi,
            "frequency": round(float(f), 2),
            "string": int(string_guess),
            "fret": int(fret),
            "chord_root": chord_root,
            "confidence": round(float(prob), 3),
        })
    
    # Merge consecutive identical notes
    merged = _merge_consecutive_bass_notes(notes)
    
    logger.info(f"[{task_id}] Bass note detection done: {len(merged)} notes, "
                f"{len(set(n['chord_root'] for n in merged))} unique roots")
    return merged


def _merge_consecutive_bass_notes(notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge consecutive notes with the same pitch."""
    if not notes:
        return []
    merged = [dict(notes[0])]
    for note in notes[1:]:
        if note["note"] == merged[-1]["note"] and note["start"] - merged[-1]["end"] < 0.05:
            merged[-1]["end"] = note["end"]
        else:
            merged.append(dict(note))
    return merged


def _parse_omnizart_output(raw) -> List[Dict[str, Any]]:
    """Parse Omnizart chord output into our standard format."""
    # Omnizart returns a dict or list depending on version
    # Standard format: list of (start_sec, end_sec, chord_name)
    result = []
    if hasattr(raw, "chords"):
        for chord_event in raw.chords:
            start, end, name = chord_event.start, chord_event.end, chord_event.name
            result.append({"start": float(start), "end": float(end), "chord": str(name)})
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                result.append({"start": float(item[0]), "end": float(item[1]), "chord": str(item[2])})
    return result


def _librosa_fallback(audio_path: Path) -> List[Dict[str, Any]]:
    """Fallback chord detection using librosa."""
    import librosa
    import numpy as np

    y, sr = librosa.load(str(audio_path))
    
    # Chromagram for chord detection
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
    
    # Beat-synchronous chord detection
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512)
    
    # Simple chord estimation from chromagram
    chords = []
    beat_times = np.append(beat_times, librosa.get_samplerate(audio_path) / 512 * len(y) / librosa.get_samplerate(audio_path))
    
    for i in range(len(beat_times) - 1):
        start = float(beat_times[i])
        end = float(beat_times[i + 1])
        start_frame = librosa.time_to_frames(start, sr=sr, hop_length=512)
        end_frame = librosa.time_to_frames(end, sr=sr, hop_length=512)
        start_frame = max(0, start_frame)
        end_frame = min(chroma.shape[1], end_frame)
        
        if end_frame <= start_frame:
            continue
            
        chroma_seg = chroma[:, start_frame:end_frame]
        chroma_mean = np.mean(chroma_seg, axis=1)
        root_idx = int(np.argmax(chroma_mean))
        chroma_vec = chroma_mean / (np.sum(chroma_mean) + 1e-8)
        
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        # Correlation with major/minor profiles
        major = np.corrcoef(chroma_vec, major_profile)[0, 1]
        minor = np.corrcoef(chroma_vec, minor_profile)[0, 1]
        
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        root = notes[root_idx]
        quality = "maj" if major >= minor else "min"
        chord = f"{root}{quality}" if root != "C" else f"C{quality}"
        if quality == "maj" and major > 0.5:
            chord = root
        elif quality == "min" and minor > 0.5:
            chord = f"{root}m"
        else:
            chord = f"{root}m"
        
        chords.append({"start": round(start, 3), "end": round(end, 3), "chord": chord})
    
    return chords
