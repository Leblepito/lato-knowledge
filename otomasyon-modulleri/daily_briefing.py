#!/usr/bin/env python3
"""
Lato Otel Otomasyon — Günlük Bülten + TM30/WP Alert + Fatura OCR.

Bu modül Hermes cron job olarak veya bağımsız daemon olarak çalışır.
Excel'den okur (veya JSON cache'den), Telegram'a gönderir.

Kullanım:
  # Tek seferlik (cron)
  python3 daily_briefing.py

  # Daemon mode (event-driven)
  python3 daily_briefing.py --daemon
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("lato-briefing")

# ── Config ─────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TRANSLATE_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
GROUP_CHAT_ID = -1003776134843
TOPIC_OPS = 132       # 🛎️ Operasyon
TOPIC_TECH = 130      # ⚡ Elektrik & Havuz
TOPIC_PURCH = 133     # 📦 Satın Alma
TOPIC_GEN = 1         # Genel

# HOTEL_DB cache (Excel'den export edilmiş JSON)
DATA_PATH = Path(__file__).parent / "data" / "hotel_db.json"


# ── Data Layer ────────────────────────────────────────────────────
def load_hotel_data() -> dict:
    """Excel HOTEL_DB'den export edilmiş JSON'ı yükle."""
    if DATA_PATH.exists():
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"hotels": [], "staff": [], "operations": []}


# ── Telegram ──────────────────────────────────────────────────────
async def send_message(text: str, topic_id: int = TOPIC_OPS):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{API_BASE}/sendMessage", json={
            "chat_id": GROUP_CHAT_ID,
            "message_thread_id": topic_id,
            "text": text,
            "parse_mode": "Markdown",
        })
        return r.json()


# ── 1. Günlük Operasyon Bülteni ──────────────────────────────────
async def daily_briefing():
    """Her sabah 08:00 — doluluk, check-in/out, kritik görevler."""
    data = load_hotel_data()
    today = datetime.now().strftime("%d.%m.%Y")
    now_month = datetime.now().month

    # Sezon hesapla
    season_map = {11: "HIGH", 0: "HIGH", 1: "HIGH", 2: "HIGH",
                  3: "MID", 4: "LOW", 5: "LOW", 6: "LOW", 7: "LOW",
                  8: "LOW", 9: "MID", 10: "HIGH"}
    season = season_map.get(now_month, "MID")

    lines = [
        f"📋 **GÜNLÜK OPERASYON BÜLTENİ**",
        f"📅 {today} | Sezon: **{season}**",
        "",
        "🏨 **PORTFÖY ÖZETİ (7 Otel)**",
    ]

    total_rooms = 0
    total_occ = 0
    total_rev = 0

    for hotel in data.get("hotels", []):
        rooms = hotel.get("rooms", 0)
        occ = hotel.get("occupancy", 0)
        rev = hotel.get("revenue_today", 0)
        total_rooms += rooms
        total_occ += occ * rooms
        total_rev += rev
        flag = "🟢" if occ > 0.7 else ("🟡" if occ > 0.5 else "🔴")
        lines.append(f"  {flag} {hotel['name']}: {rooms} oda, %{occ*100:.0f} dolu")

    if total_rooms > 0:
        avg_occ = total_occ / total_rooms
        lines.append(f"")
        lines.append(f"📊 **Toplam**: {total_rooms} oda, %{avg_occ*100:.0f} ortalama doluluk")
        lines.append(f"💰 **Bugün tahmini gelir**: {total_rev:,.0f} THB")

    # Kritik görevler
    ops = data.get("operations", [])
    critical = [o for o in ops if o.get("priority") == "KRITIK" and o.get("status") != "Tamamlandi"]
    if critical:
        lines.append("")
        lines.append(f"⚠️ **Kritik Görevler ({len(critical)}):**")
        for op in critical[:5]:
            lines.append(f"  • {op['task']} — Son: {op.get('deadline', '?')}")

    # TM30 kontrolü
    lines.append("")
    lines.append("🛂 **TM30**: Bugün check-in yapan yabancı misafirler için 24 saat içinde bildirim yapın!")
    lines.append("   Ceza: 1,600 THB/ihlal")

    await send_message("\n".join(lines), TOPIC_OPS)
    logger.info("✅ Günlük bülten gönderildi")


# ── 2. Work Permit Expiry Check ──────────────────────────────────
async def check_work_permits():
    """Work permit bitiş tarihlerini kontrol et, yaklaşanlar için uyarı."""
    data = load_hotel_data()
    staff = data.get("staff", [])
    today = datetime.now().date()

    alerts = []
    for person in staff:
        wp_exp = person.get("wp_expiry")
        if not wp_exp:
            continue

        try:
            exp_date = datetime.strptime(wp_exp, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        days_left = (exp_date - today).days

        if days_left <= 0:
            alerts.append(("🔴 SÜRESİ DOLDU", person, days_left))
        elif days_left <= 7:
            alerts.append(("🟠 7 GÜN KALDI", person, days_left))
        elif days_left <= 15:
            alerts.append(("🟡 15 GÜN KALDI", person, days_left))
        elif days_left <= 30:
            alerts.append(("🔵 30 GÜN KALDI", person, days_left))

    if not alerts:
        return

    lines = ["👷 **WORK PERMIT UYARISI**", ""]
    for level, person, days in alerts:
        name = person.get("name", "?")
        dept = person.get("department", "?")
        hotel = person.get("hotel", "?")
        nationality = person.get("nationality", "?")
        lines.append(f"{level}: **{name}** ({nationality})")
        lines.append(f"  🏨 {hotel} | 🔧 {dept}")
        if days <= 0:
            lines.append(f"  ⚠️ {abs(days)} gün önce doldu! Ceza riski: 10,000+ THB")
        else:
            lines.append(f"  ⏳ {days} gün kaldı — yenileme başlatın")
        lines.append("")

    lines.append("📝 Yenileme için: Ministry of Labour, Phuket")
    await send_message("\n".join(lines), TOPIC_OPS)
    logger.info(f"✅ WP alert: {len(alerts)} personel")


# ── 3. Burokratik Hatırlatma (VAT/SSO/Lisans) ───────────────────
async def check_bureaucratic_deadlines():
    """VAT, SSO, lisans yenileme gibi yasal deadlines kontrol et."""
    today = datetime.now().date()
    day_of_month = today.day

    alerts = []

    # VAT PP30 — her ayın 15'i
    if day_of_month >= 10 and day_of_month <= 15:
        days = 15 - day_of_month
        alerts.append({
            "task": "VAT PP30 Beyannamesi",
            "deadline": f"{today.year}-{today.month:02d}-15",
            "days_left": days,
            "penalty": "2,000 THB + %1.5/ay gecikme faizi",
            "authority": "Revenue Department",
        })

    # SSO — her ayın 15'i
    if day_of_month >= 10 and day_of_month <= 15:
        days = 15 - day_of_month
        alerts.append({
            "task": "SSO (Sosyal Sigorta) Bildirimi",
            "deadline": f"{today.year}-{today.month:02d}-15",
            "days_left": days,
            "penalty": "5,000 THB/personel",
            "authority": "Social Security Office",
        })

    # Bordro — her ayın 25'i
    if day_of_month >= 20 and day_of_month <= 25:
        days = 25 - day_of_month
        alerts.append({
            "task": "Personel Bordro Hazırlığı",
            "deadline": f"{today.year}-{today.month:02d}-25",
            "days_left": days,
            "penalty": "Personel maş gecikmesi",
            "authority": "Otel Yönetimi",
        })

    if not alerts:
        return

    lines = ["🏛️ **BÜROKRATİK HATIRLATMA**", ""]
    for a in alerts:
        urgency = "🔴" if a["days_left"] <= 1 else ("🟠" if a["days_left"] <= 3 else "🟡")
        lines.append(f"{urgency} **{a['task']}**")
        lines.append(f"  ⏳ {a['days_left']} gün kaldı (son: {a['deadline']})")
        lines.append(f"  ⚠️ Ceza: {a['penalty']}")
        lines.append(f"  🏛️ {a['authority']}")
        lines.append("")

    await send_message("\n".join(lines), TOPIC_OPS)


# ── 4. Acente Ödeme Hatırlatma ───────────────────────────────────
async def check_agency_payments():
    """Acente ödeme vadelerini kontrol et."""
    data = load_hotel_data()
    agencies = data.get("agencies", [])
    today = datetime.now().date()

    overdue = []
    for agency in agencies:
        status = agency.get("payment_status", "")
        if status in ("Gecikti", "Beklemede"):
            overdue.append(agency)

    if not overdue:
        return

    lines = ["💰 **ACENTE ÖDEME DURUMU**", ""]
    for a in overdue:
        flag = "🔴" if a.get("payment_status") == "Gecikti" else "🟡"
        lines.append(f"{flag} **{a['name']}** ({a.get('type', '?')})")
        lines.append(f"  Komisyon: %{a.get('commission_pct', 0)*100:.0f}")
        lines.append(f"  Tutar: ~{a.get('commission_thb', 0):,.0f} THB")
        lines.append(f"  Durum: {a['payment_status']}")
        lines.append("")

    await send_message("\n".join(lines), TOPIC_OPS)


# ── Main ──────────────────────────────────────────────────────────
async def run_all():
    """Tüm kontrolleri çalıştır."""
    logger.info("🚀 Otel otomasyon kontrolü başlıyor...")
    await daily_briefing()
    await check_work_permits()
    await check_bureaucratic_deadlines()
    await check_agency_payments()
    logger.info("✅ Tüm kontroller tamamlandı")


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        # TODO: event-driven daemon mode
        asyncio.run(run_all())
    else:
        asyncio.run(run_all())
