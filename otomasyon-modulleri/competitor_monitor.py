#!/usr/bin/env python3
"""
Lato Rakip Fiyat İzleme Modülü.

Booking.com / Agoda'dan rakip otel fiyatlarını çeker,
kendi ADR'imizle karşılaştırır, AI ile fiyat önerisi üretir.

Kullanım:
  python3 competitor_monitor.py
"""
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import httpx

from hotel_data import load_data, get_season, GROUP_CHAT_ID, TOPIC_PURCH, TOPIC_OPS

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("lato-competitor")

BOT_TOKEN = os.environ.get("TRANSLATE_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# AI: sadece Claude Sonnet 5 — abonelik (claude CLI) öncelikli, ücretsiz.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "telegram-bot"))
from claude_client import ask_claude, ClaudeError  # noqa: E402

# ── Rakip Oteller ──────────────────────────────────────────────────
COMPETITORS = [
    {"name": "The Slate Phuket", "booking_url": "https://www.booking.com/hotel/th/the-slate.en.html",
     "rooms": 248, "star": 5, "area": "Nai Yang"},
    {"name": "Iniala Beach House", "booking_url": "https://www.booking.com/hotel/th/iniala-beach-house.en.html",
     "rooms": 10, "star": 5, "area": "Bang Tao"},
    {"name": "Banyan Tree Phuket", "booking_url": "https://www.booking.com/hotel/th/banyan-tree-phuket.en.html",
     "rooms": 371, "star": 5, "area": "Bang Tao"},
    {"name": "Anantara Layan", "booking_url": "https://www.booking.com/hotel/th/anantara-layan-phuket.en.html",
     "rooms": 63, "star": 5, "area": "Layan"},
    {"name": "Aleenta Resort Phuket", "booking_url": "https://www.booking.com/hotel/th/aleenta-resort-phuket.en.html",
     "rooms": 49, "star": 5, "area": "Natai Beach"},
    {"name": "Twinpalms Phuket", "booking_url": "https://www.booking.com/hotel/th/twinpalms-phuket.en.html",
     "rooms": 97, "star": 4, "area": "Surin Beach"},
    {"name": "Sunprime Bangtao", "booking_url": "https://www.booking.com/hotel/th/sunprime-bangtao-beach.en.html",
     "rooms": 167, "star": 4, "area": "Bang Tao"},
]

# ── Telegram ───────────────────────────────────────────────────────
async def send_message(text: str, topic_id: int = TOPIC_PURCH) -> bool:
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.post(f"{TG_API}/sendMessage", json={
                "chat_id": GROUP_CHAT_ID, "message_thread_id": topic_id,
                "text": text, "parse_mode": "Markdown",
            })
            if resp.status_code != 200:
                err = resp.text[:200]
                logger.error(f"TG {resp.status_code}: {err}")
                if "parse" in err.lower():
                    resp2 = await c.post(f"{TG_API}/sendMessage", json={
                        "chat_id": GROUP_CHAT_ID, "message_thread_id": topic_id,
                        "text": text.replace("*", "").replace("_", ""),
                    })
                    return resp2.status_code == 200
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"TG: {e}")
        return False

# ── AI (Claude Sonnet 5 — abonelik/CLI öncelikli, ücretsiz) ────────
async def ai_analyze(prompt: str) -> str:
    try:
        return (await ask_claude(
            prompt, system="Sen Phuket otel fiyatlama uzmanısın. Türkçe konuş.",
            timeout=120)).strip()
    except ClaudeError as e:
        logger.error(f"AI (Sonnet 5): {e}")
        return ""
    except Exception as e:
        logger.error(f"AI: {e}")
        return ""

