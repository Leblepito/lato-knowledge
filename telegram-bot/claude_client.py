#!/usr/bin/env python3
"""
Lato Claude İstemcisi — Sonnet 5, abonelik öncelikli (token ücreti YOK).

Sıra:
  1. `claude` CLI (Claude Pro/Max aboneliği — `claude setup-token` ile giriş yapılmışsa
     API faturası çıkmaz, plan limitleri dahilinde ÜCRETSİZ)  ← varsayılan
  2. Anthropic API (ANTHROPIC_API_KEY tanımlıysa — ücretli fallback)
  3. OpenRouter (OPENROUTER_API_KEY tanımlıysa — ücretli fallback)

Her üç yol da AYNI modeli kullanır: Claude Sonnet 5. Başka model yok.

Kullanım:
    from claude_client import ask_claude, parse_ai_json
    text = await ask_claude("soru", system="sen ...", files=["/tmp/foto.jpg"])
"""
import asyncio
import base64
import json
import logging
import os
import re
import shutil
from pathlib import Path

logger = logging.getLogger("claude-client")

# Tek model: Sonnet 5 (dateless pinned ID). Değiştirme noktası yine env.
MODEL = os.environ.get("LATO_AI_MODEL", "claude-sonnet-5")
# OpenRouter fallback için slug (anthropic/ öneki gerekir)
OR_MODEL = MODEL if "/" in MODEL else f"anthropic/{MODEL}"

CLI_TIMEOUT = int(os.environ.get("LATO_CLI_TIMEOUT", "240"))
MAX_TOKENS = int(os.environ.get("LATO_MAX_TOKENS", "4096"))

IMAGE_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
             ".webp": "image/webp", ".gif": "image/gif"}


class ClaudeError(RuntimeError):
    pass


def parse_ai_json(content: str) -> dict:
    """Model çıktısından JSON çıkar — ```json çitlerini ve çevre metni tolere eder."""
    content = (content or "").strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


# ── 1) claude CLI — abonelik, ücretsiz ─────────────────────────────
async def _ask_cli(prompt: str, system: str | None, files: list[str] | None,
                   cwd: str | None, timeout: int) -> str:
    claude_bin = shutil.which("claude")
    if not claude_bin or os.environ.get("LATO_DISABLE_CLI") == "1":
        raise ClaudeError("claude CLI yok/kapalı")

    cmd = [claude_bin, "-p", "--model", MODEL, "--output-format", "text"]
    if system:
        cmd += ["--append-system-prompt", system]
    if files:
        # Dosyalar cwd içinde olmalı; Read tool'una izin ver
        cmd += ["--allowedTools", "Read"]
        names = ", ".join(Path(f).name for f in files)
        prompt = f"Önce Read tool ile şu dosya(ları) oku: {names}\n\n{prompt}"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd or (str(Path(files[0]).parent) if files else None),
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(prompt.encode()), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise ClaudeError(f"CLI timeout ({timeout}s)")

    if proc.returncode != 0 or not out.strip():
        raise ClaudeError(f"CLI rc={proc.returncode}: {err.decode(errors='ignore')[:200]}")
    return out.decode(errors="ignore").strip()


# ── 2) Anthropic API — ücretli fallback ────────────────────────────
async def _ask_anthropic(prompt: str, system: str | None, files: list[str] | None,
                         timeout: int) -> str:
    import httpx
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ClaudeError("ANTHROPIC_API_KEY yok")

    content: list[dict] = []
    for f in files or []:
        p = Path(f)
        ext = p.suffix.lower()
        data = base64.b64encode(p.read_bytes()).decode()
        if ext in IMAGE_EXT:
            content.append({"type": "image",
                            "source": {"type": "base64", "media_type": IMAGE_EXT[ext], "data": data}})
        elif ext == ".pdf":
            content.append({"type": "document",
                            "source": {"type": "base64", "media_type": "application/pdf", "data": data}})
        else:
            logger.warning(f"API fallback: {p.name} tipi desteklenmiyor, atlanıyor")
    content.append({"type": "text", "text": prompt})

    body = {"model": MODEL, "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": content}]}
    if system:
        body["system"] = system

    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post("https://api.anthropic.com/v1/messages",
                         headers={"x-api-key": key,
                                  "anthropic-version": "2023-06-01",
                                  "content-type": "application/json"},
                         json=body)
        if r.status_code != 200:
            raise ClaudeError(f"Anthropic {r.status_code}: {r.text[:200]}")
        parts = r.json().get("content", [])
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()


# ── 3) OpenRouter — ücretli fallback ───────────────────────────────
async def _ask_openrouter(prompt: str, system: str | None, files: list[str] | None,
                          timeout: int) -> str:
    import httpx
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise ClaudeError("OPENROUTER_API_KEY yok")

    user_content: list[dict] = []
    for f in files or []:
        p = Path(f)
        ext = p.suffix.lower()
        if ext in IMAGE_EXT:
            data = base64.b64encode(p.read_bytes()).decode()
            user_content.append({"type": "image_url",
                                 "image_url": {"url": f"data:{IMAGE_EXT[ext]};base64,{data}"}})
        else:
            logger.warning(f"OpenRouter fallback: {p.name} tipi desteklenmiyor, atlanıyor")
    user_content.append({"type": "text", "text": prompt})

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_content})

    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post("https://openrouter.ai/api/v1/chat/completions",
                         headers={"Authorization": f"Bearer {key}"},
                         json={"model": OR_MODEL, "messages": messages,
                               "max_tokens": MAX_TOKENS})
        if r.status_code != 200:
            raise ClaudeError(f"OpenRouter {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"].strip()


# ── Ana giriş ──────────────────────────────────────────────────────
async def ask_claude(prompt: str, system: str | None = None,
                     files: list[str] | None = None,
                     cwd: str | None = None,
                     timeout: int = CLI_TIMEOUT) -> str:
    """Sonnet 5'e sor. Sıra: CLI (ücretsiz/abonelik) → Anthropic API → OpenRouter."""
    errors = []
    for name, fn in (("cli", _ask_cli), ("anthropic", _ask_anthropic), ("openrouter", _ask_openrouter)):
        try:
            if name == "cli":
                return await fn(prompt, system, files, cwd, timeout)
            return await fn(prompt, system, files, timeout)
        except ClaudeError as e:
            errors.append(f"{name}: {e}")
            logger.debug(f"{name} başarısız: {e}")
        except Exception as e:
            errors.append(f"{name}: {e}")
            logger.warning(f"{name} beklenmeyen hata: {e}")
    raise ClaudeError("Hiçbir Claude kanalı çalışmadı → " + " | ".join(errors))


if __name__ == "__main__":
    # Hızlı test: python3 claude_client.py "soru"
    import sys
    logging.basicConfig(level=logging.INFO)
    q = sys.argv[1] if len(sys.argv) > 1 else "Tek cümlede kendini tanıt."
    print(asyncio.run(ask_claude(q, system="Türkçe ve çok kısa cevap ver.")))
