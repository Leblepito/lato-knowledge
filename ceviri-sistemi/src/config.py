#!/usr/bin/env python3
"""Lato Çeviri Botu — Konfigürasyon."""
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
VOICE_SAMPLES_DIR = DATA_DIR / "voice_samples"
AUDIO_OUTPUT_DIR = DATA_DIR / "audio_output"

# ── Telegram ───────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TRANSLATION_TOPIC_ID = 146          # 🌐 Çeviri / Translation / การแปล
GROUP_CHAT_ID = -1003776134843      # Phuket Lato grubu

# ── Diller ─────────────────────────────────────────────────────────
ACTIVE_LANGUAGES = ["th", "tr", "en"]
LANGUAGE_NAMES = {
    "th": "Tayca (ไทย)",
    "tr": "Türkçe",
    "en": "English",
}
LANGUAGE_FLAGS = {"th": "🇹🇭", "tr": "🇹🇷", "en": "🇬🇧"}

# ── STT (faster-whisper) ───────────────────────────────────────────
WHISPER_MODEL_SIZE = "base"     # tiny|base|small|medium|large-v3 (base=fast for streaming)
WHISPER_DEVICE = "cpu"          # cpu|cuda
WHISPER_COMPUTE_TYPE = "int8"   # int8|float16|float32

# ── Çeviri (OpenRouter) ────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TRANSLATION_PROVIDER = "openrouter"   # openrouter | openai
TRANSLATION_BASE_URL = "https://openrouter.ai/api/v1"
TRANSLATION_API_KEY = OPENROUTER_API_KEY or OPENAI_API_KEY
# Tek model: Claude Sonnet 5. Öncelik claude CLI (abonelik — ücretsiz, translation_engine
# içinde); bu API modeli sadece CLI yoksa fallback olarak kullanılır.
_tm = os.environ.get("LATO_TRANSLATE_MODEL", os.environ.get("LATO_AI_MODEL", "claude-sonnet-5"))
TRANSLATION_MODEL = _tm if "/" in _tm else f"anthropic/{_tm}"   # OpenRouter slug normalizasyonu

# ── TTS ────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_MODEL = "eleven_multilingual_v2"
OPENAI_TTS_MODEL = "gpt-4o-mini-tts"

# ElevenLabs default voice (Lato asistan sesi)
ELEVENLABS_DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"

# ── Speaker Recognition ────────────────────────────────────────────
SPEAKER_SIMILARITY_THRESHOLD = 0.72   # cosine similarity
MFCC_DIM = 13

# ── Dirs ───────────────────────────────────────────────────────────
for d in [DATA_DIR, VOICE_SAMPLES_DIR, AUDIO_OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
