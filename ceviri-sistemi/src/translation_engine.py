#!/usr/bin/env python3
"""Translation Engine — Claude Sonnet 5 ile çok dilli çeviri.

Öncelik: claude CLI (abonelik — token ücreti YOK) → OpenRouter API fallback (yine Sonnet 5).
"""
import logging
import os
import re
import shutil
import subprocess
from openai import OpenAI
import config

logger = logging.getLogger(__name__)
_client = None


def _translate_via_cli(system_prompt: str, user_prompt: str) -> str | None:
    """claude CLI ile çeviri (Claude Pro/Max aboneliği — ücretsiz). Yoksa None."""
    claude_bin = shutil.which("claude")
    if not claude_bin or os.environ.get("LATO_DISABLE_CLI") == "1":
        return None
    try:
        model = config.TRANSLATION_MODEL.split("/")[-1]  # CLI bare ID ister
        r = subprocess.run(
            [claude_bin, "-p", "--model", model, "--output-format", "text",
             "--append-system-prompt", system_prompt],
            input=user_prompt.encode(), capture_output=True, timeout=90)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.decode(errors="ignore").strip()
        logger.warning(f"CLI çeviri rc={r.returncode}: {r.stderr.decode(errors='ignore')[:150]}")
    except Exception as e:
        logger.warning(f"CLI çeviri hatası: {e}")
    return None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=config.TRANSLATION_API_KEY,
            base_url=config.TRANSLATION_BASE_URL,
        )
    return _client


def detect_language_simple(text: str) -> str:
    """Hızlı alfabetik dil tespiti (fallback)."""
    thai_chars = len(re.findall(r'[\u0E00-\u0E7F]', text))
    turkish_chars = len(re.findall(r'[şçğıöüİŞÇĞÖÜ]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))

    if thai_chars > 3:
        return "th"
    if turkish_chars > 0 or (latin_chars > 0 and thai_chars == 0):
        # Could be TR or EN — check Turkish-specific chars
        if turkish_chars > 0:
            return "tr"
    return "en"


def translate_text(text: str, source_lang: str, target_langs: list[str],
                   speaker_name: str = None) -> dict:
    """
    Metni hedef dillere çevir.

    Args:
        text: Çevrilecek metin.
        source_lang: Kaynak dil kodu (th/tr/en).
        target_langs: Hedef dil kodları listesi.
        speaker_name: Konuşmacı adı (akses düzeltmeleri için).

    Returns:
        {lang_code: translated_text}
    """
    client = get_client()
    results = {}

    targets = [t for t in target_langs if t != source_lang]
    if not targets:
        return results

    # Tek istekte tüm dillere çevir (daha hızlı)
    target_names = ", ".join(
        f"{config.LANGUAGE_NAMES[t]} ({t})" for t in targets
    )

    system_prompt = """Sen Phuket, Tayland'da bir otel çevirmenisin.
Türkçe, Tayca ve İngilizce arasında profesyonel çeviri yaparsın.
Otel terminolojisini (oda, havuz, elektrik, klima, resepsiyon vb.) doğru çevirirsin.
Doğal, akıcı ve nazik bir ton kullanırsın."""

    user_prompt = f"""Aşağıdaki metni şu dillere çevir: {target_names}

Her çeviriyi şu formatta ver:
[lang_code] çeviri_metni

Örnek:
[tr] Merhaba
[en] Hello

Metin: {text}"""

    try:
        # 1) claude CLI — abonelik, ücretsiz
        raw = _translate_via_cli(system_prompt, user_prompt)

        # 2) API fallback (OpenRouter — yine Sonnet 5)
        if raw is None:
            response = client.chat.completions.create(
                model=config.TRANSLATION_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            raw = response.choices[0].message.content.strip()

        # Parse [lang] text format
        for match in re.finditer(r'\[(\w+)\]\s*(.+?)(?=\[\w+\]|$)', raw, re.DOTALL):
            lang_code = match.group(1).strip().lower()
            translated = match.group(2).strip()
            if lang_code in targets:
                results[lang_code] = translated

    except Exception as e:
        logger.error(f"Translation error: {e}")
        # Fallback: tek tek çevir
        for target in targets:
            try:
                target_name = config.LANGUAGE_NAMES[target]
                resp = client.chat.completions.create(
                    model=config.TRANSLATION_MODEL,
                    messages=[
                        {"role": "system", "content": f"Translate to {target_name}. Output only the translation."},
                        {"role": "user", "content": text},
                    ],
                    temperature=0.2,
                )
                results[target] = resp.choices[0].message.content.strip()
            except Exception as e2:
                logger.error(f"Fallback translation error for {target}: {e2}")
                results[target] = f"[çeviri hatası]"

    return results
