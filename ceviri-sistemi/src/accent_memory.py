#!/usr/bin/env python3
"""Accent Memory — Konuşmacıya özel telaffuz/aksan düzeltmeleri."""
import json
import logging
from pathlib import Path

import config

logger = logging.getLogger(__name__)
CORRECTIONS_PATH = config.DATA_DIR / "accent_corrections.json"


def load_corrections() -> dict:
    if CORRECTIONS_PATH.exists():
        with open(CORRECTIONS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_corrections(corrections: dict):
    with open(CORRECTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(corrections, f, indent=2, ensure_ascii=False)


def add_correction(speaker_name: str, original: str, corrected: str,
                   language: str = None) -> bool:
    """
    Konuşmacı için telaffuz düzeltmesi ekle.
    Örn: speaker="Somchai", original="eletrik", corrected="elektrik"
    """
    corrections = load_corrections()
    if speaker_name not in corrections:
        corrections[speaker_name] = []

    # Aynı düzeltme varsa atla
    for c in corrections[speaker_name]:
        if c["original"].lower() == original.lower():
            c["corrected"] = corrected
            c["language"] = language
            save_corrections(corrections)
            return False  # updated existing

    corrections[speaker_name].append({
        "original": original,
        "corrected": corrected,
        "language": language,
    })
    save_corrections(corrections)
    logger.info(f"Correction added: {speaker_name}: '{original}' → '{corrected}'")
    return True  # new


def get_corrections(speaker_name: str) -> list:
    return load_corrections().get(speaker_name, [])


def apply_corrections(text: str, speaker_name: str) -> str:
    """Metindeki bilinen aksan hatalarını düzelt."""
    corrections = get_corrections(speaker_name)
    for c in corrections:
        text = text.replace(c["original"], c["corrected"])
    return text


def remove_correction(speaker_name: str, original: str) -> bool:
    corrections = load_corrections()
    if speaker_name not in corrections:
        return False
    before = len(corrections[speaker_name])
    corrections[speaker_name] = [
        c for c in corrections[speaker_name]
        if c["original"].lower() != original.lower()
    ]
    save_corrections(corrections)
    return len(corrections[speaker_name]) < before
