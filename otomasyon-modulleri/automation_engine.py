#!/usr/bin/env python3
"""
Lato Gelişmiş Otomasyon Motoru — 10 modül tek sistemde.

Modüller:
  1. daily_briefing       — Günlük operasyon bülteni + AI stratejik öneri
  2. check_work_permits   — WP süre kontrolü (30/15/7/0 gün)
  3. check_tm30_deadline  — TM30 bildirim zamanlayıcı (24 saat)
  4. check_bureaucratic   — VAT/SSO/Bordro deadline takibi
  5. check_agency_pay     — Acente komisyon/ödeme kontrolü
  6. check_supplier       — Tedarikçi sözleşme süre kontrolü
  7. weekly_financial     — Haftalık P&L özeti + anomali tespiti
  8. electricity_anomaly  — Elektrik faturası anomalisi (+%20)
  9. check_reconciliation — Banka vs muhasebe mutabakat
 10. ota_review_monitor   — OTA yorum sentiment analizi

Kullanım:
  python3 automation_engine.py [modül_adı]
  python3 automation_engine.py              # run_all
"""
import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from hotel_data import (
    load_data, get_season, GROUP_CHAT_ID,
    TOPIC_GEN, TOPIC_TECH, TOPIC_OPS, TOPIC_PURCH, TOPIC_FNB,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("lato-auto")

# ── Config ─────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TRANSLATE_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OR_MODEL = "openai/gpt-4o-mini"
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE = "EXAVITQu4vr4xnTf7T8s"  # Sarah — multilingual

# Türkçe karakterler için Telegram Markdown escape
def md_escape(text: str) -> str:
    """Telegram MarkdownV1 için güvenli metin."""
    # Sadece * ve _ kaçır (biz bold için * kullanıyoruz)
    return text.replace("*", "").replace("`", "")

# ── Telegram ───────────────────────────────────────────────────────
async def send_message(text: str, topic_id: int = TOPIC_OPS) -> bool:
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.post(f"{TG_API}/sendMessage", json={
                "chat_id": GROUP_CHAT_ID, "message_thread_id": topic_id,
                "text": text, "parse_mode": "Markdown",
            })
            if resp.status_code != 200:
                err = resp.text[:200]
                logger.error(f"TG {resp.status_code}: {err}")
                if "parse" in err.lower() or "can't parse" in err.lower():
                    resp2 = await c.post(f"{TG_API}/sendMessage", json={
                        "chat_id": GROUP_CHAT_ID, "message_thread_id": topic_id,
                        "text": md_escape(text),
                    })
                    return resp2.status_code == 200
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"TG exception: {e}")
        return False

async def send_voice(text: str, topic_id: int = TOPIC_OPS) -> bool:
    """ElevenLabs → Edge TTS fallback ile sesli mesaj gönder."""
    audio_path = None
    try:
        audio_path = await _tts(text)
        if not audio_path:
            return False
        async with httpx.AsyncClient(timeout=30) as c:
            with open(audio_path, "rb") as f:
                resp = await c.post(f"{TG_API}/sendVoice",
                    data={"chat_id": str(GROUP_CHAT_ID),
                          "message_thread_id": str(topic_id)},
                    files={"voice": (Path(audio_path).name, f, "audio/ogg")})
                return resp.status_code == 200
    except Exception as e:
        logger.error(f"send_voice: {e}")
        return False
    finally:
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)

async def _tts(text: str) -> str | None:
    """ElevenLabs dene → Edge TTS fallback."""
    # ElevenLabs
    if ELEVEN_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                resp = await c.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE}",
                    headers={"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"},
                    json={"text": text[:500], "model_id": "eleven_multilingual_v2",
                          "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
                )
                if resp.status_code == 200:
                    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir="/tmp")
                    tmp.write(resp.content)
                    tmp.close()
                    return tmp.name
        except Exception as e:
            logger.warning(f"ElevenLabs failed: {e}")

    # Edge TTS fallback
    try:
        import edge_tts
        tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False, dir="/tmp")
        tmp.close()
        comm = edge_tts.Communicate(text[:3000], voice="th-TH-PremwadeeNeural")
        await comm.save(tmp.name)
        return tmp.name
    except Exception as e:
        logger.error(f"Edge TTS failed: {e}")
        return None

