from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np


def analyze_audio(file_path: str | Path) -> dict:
    """
    Analyze an audio file and return the metadata required by the assignment.

    Returns:
        duration_seconds
        sample_rate_khz
        bitrate_kbps
        loudness_db
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    # Load the audio without forcing a different sample rate.
    # sr=None preserves the original sample rate.
    audio, sample_rate = librosa.load(
        path,
        sr=None,
        mono=True,
    )

    if audio.size == 0:
        raise ValueError("The uploaded audio file contains no audio data.")

    # Duration in seconds.
    duration_seconds = float(len(audio) / sample_rate)

    if duration_seconds <= 0:
        raise ValueError("Audio duration must be greater than zero.")

    # Approximate bitrate from file size and duration.
    # This works for both compressed and uncompressed files as
    # an effective file bitrate.
    file_size_bytes = path.stat().st_size
    bitrate_kbps = float(
        (file_size_bytes * 8) / duration_seconds / 1000
    )

    # RMS loudness converted to decibels.
    rms = float(np.sqrt(np.mean(np.square(audio))))

    # Avoid log10(0) for complete silence.
    if rms <= 0:
        loudness_db = -100.0
    else:
        loudness_db = float(20 * np.log10(rms))

    return {
        "duration_seconds": round(duration_seconds, 3),
        "sample_rate_khz": round(sample_rate / 1000, 3),
        "bitrate_kbps": round(bitrate_kbps, 2),
        "loudness_db": round(loudness_db, 2),
    }