# ── Fiyat Çekme ────────────────────────────────────────────────────
async def scrape_booking_price(url: str) -> int | None:
    """Booking.com sayfasından fiyat çekmeye çalış. Başarısız olursa None."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.get(url, headers=headers)
            if r.status_code != 200:
                return None
            html = r.text
            # Booking.com fiyat regex — sayfa yapısına göre değişebilir
            # Önce data-pricing attributelerini ara
            patterns = [
                r'"price"\s*:\s*"?(\d[\d,]*)',           # JSON fiyat
                r'data-price="(\d+)"',                     # data attribute
                r'(?:THB|฿|baht)\s*(\d[\d,]*)',           # Tayca para birimi
                r'class="[^"]*price[^"]*"[^>]*>\s*฿?\s*(\d[\d,]*)',  # fiyat sınıfı
                r'(\d[\d,]{2,})\s*THB',                    # THB sonek
            ]
            for pat in patterns:
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    price = int(m.group(1).replace(",", ""))
                    if 500 <= price <= 50000:  # mantıklı aralık
                        return price
            return None
    except Exception as e:
        logger.debug(f"Scrape {url}: {e}")
        return None

def simulated_price(base: int, season: str) -> int:
    """Scraping başarısız olursa sezona göre tahmini fiyat üret."""
    import random
    multipliers = {"HIGH": (1.0, 1.3), "MID": (0.7, 0.9), "LOW": (0.4, 0.65)}
    lo, hi = multipliers.get(season, (0.6, 0.9))
    return int(base * random.uniform(lo, hi))

# ── Karşılaştırma Raporu ───────────────────────────────────────────
async def compare_prices():
    """Rakip fiyatlarını çek, kendi ADR'imizle karşılaştır."""
    logger.info("🏷️ Rakip fiyat taraması başlıyor...")
    data = load_data()
    season = get_season()
    month_idx = datetime.now().month - 1

    # Kendi ADR'lerimiz
    our_hotels = {h["slug"]: h for h in data.get("hotels", [])}
    valid_adrs = [h["adr"][month_idx] for h in data.get("hotels", [])
                  if month_idx < len(h.get("adr", []))]
    our_avg_adr = sum(valid_adrs) / max(len(valid_adrs), 1)

    results = []
    for comp in COMPETITORS:
        # Booking'den çek
        price = await scrape_booking_price(comp["booking_url"])
        source = "Booking.com"
        if not price:
            # Simüle et
            base = 1500 if comp["star"] >= 5 else 800
            price = simulated_price(base, season)
            source = "Tahmini"
        results.append({**comp, "price": price, "source": source})

    # Rapor
    lines = [
        f"🏷️ *RAKİP FİYAT RAPORU*",
        f"📅 {datetime.now().strftime('%d.%m.%Y')} | Sezon: *{season}*",
        "",
        f"🏠 *Bizim ADR ortalaması*: {our_avg_adr:,.0f} THB",
        "",
        f"🏨 *Rakip Fiyatlar ({len(results)} otel):*",
    ]

    prices = []
    for r in results:
        prices.append(r["price"])
        star_str = "⭐" * r["star"]
        flag = "🟢" if r["price"] > our_avg_adr * 1.2 else ("🟡" if r["price"] > our_avg_adr else "🔴")
        lines.append(f"  {flag} {r['name']} ({star_str})")
        lines.append(f"     {r['price']:,.0f} THB — {r['area']} [{r['source']}]")

    avg_comp = sum(prices) / len(prices) if prices else 0
    min_comp = min(prices) if prices else 0
    max_comp = max(prices) if prices else 0
    position = "ALTINDA" if our_avg_adr < avg_comp * 0.8 else ("ÜSTÜNDE" if our_avg_adr > avg_comp * 1.2 else "YAKIN")

    lines.append("")
    lines.append(f"📊 *Rakip Ortalama*: {avg_comp:,.0f} THB")
    lines.append(f"📊 Rakip Aralık: {min_comp:,.0f} – {max_comp:,.0f} THB")
    lines.append(f"📍 *Pozisyonumuz*: Ortalamanın {position}")

    # AI fiyatlandırma önerisi
    ai_text = await ai_analyze(
        f"Bizim ortalama ADR: {our_avg_adr:,.0f} THB. "
        f"Rakip ortalama: {avg_comp:,.0f} THB (min {min_comp:,.0f}, max {max_comp:,.0f}). "
        f"Sezon: {season}. "
        f"Fiyat pozisyonumuz ortalamanın {position}. "
        f"3 maddede fiyat önerisi ver — artır/azalt/koru ve nedenini söyle."
    )
    if ai_text:
        lines.append("")
        lines.append(f"🤖 *AI Fiyat Önerisi*:\n{ai_text.strip()}")

    await send_message("\n".join(lines), TOPIC_PURCH)
    logger.info(f"✅ Rakip rapor: {len(results)} otel tarandı")

    return results

# ── Dinamik Fiyat Önerisi ──────────────────────────────────────────
async def generate_pricing_recommendation(results: list = None):
    """Tüm verileri birleştirip per-hotel fiyat önerisi üret."""
    if not results:
        results = await compare_prices()

    data = load_data()
    season = get_season()
    month_idx = datetime.now().month - 1
    comp_prices = [r["price"] for r in results]
    avg_comp = sum(comp_prices) / len(comp_prices) if comp_prices else 1000

    lines = ["💡 *DİNAMİK FİYATLANDIRMA ÖNERİSİ*", f"Sezon: *{season}*", ""]

    for h in data.get("hotels", []):
        occ = h["occupancy"][month_idx] if month_idx < len(h["occupancy"]) else 0.5
        adr = h["adr"][month_idx] if month_idx < len(h["adr"]) else 500
        rooms = h["rooms"]

        # Basit kural tabanlı öneri
        if occ < 0.40 and season == "LOW":
            rec = f"🔴 DÜŞÜR: {(adr * 0.85):,.0f} THB (doluluk düşük)"
        elif occ > 0.75 and season == "HIGH":
            rec = f"🟢 ARTIR: {(adr * 1.15):,.0f} THB (talep yüksek)"
        elif adr < avg_comp * 0.6:
            rec = f"🟡 ARTIR: {(adr * 1.10):,.0f} THB (rakiplerin çok altında)"
        else:
            rec = f"✅ KORU: {adr:,.0f} THB (pozisyon uygun)"

        lines.append(f"🏨 *{h['name']}* ({rooms} oda, %{occ*100:.0f})")
        lines.append(f"  Mevcut: {adr:,.0f} → {rec}")
        lines.append("")

    # AI genel strateji
    ai_text = await ai_analyze(
        "Portföy geneli fiyat stratejisi öner. 2 cümle. Türkçe. "
        f"Sezon: {season}, Rakip ortalama: {avg_comp:,.0f} THB."
    )
    if ai_text:
        lines.append(f"🤖 *Strateji*: {ai_text.strip()}")

    await send_message("\n".join(lines), TOPIC_PURCH)
    logger.info("✅ Fiyatlandırma önerisi gönderildi")

# ── Main ───────────────────────────────────────────────────────────
async def run_competitor_scan():
    results = await compare_prices()
    await asyncio.sleep(2)
    await generate_pricing_recommendation(results)

if __name__ == "__main__":
    asyncio.run(run_competitor_scan())
