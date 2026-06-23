#!/usr/bin/env python3
"""Voice Registry — Speaker recognition (MFCC) + ElevenLabs voice clone management."""
import json
import logging
import subprocess
import numpy as np
from pathlib import Path
from python_speech_features import mfcc as extract_mfcc
from scipy.io import wavfile

import config

logger = logging.getLogger(__name__)
REGISTRY_PATH = config.DATA_DIR / "voice_registry.json"


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {"speakers": {}}


def save_registry(registry: dict):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def _to_wav_16k(audio_path: str) -> str:
    """Convert any audio to 16kHz mono WAV for processing."""
    wav_path = str(Path(audio_path).with_suffix(".16k.wav"))
    subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path,
         "-ar", "16000", "-ac", "1", "-f", "wav", wav_path],
        capture_output=True, timeout=30,
    )
    return wav_path


def extract_voice_fingerprint(audio_path: str) -> dict:
    """
    MFCC tabanlı ses parmak izi çıkar.
    Returns: {"mean": [...], "std": [...]}  (MFCC istatistikleri)
    """
    wav_path = _to_wav_16k(audio_path)
    try:
        sample_rate, signal = wavfile.read(wav_path)

        # Normalise
        if signal.dtype != np.float32:
            signal = signal.astype(np.float32) / 32768.0

        if len(signal) < sample_rate * 0.5:  # < 0.5s → too short
            logger.warning(f"Audio too short for fingerprint: {len(signal)/sample_rate:.1f}s")
            return {"mean": [], "std": []}

        mfcc_feat = extract_mfcc(
            signal, samplerate=sample_rate,
            numcep=config.MFCC_DIM, nfilt=26, nfft=512,
        )

        return {
            "mean": np.mean(mfcc_feat, axis=0).tolist(),
            "std": np.std(mfcc_feat, axis=0).tolist(),
        }
    except Exception as e:
        logger.error(f"Fingerprint extraction error: {e}")
        return {"mean": [], "std": []}
    finally:
        Path(wav_path).unlink(missing_ok=True)


def _cosine_similarity(a: list, b: list) -> float:
    a_arr = np.array(a, dtype=np.float64)
    b_arr = np.array(b, dtype=np.float64)
    if len(a_arr) == 0 or len(b_arr) == 0:
        return 0.0
    min_len = min(len(a_arr), len(b_arr))
    a_arr, b_arr = a_arr[:min_len], b_arr[:min_len]
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


def identify_speaker(audio_path: str) -> tuple:
    """
    Ses kaydından konuşmacıyı tanı.
    Returns: (speaker_name | None, confidence: float)
    """
    registry = load_registry()
    if not registry["speakers"]:
        return None, 0.0

    fingerprint = extract_voice_fingerprint(audio_path)
    if not fingerprint["mean"]:
        return None, 0.0

    best_match = None
    best_score = 0.0

    for name, data in registry["speakers"].items():
        stored = data.get("fingerprint", {})
        if not stored.get("mean"):
            continue
        score = _cosine_similarity(fingerprint["mean"], stored["mean"])
        logger.info(f"  Speaker match: {name} → {score:.3f}")
        if score > best_score:
            best_score = score
            best_match = name

    if best_score >= config.SPEAKER_SIMILARITY_THRESHOLD:
        return best_match, best_score
    return None, best_score


def register_speaker(name: str, audio_path: str, voice_id: str = None,
                     telegram_user_id: int = None) -> dict:
    """Yeni konuşmacı kaydet: fingerprint + opsiyonel ElevenLabs voice_id."""
    registry = load_registry()
    fingerprint = extract_voice_fingerprint(audio_path)

    # Save sample
    sample_path = config.VOICE_SAMPLES_DIR / f"{name}_sample.ogg"
    subprocess.run(
        ["cp", audio_path, str(sample_path)],
        capture_output=True,
    )

    existing = registry["speakers"].get(name, {})
    registry["speakers"][name] = {
        "fingerprint": fingerprint,
        "voice_id": voice_id or existing.get("voice_id"),
        "sample_path": str(sample_path),
        "telegram_user_id": telegram_user_id or existing.get("telegram_user_id"),
        "registered_samples": existing.get("registered_samples", 0) + 1,
    }

    save_registry(registry)
    logger.info(f"Speaker registered: {name} (voice_id={voice_id})")
    return registry["speakers"][name]


def get_voice_id(name: str) -> str | None:
    """Konuşmacının ElevenLabs voice_id'sini getir."""
    registry = load_registry()
    return registry["speakers"].get(name, {}).get("voice_id")


def clone_voice_elevenlabs(name: str, sample_path: str) -> str | None:
    """
    ElevenLabs ile ses klonla. voice_id döndür.
    ELEVENLABS_API_KEY yoksa None döner.
    """
    if not config.ELEVENLABS_API_KEY:
        logger.warning("ELEVENLABS_API_KEY not set — skipping voice clone")
        return None

    try:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)

        # Read sample audio
        with open(sample_path, "rb") as f:
            audio_data = f.read()

        voice = client.voices.ivc.create(
            name=f"Lato-{name}",
            files=[audio_data],
            description=f"Cloned voice for {name} — Lato Translation Bot",
        )

        voice_id = voice.voice_id
        logger.info(f"Voice cloned for {name}: voice_id={voice_id}")

        # Save voice_id to registry
        registry = load_registry()
        if name in registry["speakers"]:
            registry["speakers"][name]["voice_id"] = voice_id
            save_registry(registry)

        return voice_id

    except Exception as e:
        logger.error(f"Voice cloning error for {name}: {e}")
        return None


def list_speakers() -> dict:
    """Kayıtlı tüm konuşmacıları listele."""
    registry = load_registry()
    return registry["speakers"]
