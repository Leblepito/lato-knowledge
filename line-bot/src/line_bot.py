#!/usr/bin/env python3
"""
Lato LINE Bot — Otel personeli için akıllı mesaj asistanı.

LINE (Tayland personel) ↔ Telegram (yönetim) köprüsü.
Her mesajı AI ile sınıflandırır, doğru departmana yönlendirir.

Gereksinimler:
  LINE_CHANNEL_ACCESS_TOKEN  — developers.line.biz
  LINE_CHANNEL_SECRET        — developers.line.biz
  TRANSLATE_BOT_TOKEN        — Telegram bot (mevcut)
  OPENROUTER_API_KEY         — AI sınıflandırma
  GOOGLE_API_KEY             — Gemini (OCR + çeviri fallback)
"""
import asyncio
import hashlib
import hmac
import base64
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import httpx
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("lato-line")

# ── Config ─────────────────────────────────────────────────────────
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
TG_TOKEN = os.environ.get("TRANSLATE_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"
OR_API = os.environ.get("OPENROUTER_API_KEY", "")
OR_MODEL = "openai/gpt-4o-mini"

TG_GROUP = -1003776134843
TG_TOPICS = {
    "ON_BURO": 132, "HK": 132, "FB": 134, "TEKNIK": 130,
    "GUVENLIK": 132, "MUHASEBE": 133, "YONETIM": 1,
}

# Staff registry: LINE user_id → name/role/dept
STAFF_REGISTRY_PATH = Path(__file__).parent / "data" / "line_staff.json"

for v in [LINE_TOKEN, LINE_SECRET, TG_TOKEN]:
    if not v:
        logger.warning(f"⚠️ Eksik env — LINE token/secret veya TG token")

FLAG = {"tr": "🇹🇷", "th": "🇹🇭", "en": "🇬🇧"}
DEPT_FLAG = {
    "ON_BURO": "🛎️", "HK": "🧹", "FB": "🍽️", "TEKNIK": "🔧",
    "GUVENLIK": "🔒", "MUHASEBE": "💰", "YONETIM": "🏨",
}


# ── Staff Registry ────────────────────────────────────────────────
def load_staff() -> dict:
    if STAFF_REGISTRY_PATH.exists():
        with open(STAFF_REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}}

def save_staff(data: dict):
    STAFF_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STAFF_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_staff(line_user_id: str) -> dict:
    return load_staff()["users"].get(line_user_id, {
        "name": "Bilinmeyen",
        "department": "GENEL",
        "role": "PERSONEL",
    })


# ── LINE API ──────────────────────────────────────────────────────
LINE_API = "https://api-data.line.me/v2/bot"
LINE_MSG_API = "https://api.line.me/v2/bot"

async def line_reply(reply_token: str, messages: list[dict]):
    """LINE'a mesaj gönder (reply)."""
    async with httpx.AsyncClient(timeout=30) as c:
        await c.post(f"{LINE_MSG_API}/message/reply", json={
            "replyToken": reply_token,
            "messages": messages,
        }, headers={"Authorization": f"Bearer {LINE_TOKEN}",
                     "Content-Type": "application/json"})

async def line_push(to_user_id: str, messages: list[dict]):
    """LINE'a push mesaj (proaktif)."""
    async with httpx.AsyncClient(timeout=30) as c:
        await c.post(f"{LINE_MSG_API}/message/push", json={
            "to": to_user_id,
            "messages": messages,
        }, headers={"Authorization": f"Bearer {LINE_TOKEN}",
                     "Content-Type": "application/json"})

async def download_line_content(message_id: str, msg_type: str) -> bytes:
    """LINE'dan image/audio/video indir."""
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(f"{LINE_API}/message/{message_id}/content",
                        headers={"Authorization": f"Bearer {LINE_TOKEN}"})
        return r.content


# ── Telegram ──────────────────────────────────────────────────────
async def tg_send(text: str, topic_id: int = 132):
    async with httpx.AsyncClient(timeout=30) as c:
        await c.post(f"{TG_API}/sendMessage", json={
            "chat_id": TG_GROUP, "message_thread_id": topic_id,
            "text": text,
        })

