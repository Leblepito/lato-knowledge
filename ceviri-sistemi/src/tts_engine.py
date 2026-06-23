#!/usr/bin/env python3
"""TTS Engine — ElevenLabs (klonlanmış ses) + OpenAI fallback."""
import logging
import hashlib
from pathlib import Path

import config

logger = logging.getLogger(__name__)


def _hash_filename(text: str, ext: str = ".ogg") -> str:
    h = hashlib.md5(text.encode()).hexdigest()[:12]
    return str(config.AUDIO_OUTPUT_DIR / f"tts_{h}{ext}")


def synthesize_elevenlabs(text: str, voice_id: str, output_path: str = None) -> str:
    """ElevenLabs ile ses üret (klonlanmış veya preset ses)."""
    if output_path is None:
        output_path = _hash_filename(text)

    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=config.ELEVENLABS_MODEL,
        text=text,
        output_format="mp3_44100_128",
    )

    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)

    # Convert to OGG for Telegram voice message
    ogg_path = output_path.rsplit(".", 1)[0] + ".ogg"
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-i", output_path, "-c:a", "libopus",
         "-b:a", "64k", "-ar", "48000", ogg_path],
        capture_output=True, timeout=30,
    )
    Path(output_path).unlink(missing_ok=True)
    return ogg_path


def synthesize_openai(text: str, voice: str = "alloy", output_path: str = None) -> str:
    """OpenAI TTS fallback."""
    if output_path is None:
        output_path = _hash_filename(text)

    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    mp3_path = output_path.replace(".ogg", ".mp3")
    response = client.audio.speech.create(
        model=config.OPENAI_TTS_MODEL,
        voice=voice,
        input=text,
        response_format="mp3",
    )
    response.stream_to_file(mp3_path)

    # Convert to OGG for Telegram
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus",
         "-b:a", "64k", "-ar", "48000", output_path],
        capture_output=True, timeout=30,
    )
    Path(mp3_path).unlink(missing_ok=True)
    return output_path


def synthesize_edge(text: str, voice: str = "en-US-AriaNeural",
                    output_path: str = None) -> str:
    """Free Microsoft Edge TTS via subprocess CLI — robust, no async issues."""
    if output_path is None:
        output_path = _hash_filename(text)

    import subprocess
    subprocess.run(
        ["edge-tts", "--voice", voice, "--text", text,
         "--write-media", output_path],
        capture_output=True, timeout=30,
    )
    if not Path(output_path).exists() or Path(output_path).stat().st_size < 100:
        logger.warning(f"Edge TTS empty output for voice={voice}, trying fallback")
        # Fallback: use subprocess with shell
        subprocess.run(
            f'edge-tts --voice "{voice}" --text "{text[:500]}" --write-media "{output_path}"',
            shell=True, capture_output=True, timeout=30,
        )
    return output_path


def synthesize(text: str, voice_id: str = None, language: str = None,
               speaker_name: str = None) -> str:
    """
    Ses üret. Öncelik sırası:
    1. ElevenLabs (klonlanmış ses) — API key + voice_id varsa
    2. Edge TTS (ücretsiz) — tüm diller için

    Returns: OGG dosya yolu (Telegram voice message için).
    """
    # Accent düzeltmelerini uygula
    if speaker_name:
        from accent_memory import apply_corrections
        text = apply_corrections(text, speaker_name)

    # 1. ElevenLabs (voice cloning)
    if config.ELEVENLABS_API_KEY and voice_id:
        logger.info(f"TTS: ElevenLabs voice={voice_id[:8]}...")
        try:
            return synthesize_elevenlabs(text, voice_id)
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}, falling back to Edge TTS")

    # 2. Edge TTS (free, multilingual)
    edge_voices = {
        "th": "th-TH-PremwadeeNeural",   # Thai female (natural)
        "tr": "tr-TR-EmelNeural",         # Turkish female
        "en": "en-US-AriaNeural",         # English female
    }
    voice = edge_voices.get(language, "en-US-AriaNeural")
    logger.info(f"TTS: Edge voice={voice}")
    mp3_path = synthesize_edge(text, voice=voice)

    # Convert to OGG Opus for Telegram
    ogg_path = mp3_path.replace(".ogg", "_voice.ogg")
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus",
         "-b:a", "64k", "-ar", "48000", ogg_path],
        capture_output=True, timeout=30,
    )
    Path(mp3_path).unlink(missing_ok=True)
    return ogg_path