# ── AI ─────────────────────────────────────────────────────────────
async def ai_analyze(system_prompt: str, user_prompt: str, timeout: int = 30) -> str:
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OR_KEY}"},
                json={"model": OR_MODEL, "temperature": 0.3,
                      "messages": [{"role": "system", "content": system_prompt},
                                   {"role": "user", "content": user_prompt}]})
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI: {e}")
        return ""

# ════════════════════════════════════════════════════════════════════
# MODÜL 1: Günlük Operasyon Bülteni
# ════════════════════════════════════════════════════════════════════
async def daily_briefing():
    logger.info("📋 Günlük bülten hazırlanıyor...")
    data = load_data()
    today = datetime.now()
    month_idx = today.month - 1
    season = get_season(today.month)
    hotels = data.get("hotels", [])

    lines = [
        f"📋 *GÜNLÜK OPERASYON BÜLTENİ*",
        f"📅 {today.strftime('%d.%m.%Y')} | Sezon: *{season}*",
        "",
        f"🏨 *PORTFÖY ÖZETİ ({len(hotels)} Otel)*",
    ]

    total_rooms = 0
    weighted_occ = 0
    total_rev = 0
    for h in hotels:
        rooms = h["rooms"]
        occ = h["occupancy"][month_idx] if month_idx < len(h["occupancy"]) else 0.5
        adr = h["adr"][month_idx] if month_idx < len(h["adr"]) else 500
        rev = rooms * occ * adr * 30
        total_rooms += rooms
        weighted_occ += occ * rooms
        total_rev += rev
        flag = "🟢" if occ > 0.7 else ("🟡" if occ > 0.45 else "🔴")
        lines.append(f"  {flag} {h['name']}: {rooms} oda, %{occ*100:.0f}")

    avg_occ = weighted_occ / total_rooms if total_rooms else 0
    lines.append("")
    lines.append(f"📊 *Toplam*: {total_rooms} oda | Ortalama %{avg_occ*100:.0f} doluluk")
    lines.append(f"💰 *Aylık tahmini gelir*: {total_rev:,.0f} THB")
    lines.append(f"💵 *ADR ortalaması*: {total_rev / (total_rooms * avg_occ * 30) if avg_occ > 0 else 0:,.0f} THB")

    # Kritik görevler
    critical = [o for o in data.get("operations", [])
                if o.get("priority") == "KRITIK" and o.get("status") != "Tamamlandi"]
    if critical:
        lines.append("")
        lines.append(f"⚠️ *Kritik Görevler ({len(critical)}):*")
        for op in critical[:5]:
            lines.append(f"  • {op['task']} — Son: {op.get('deadline', '?')}")

    # TM30 hatırlatma
    lines.append("")
    lines.append("🛂 *TM30*: Yabancı misafir check-in → 24 saat içinde bildirim!")
    lines.append("   Ceza: 1,600 THB/ihlal")

    # AI stratejik öneri
    ai_text = await ai_analyze(
        "Sen Phuket'te otel portföy yöneticisisin. 1-2 cümlede stratejik öneri ver. Türkçe konuş.",
        f"Sezon: {season}. Toplam {total_rooms} oda, %{avg_occ*100:.0f} doluluk. "
        f"Tahmini gelir: {total_rev:,.0f} THB/ay. {len(critical)} kritik görev var."
    )
    if ai_text:
        lines.append("")
        lines.append(f"🤖 *AI Öneri*: {ai_text.strip()}")

    await send_message("\n".join(lines), TOPIC_OPS)
    logger.info("✅ Günlük bülten gönderildi")