async def tg_send_photo(photo_path: str, caption: str, topic_id: int = 133):
    async with httpx.AsyncClient(timeout=60) as c:
        with open(photo_path, "rb") as f:
            await c.post(f"{TG_API}/sendPhoto",
                data={"chat_id": str(TG_GROUP), "message_thread_id": str(topic_id),
                      "caption": caption},
                files={"photo": (Path(photo_path).name, f, "image/jpeg")})


# ── AI Sınıflandırma Motoru ───────────────────────────────────────
CLASSIFY_SYSTEM = """Sen Phuket'te bir otel yönetim asistanısın. Gelen mesajı analiz et ve şu JSON formatında dön:

{
  "mesaj_tipi": "GOREV | TALIMAT | SONUC_RAPORU | GIDER_BILDIRIMI | SIKAYET | BILGI | ACIL",
  "kaynak_dil": "TR | EN | TH",
  "oncelik": "KRITIK | YUKSEK | NORMAL | DUSUK",
  "departman": "ON_BURO | HK | FB | TEKNIK | GUVENLIK | MUHASEBE | YONETIM",
  "ozet_tr": "Türkçe 1 cümle özet",
  "ozet_en": "English 1 sentence summary",
  "ozet_th": "สรุปภาษาไทย 1 ประโยค",
  "eylem": "Yapılması gereken iş",
  "tutar_var_mi": false,
  "tutar": null,
  "para_birimi": "THB | USD | null"
}

KURALLAR:
- "acil", "hemen", "ด่วน", "urgent" → KRITIK
- Fiyat/tutar → GIDER_BILDIRIMI + MUHASEBE
- Havuz/klima/elektrik → TEKNIK
- Oda temizlik → HK
- Misafir → ON_BURO
- SADECE JSON dön, başka metin yazma"""

