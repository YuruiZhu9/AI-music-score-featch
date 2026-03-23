"""
Audio Source Separation — Demucs
=================================
Separates mixed audio into stems: vocals, guitar, bass, drums, other.
Uses Meta's Demucs v4 (htdemucs) — state-of-the-art open-source separation.
"""

import os
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def separate_audio(input_path: Path, task_id: str) -> Dict[str, Path]:
    """
    Run Demucs separation on the uploaded audio file.
    
    Returns:
        dict mapping instrument name → path of isolated stem file.
        Keys: "vocals", "guitar", "bass", "drums", "other"
    """
    try:
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        import torchaudio
        import torch
    except ImportError as e:
        logger.warning(f"Demucs not installed ({e}), using mock separation.")
        return _mock_separation(input_path, task_id)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"[{task_id}] Loading Demucs model on {device}...")
    
    model = get_model("htdemucs")
    model.to(device)
    waveform, sr = torchaudio.load(str(input_path))
    
    # Ensure mono/stereo correct shape [channels, samples]
    if waveform.shape[0] > 2:
        waveform = waveform[:2, :]  # keep first 2 channels

    # Separate
    logger.info(f"[{task_id}] Running Demucs separation...")
    sources = apply_model(model, waveform, device=device)
    
    source_names = ["drums", "bass", "other", "vocals"]  # Demucs default order
    # Check if guitar was separated (depends on model variant)
    # htdemucs has 4 tracks; we map "other" as guitar/bass placeholder
    # For a 6-stem model, guitar would be separate — use "other" as approximation
    
    output_base = Path(os.getenv("OUTPUT_DIR", "./outputs")) / task_id
    output_base.mkdir(parents=True, exist_ok=True)
    
    result = {}
    for i, name in enumerate(source_names):
        out_path = output_base / f"{name}.wav"
        # Downmix to mono and save
        stem_waveform = sources[0, i] if sources.dim() == 3 else sources[i]
        if stem_waveform.dim() == 1:
            stem_waveform = stem_waveform.unsqueeze(0)
        torchaudio.save(str(out_path), stem_waveform.cpu(), sr)
        result[name] = out_path
        logger.info(f"[{task_id}] Saved stem: {name} → {out_path}")

    # Alias "guitar" to "other" for MVP (real guitar separation needs dedicated model)
    result["guitar"] = result.get("other", result["vocals"])
    return result


def _mock_separation(input_path: Path, task_id: str) -> Dict[str, Path]:
    """Fallback when Demucs is not available — returns original as all stems."""
    output_dir = Path(os.getenv("OUTPUT_DIR", "./outputs")) / task_id
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "vocals.wav"
    import shutil
    shutil.copy(str(input_path), str(out))
    return {"vocals": out, "guitar": out, "bass": out, "drums": out, "other": out}