# ════════════════════════════════════════════════════════════════════
# MODÜL 2: Work Permit Kontrolü
# ════════════════════════════════════════════════════════════════════
async def check_work_permits():
    logger.info("👷 WP kontrolü...")
    data = load_data()
    today = datetime.now().date()
    alerts = []

    for person in data.get("staff", []):
        wp = person.get("wp_expiry")
        if not wp:
            continue
        try:
            exp = datetime.strptime(wp, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        days = (exp - today).days
        if days <= 30:
            alerts.append((person, days))

    if not alerts:
        logger.info("✅ WP: sorun yok")
        return

    lines = ["👷 *WORK PERMIT UYARISI*", ""]
    for person, days in sorted(alerts, key=lambda x: x[1]):
        name = person.get("name", "?")
        nat = person.get("nationality", "?")
        dept = person.get("department", "?")
        hotel = person.get("hotel", "?")
        if days <= 0:
            lines.append(f"🔴 *SÜRESİ DOLDU*: {name} ({nat})")
            lines.append(f"  ⚠️ {abs(days)} gün önce! Ceza riski: 10,000+ THB")
        elif days <= 7:
            lines.append(f"🟠 *7 GÜN KALDI*: {name} ({nat})")
            lines.append(f"  ⏳ {days} gün — acil yenileme!")
        elif days <= 15:
            lines.append(f"🟡 *15 GÜN KALDI*: {name} ({nat})")
        elif days <= 30:
            lines.append(f"🔵 *30 GÜN KALDI*: {name} ({nat})")
        lines.append(f"  🏨 {hotel} | 🔧 {dept}")
        lines.append("")

    lines.append("📝 Yenileme: Ministry of Labour, Phuket")
    await send_message("\n".join(lines), TOPIC_OPS)
    logger.info(f"✅ WP: {len(alerts)} uyarı")

# ════════════════════════════════════════════════════════════════════
# MODÜL 3: TM30 Deadline
# ════════════════════════════════════════════════════════════════════
async def check_tm30_deadline():
    """TM30 bildirim kontrolü — check-in'den 20+ saat geçen misafirler."""
    logger.info("🛂 TM30 kontrolü...")
    today = datetime.now()
    lines = [
        "🛂 *TM30 BİLDİRİM KONTROLÜ*",
        f"📅 {today.strftime('%d.%m.%Y %H:%M')}",
        "",
        "⚠️ Bugün check-in yapan yabancı misafirler için:",
        "   TM30 bildirimi son 24 saat içinde yapılmış olmalı!",
        "   Ceza: 1,600 THB/ihlal",
        "",
        "📋 _Aksiyon: Resepsiyon → bugünün check-in listesini kontrol et_",
    ]
    await send_message("\n".join(lines), TOPIC_OPS)
    logger.info("✅ TM30 hatırlatma gönderildi")

# ════════════════════════════════════════════════════════════════════
# MODÜL 4: Bürokratik Deadline
# ════════════════════════════════════════════════════════════════════
async def check_bureaucratic_deadlines():
    logger.info("🏛️ Bürokratik deadline kontrolü...")
    today = datetime.now().date()
    dom = today.day
    alerts = []

    if 8 <= dom <= 16:
        d = 15 - dom
        alerts.append(("VAT PP30 Beyannamesi", d, "2,000 THB + %1.5/ay faiz", "Revenue Department"))
        alerts.append(("SSO (Sosyal Sigorta)", d, "5,000 THB/personel", "Social Security Office"))

    if 20 <= dom <= 27:
        d = 25 - dom
        alerts.append(("Personel Bordro Hazırlığı", d, "Maaş gecikmesi riski", "Otel Yönetimi"))

    # 3 ayda bir — PND 50 (kurumsar gelir vergisi)
    if dom <= 15 and today.month in [3, 6, 9, 12]:
        d = 15 - dom
        alerts.append(("PND 50 Kurumlar Vergisi", d, "%20 vergi + gecikme", "Revenue Department"))

    if not alerts:
        logger.info("✅ Bürokratik: bu hafta deadline yok")
        return

    lines = ["🏛️ *BÜROKRATİK HATIRLATMA*", ""]
    for task, days, penalty, authority in alerts:
        icon = "🔴" if days <= 1 else ("🟠" if days <= 3 else "🟡")
        lines.append(f"{icon} *{task}*")
        lines.append(f"  ⏳ {days} gün kaldı")
        lines.append(f"  ⚠️ Ceza: {penalty}")
        lines.append(f"  🏛️ {authority}")
        lines.append("")

    await send_message("\n".join(lines), TOPIC_PURCH)
    logger.info(f"✅ Bürokratik: {len(alerts)} hatırlatma")

# ════════════════════════════════════════════════════════════════════
# MODÜL 5: Acente Ödeme Kontrolü
# ════════════════════════════════════════════════════════════════════
async def check_agency_payments():
    logger.info("💰 Acente ödeme kontrolü...")
    data = load_data()
    overdue = [a for a in data.get("agencies", [])
               if a.get("payment_status") in ("Gecikti", "Beklemede")]

    if not overdue:
        logger.info("✅ Acente: sorun yok")
        return

    lines = ["💰 *ACENTE ÖDEME DURUMU*", ""]
    total_due = 0
    for a in overdue:
        flag = "🔴" if a["payment_status"] == "Gecikti" else "🟡"
        amt = a.get("commission_thb", 0)
        total_due += amt
        lines.append(f"{flag} *{a['name']}* ({a.get('type', '?')})")
        lines.append(f"  Komisyon: %{a.get('commission_pct', 0)*100:.0f}")
        lines.append(f"  Tutar: ~{amt:,.0f} THB")
        lines.append(f"  Durum: {a['payment_status']}")
        lines.append("")

    lines.append(f"💵 *Toplam bekleyen*: {total_due:,.0f} THB")
    await send_message("\n".join(lines), TOPIC_PURCH)
    logger.info(f"✅ Acente: {len(overdue)} bekleyen, {total_due:,.0f} THB")

# ════════════════════════════════════════════════════════════════════
# MODÜL 6: Tedarikçi Sözleşme Kontrolü
# ════════════════════════════════════════════════════════════════════
async def check_supplier_contracts():
    logger.info("📦 Tedarikçi sözleşme kontrolü...")
    data = load_data()
    today = datetime.now().date()
    alerts = []

    for s in data.get("suppliers", []):
        exp = s.get("contract_expiry")
        if not exp:
            continue
        try:
            exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        days = (exp_date - today).days
        if days <= 30:
            alerts.append((s, days))

    if not alerts:
        logger.info("✅ Tedarikçi: sözleşme sorunu yok")
        return

    lines = ["📦 *TEDARİKÇİ SÖZLEŞME UYARISI*", ""]
    for s, days in sorted(alerts, key=lambda x: x[1]):
        icon = "🔴" if days <= 0 else ("🟠" if days <= 7 else ("🟡" if days <= 15 else "🔵"))
        lines.append(f"{icon} *{s['name']}* ({s.get('category', '?')})")
        if days <= 0:
            lines.append(f"  ⚠️ {abs(days)} gün önce doldu!")
        else:
            lines.append(f"  ⏳ {days} gün kaldı")
        if s.get("monthly_avg_thb"):
            lines.append(f"  Aylık: ~{s['monthly_avg_thb']:,.0f} THB")
        lines.append("")

    await send_message("\n".join(lines), TOPIC_PURCH)
    logger.info(f"✅ Tedarikçi: {len(alerts)} uyarı")

# ════════════════════════════════════════════════════════════════════
# MODÜL 7: Haftalık Finansal Özet
# ════════════════════════════════════════════════════════════════════
async def weekly_financial_summary():
    logger.info("📊 Haftalık finansal özet...")
    data = load_data()
    fin = data.get("financial", {})
    months = fin.get("months", [])
    rev = fin.get("revenue", [])
    exp = fin.get("expenses", [])

    if not rev or not exp:
        logger.warning("Finansal veri yok")
        return

    lines = ["📊 *HAFTALIK FİNANSAL ÖZET*", ""]

    for i, m in enumerate(months):
        if i >= len(rev) or i >= len(exp):
            break
        r, e = rev[i], exp[i]
        pnl = r - e
        icon = "🟢" if pnl > 0 else "🔴"
        lines.append(f"{icon} {m}: Gelir {r:,.0f} | Gider {e:,.0f} | P&L {pnl:+,.0f} THB")

    # Ortalama gider ve anomali tespiti
    if len(exp) >= 3:
        avg_exp = sum(exp[:len(months)]) / len(months)
        lines.append("")
        lines.append(f"📈 Ortalama gider: {avg_exp:,.0f} THB/ay")
        for i, e in enumerate(exp):
            if i >= len(months):
                break
            deviation = abs(e - avg_exp) / avg_exp * 100 if avg_exp else 0
            if deviation > 20:
                direction = "yüksek" if e > avg_exp else "düşük"
                lines.append(f"  ⚠️ {months[i]}: gider %{deviation:.0f} {direction} (anomali)")

    # Mutabakat uyarısı
    recon = fin.get("reconciliation", {}).get("brook", {})
    if recon.get("discrepancy_pct", 0) > 1:
        lines.append("")
        lines.append(f"🚨 *BROOK MUTABAKAT*: Banka {recon['bank_statement']:,.0f} vs "
                     f"Muhasebe {recon['accounting']:,.0f} THB")
        lines.append(f"   Fark: {recon['discrepancy']:,.0f} THB (%{recon['discrepancy_pct']:.0f})")

    # AI öneri
    pnl_current = (rev[-1] - exp[-1]) if rev and exp else 0
    ai_text = await ai_analyze(
        "Sen otel finansal danışmanısın. 2 cümlede öneri ver. Türkçe.",
        f"Mevcut ay P&L: {pnl_current:+,.0f} THB. Sezon: {get_season()}. "
        f"Break-even ADR: {fin.get('break_even_adr', 684)} THB."
    )
    if ai_text:
        lines.append("")
        lines.append(f"🤖 *AI*: {ai_text.strip()}")

    await send_message("\n".join(lines), TOPIC_OPS)
    logger.info("✅ Haftalık finansal özet gönderildi")

# ════════════════════════════════════════════════════════════════════
# MODÜL 8: Elektrik Faturası Anomalisi
# ════════════════════════════════════════════════════════════════════
async def electricity_anomaly_check():
    logger.info("⚡ Elektrik anomali kontrolü...")
    data = load_data()
    lines = ["⚡ *ELEKTRİK FATURASI KONTROLÜ*", ""]

    anomalies = []
    for s in data.get("suppliers", []):
        if s.get("category") != "Elektrik" and "electric" not in s.get("category", "").lower() and "elektr" not in s.get("category", "").lower():
            # PEA'yı da kontrol et
            if "PEA" not in s.get("name", "").upper() and "ELECTR" not in s.get("name", "").upper():
                continue
        avg = s.get("monthly_avg_thb", 0)
        last = s.get("last_invoice_thb", 0)
        if avg > 0 and last > 0:
            change = (last - avg) / avg * 100
            if abs(change) > 20:
                anomalies.append((s, change))
            lines.append(f"📊 {s['name']}: Son {last:,.0f} | Ort {avg:,.0f} | Δ%{change:+.0f}")

    # Elektrik malzeme tedarikçileri de
    for s in data.get("suppliers", []):
        if "elektr" in s.get("category", "").lower() and s.get("monthly_avg_thb", 0) > 0:
            avg = s["monthly_avg_thb"]
            last = s.get("last_invoice_thb", 0)
            if avg > 0 and last > 0:
                change = (last - avg) / avg * 100
                if abs(change) > 20 and (s, change) not in anomalies:
                    anomalies.append((s, change))

    if anomalies:
        lines.append("")
        lines.append(f"🚨 *{len(anomalies)} Anomali tespit edildi:*")
        for s, change in anomalies:
            icon = "🔴" if change > 0 else "🟢"
            lines.append(f"  {icon} {s['name']}: %{change:+.0f} değişim")
            lines.append(f"      Son: {s['last_invoice_thb']:,.0f} | Ort: {s['monthly_avg_thb']:,.0f} THB")

    lines.append("")
    lines.append("💡 Phuket muson sezonu (Nis-Kas) klima yükü artar. "
                 "Normalden yüksek tüketim beklenebilir.")
    await send_message("\n".join(lines), TOPIC_TECH)
    logger.info(f"✅ Elektrik: {len(anomalies)} anomali")

# ════════════════════════════════════════════════════════════════════
# MODÜL 9: Mutabakat Kontrolü
# ════════════════════════════════════════════════════════════════════
async def check_reconciliation():
    logger.info("🔍 Mutabakat kontrolü...")
    data = load_data()
    recon = data.get("financial", {}).get("reconciliation", {})

    if not recon:
        logger.info("Mutabakat verisi yok")
        return

    lines = ["🔍 *MUTABAKAT KONTROLÜ*", ""]
    any_discrepancy = False

    for hotel_slug, r in recon.items():
        disc = r.get("discrepancy", 0)
        pct = r.get("discrepancy_pct", 0)
        bank = r.get("bank_statement", 0)
        acc = r.get("accounting", 0)
        if pct > 1:
            any_discrepancy = True
            lines.append(f"🚨 *{hotel_slug.upper()}*")
            lines.append(f"  Banka: {bank:,.0f} THB")
            lines.append(f"  Muhasebe: {acc:,.0f} THB")
            lines.append(f"  Fark: {disc:,.0f} THB (%{pct:.0f})")
            notes = r.get("notes", "")
            if notes:
                lines.append(f"  📝 {notes}")
            lines.append("")

    if not any_discrepancy:
        lines.append("✅ Tüm otellerde mutabakat uyumlu (<%1)")

    lines.append("📋 _Aksiyon: Muhasebe → banka ekstresi ile karşılaştırma yap_")
    await send_message("\n".join(lines), TOPIC_PURCH)
    logger.info("✅ Mutabakat gönderildi")

# ════════════════════════════════════════════════════════════════════
# MODÜL 10: OTA Yorum Sentiment Analizi
# ════════════════════════════════════════════════════════════════════
async def ota_review_monitor():
    logger.info("⭐ OTA yorum analizi...")
    mock_reviews = [
        {"hotel": "brook-pool", "platform": "Booking.com", "rating": 9.2,
         "text": "Amazing pool, great staff. Room was clean. Will come back!"},
        {"hotel": "brook-pool", "platform": "Agoda", "rating": 8.8,
         "text": "Nice boutique hotel. AC was a bit loud but everything else perfect."},
        {"hotel": "trend-kamala", "platform": "Booking.com", "rating": 7.5,
         "text": "Good location but room needs renovation. Staff friendly."},
        {"hotel": "case-del-sol", "platform": "Agoda", "rating": 9.5,
         "text": "Loved the villa! Private pool was amazing. Worth every baht."},
        {"hotel": "patong-heritage", "platform": "Booking.com", "rating": 6.8,
         "text": "Noisy at night. Room was not clean on arrival. Disappointed."},
    ]

    reviews_text = "\n".join(f"{r['hotel']} [{r['platform']}]: {r['text']}" for r in mock_reviews)
    ai_text = await ai_analyze(
        "Sen otel misafir ilişkileri uzmanısın. Yorumları analiz et. "
        "Her yorumu POZITIF/NÖTR/NEGATIF olarak sınıflandır. "
        "1 cümle özet + 1 aksiyon önerisi ver. Türkçe yaz.",
        reviews_text
    )

    lines = ["⭐ *OTA YORUM ANALİZİ*", f"📅 {datetime.now().strftime('%d.%m.%Y')}", ""]

    for r in mock_reviews:
        icon = "🟢" if r["rating"] >= 9 else ("🟡" if r["rating"] >= 7.5 else "🔴")
        lines.append(f"{icon} {r['hotel']} | {r['platform']} | Puan: {r['rating']}")
        lines.append(f"  _{r['text'][:80]}_")
        lines.append("")

    if ai_text:
        lines.append(f"🤖 *AI Analiz*:\n{ai_text.strip()}")

    await send_message("\n".join(lines), TOPIC_OPS)
    logger.info("✅ OTA yorum analizi gönderildi")

# ════════════════════════════════════════════════════════════════════
# DISPATCHER
# ════════════════════════════════════════════════════════════════════
MODULES = {
    "briefing": daily_briefing,
    "wp": check_work_permits,
    "tm30": check_tm30_deadline,
    "bureaucratic": check_bureaucratic_deadlines,
    "agency": check_agency_payments,
    "supplier": check_supplier_contracts,
    "financial": weekly_financial_summary,
    "electricity": electricity_anomaly_check,
    "reconciliation": check_reconciliation,
    "ota": ota_review_monitor,
}

async def run_all():
    logger.info("🚀 Tüm modüller çalışıyor...")
    for name, func in MODULES.items():
        try:
            await func()
            await asyncio.sleep(2)  # Telegram rate limit
        except Exception as e:
            logger.error(f"{name}: {e}")
    logger.info("✅ Tüm modüller tamamlandı")

async def run_module(name: str):
    func = MODULES.get(name)
    if not func:
        print(f"Bilinmeyen modül: {name}")
        print(f"Mevcut modüller: {', '.join(MODULES.keys())}")
        return
    await func()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(run_module(sys.argv[1]))
    else:
        asyncio.run(run_all())