async def classify_message(text: str) -> dict:
    """AI ile mesaj sınıflandırma."""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OR_API}"},
                json={
                    "model": OR_MODEL,
                    "messages": [
                        {"role": "system", "content": CLASSIFY_SYSTEM},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as e:
        logger.error(f"AI sınıflandırma hatası: {e}")
        return {
            "mesaj_tipi": "BILGI", "kaynak_dil": "tr", "oncelik": "NORMAL",
            "departman": "YONETIM", "ozet_tr": text[:100],
            "ozet_en": "", "ozet_th": "", "eylem": "",
            "tutar_var_mi": False, "tutar": None, "para_birimi": None,
        }


# ── OCR (Gemini Vision) ──────────────────────────────────────────
async def ocr_image(image_path: str) -> str:
    """Google Gemini ile fotoğraftan metin çıkar (fatura/dekont)."""
    import base64 as b64
    gemini_key = os.environ.get("GOOGLE_API_KEY", "")
    if not gemini_key:
        return ""

    with open(image_path, "rb") as f:
        img_b64 = b64.b64encode(f.read()).decode()

    try:
        base_url = "https://generativelanguage.googleapis.com/v1beta"
        gemini_url = base_url + "/models/gemini-2.0-flash:generateContent"
        full_url = gemini_url + "?key=" + gemini_key
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(full_url, json={
                "contents": [{
                    "parts": [
                        {"text": "Extract amounts, invoice no, date, company. Return JSON."},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                    ]
                }]
            })
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Extract JSON from response
            import re
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                return m.group(0)
            return text
    except Exception as e:
        logger.error(f"OCR hatası: {e}")
        return ""


# ── Mesaj İşleme ──────────────────────────────────────────────────
async def process_text_message(text: str, staff: dict, reply_token: str):
    """LINE text mesajını işle → sınıflandır → Telegram'a aktar."""
    t0 = time.time()
    name = staff.get("name", "?")
    dept = staff.get("department", "?")

    logger.info(f"📝 LINE mesaj: {name} ({dept}): {text[:60]}")

    # /register komutu — personel kaydı
    if text.startswith("/register"):
        await handle_register(text, staff, reply_token)
        return

    # AI sınıflandırma
    result = await classify_message(text)
    elapsed = time.time() - t0

    msg_type = result.get("mesaj_tipi", "BILGI")
    priority = result.get("oncelik", "NORMAL")
    target_dept = result.get("departman", "YONETIM")
    src_lang = result.get("kaynak_dil", "tr")

    # Telegram'a gönder
    topic_id = TG_TOPICS.get(target_dept, 132)
    priority_emoji = {"KRITIK": "🔴", "YUKSEK": "🟠", "NORMAL": "🟢", "DUSUK": "⚪"}
    type_emoji = {"GOREV": "📋", "ACIL": "🚨", "SIKAYET": "⚠️",
                  "GIDER_BILDIRIMI": "💵", "TALIMAT": "📢", "BILGI": "ℹ️"}

    tg_lines = [
        f"{type_emoji.get(msg_type, '📩')} **LINE → Telegram** {priority_emoji.get(priority, '')}",
        f"👤 **{name}** ({dept}) | {FLAG.get(src_lang, '')} {src_lang}",
        f"📦 {msg_type} | {priority}",
        "",
        f"💬 {text}",
        "",
    ]

    if result.get("ozet_tr"):
        tg_lines.append(f"📝 Özet: {result['ozet_tr']}")
    if result.get("ozet_th"):
        tg_lines.append(f"🇹🇭 {result['ozet_th']}")
    if result.get("ozet_en"):
        tg_lines.append(f"🇬🇧 {result['ozet_en']}")
    if result.get("eylem"):
        tg_lines.append(f"🎯 Aksiyon: {result['eylem']}")
    if result.get("tutar_var_mi") and result.get("tutar"):
        tg_lines.append(f"💰 Tutar: {result['tutar']:,.0f} {result.get('para_birimi', 'THB')}")

    tg_lines.append(f"\n⏱ {elapsed:.1f}s | 🤖 AI sınıflandırma")

    await tg_send("\n".join(tg_lines), topic_id)

    # LINE'a onay mesajı
    await line_reply(reply_token, [{
        "type": "text",
        "text": f"✅ Alındı! ({msg_type} / {priority})\n\n"
                f"🇹🇷 {result.get('ozet_tr', '')}\n"
                f"🇹🇭 {result.get('ozet_th', '')}\n"
                f"📤 Yönetim ekibine iletildi."
    }])

    logger.info(f"✅ İşlendi: {msg_type}/{priority} → Topic #{topic_id} ({elapsed:.1f}s)")


async def process_image_message(message_id: str, staff: dict, reply_token: str):
    """LINE fotoğraf → OCR → Telegram mutabakat."""
    name = staff.get("name", "?")
    logger.info(f"📸 LINE fotoğraf: {name}")

    # LINE'a bekleme mesajı
    await line_reply(reply_token, [{
        "type": "text", "text": "📷 Fotoğraf alındı, analiz ediliyor..."
    }])

    # İndir
    content = await download_line_content(message_id, "image")
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, dir="/tmp")
    tmp.write(content)
    tmp.close()

    # OCR
    ocr_result = await ocr_image(tmp.name)
    logger.info(f"📋 OCR: {ocr_result[:100] if ocr_result else 'boş'}")

    # Telegram'a gönder
    try:
        ocr_data = json.loads(ocr_result) if ocr_result else {}
        tutar = ocr_data.get("tutar", 0)
        firma = ocr_data.get("firma", "?")
        caption = (
            f"💵 **FATURA/GİDER** (LINE)\n"
            f"👤 {name}\n"
            f"🏢 {firma}\n"
            f"💰 {tutar:,.0f} THB\n"
            f"📅 {ocr_data.get('tarih', '?')}"
        )
        await tg_send_photo(tmp.name, caption, TG_TOPICS["MUHASEBE"])

        # LINE'a onay
        await line_push(staff.get("line_user_id", ""), [{
            "type": "text",
            "text": f"✅ Fatura alındı!\n🏢 {firma}\n💰 {tutar:,.0f} THB\n\nMuhasebeye iletildi."
        }])
    except (json.JSONDecodeError, Exception) as e:
        await tg_send_photo(tmp.name, f"📷 LINE foto ({name}) — OCR başarısız", TG_TOPICS["MUHASEBE"])

    os.unlink(tmp.name)


async def process_audio_message(message_id: str, staff: dict, reply_token: str):
    """LINE sesli mesaj → indir → çeviri sistemine yönlendir."""
    name = staff.get("name", "?")
    logger.info(f"🎙 LINE sesli mesaj: {name}")

    await line_reply(reply_token, [{
        "type": "text", "text": "🎙 Sesli mesaj alındı, çevriliyor..."
    }])

    # İndir
    content = await download_line_content(message_id, "audio")
    tmp = tempfile.NamedTemporaryFile(suffix=".m4a", delete=False, dir="/tmp")
    tmp.write(content)
    tmp.close()

    # TODO: Whisper STT + çeviri entegrasyonu
    # Şimdilik Telegram'a ses dosyası olarak gönder
    async with httpx.AsyncClient(timeout=60) as c:
        with open(tmp.name, "rb") as f:
            await c.post(f"{TG_API}/sendVoice",
                data={"chat_id": str(TG_GROUP), "message_thread_id": str(TG_TOPICS["YONETIM"]),
                      "caption": f"🎙 LINE voice ({name})"},
                files={"voice": (Path(tmp.name).name, f, "audio/m4a")})

    await line_push(staff.get("line_user_id", ""), [{
        "type": "text", "text": "✅ Sesli mesaj yönetime iletildi."
    }])

    os.unlink(tmp.name)


async def handle_register(text: str, staff: dict, reply_token: str):
    """/register İsim Departman — personel kaydı."""
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await line_reply(reply_token, [{
            "type": "text",
            "text": "📝 Kayıt için:\n/register [İsim] [Departman]\n\nÖrnek:\n/register Somchai TEKNIK\n/register Nong HK\n/register Kanya FB"
        }])
        return

    name = parts[1]
    dept = parts[2].upper()

    registry = load_staff()
    # Find by reply token's user — need user_id from webhook
    # This is a simplified version; actual registration from webhook
    await line_reply(reply_token, [{
        "type": "text",
        "text": f"✅ Kayıt alındı!\n👤 {name}\n🏢 {dept}\n\nYönetici onayından sonra aktif olacaktır."
    }])


# ── Webhook Handler ───────────────────────────────────────────────
async def line_webhook(request):
    """LINE webhook endpoint — mesajları yakalar."""
    # Signature doğrulama
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.text()

    if not verify_signature(body, signature):
        logger.warning("⚠️ LINE signature doğrulama başarısız")
        return web.Response(status=403)

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return web.Response(status=400)

    for event in data.get("events", []):
        if event.get("type") != "message":
            continue

        msg = event.get("message", {})
        source = event.get("source", {})
        line_user_id = source.get("userId", "")
        reply_token = event.get("replyToken", "")

        # Staff bilgisini al
        staff = get_staff(line_user_id)
        staff["line_user_id"] = line_user_id

        msg_type = msg.get("type")

        if msg_type == "text":
            asyncio.create_task(process_text_message(
                msg["text"], staff, reply_token))
        elif msg_type == "image":
            asyncio.create_task(process_image_message(
                msg["id"], staff, reply_token))
        elif msg_type == "audio":
            asyncio.create_task(process_audio_message(
                msg["id"], staff, reply_token))

    return web.Response(status=200)


def verify_signature(body: str, signature: str) -> bool:
    """LINE webhook signature doğrulama."""
    if not LINE_SECRET:
        return True  # dev mode
    hash_val = hmac.new(
        LINE_SECRET.encode(), body.encode(), hashlib.sha256
    ).digest()
    expected = base64.b64encode(hash_val).decode()
    return hmac.compare_digest(expected, signature)


# ── Health check ──────────────────────────────────────────────────
async def health(request):
    return web.json_response({
        "status": "ok",
        "bot": "lato-line",
        "line_connected": bool(LINE_TOKEN),
        "tg_connected": bool(TG_TOKEN),
        "timestamp": datetime.now().isoformat(),
    })


# ── Main ──────────────────────────────────────────────────────────
async def main():
    app = web.Application()
    app.router.add_post("/webhook", line_webhook)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8089)
    await site.start()

    logger.info(f"🚀 LINE Bot aktif — port 8089")
    logger.info(f"📍 Webhook URL: https://line.178-104-122-91.nip.io/webhook")
    logger.info(f"{'✅' if LINE_TOKEN else '❌'} LINE token")
    logger.info(f"{'✅' if TG_TOKEN else '❌'} Telegram token")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
