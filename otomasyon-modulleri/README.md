# 🤖 Otel Otomasyon Motoru v2.1

> 10 modüllü gelişmiş otomasyon sistemi — Excel analizi sentezlenerek kuruldu.
> Cron jobs: Hermes scheduler üzerinden otomatik çalışır.
> **AI model**: sadece Claude Sonnet 5 — `claude` CLI + abonelik ile **ücretsiz**
> (ortak istemci: `../telegram-bot/claude_client.py`, fallback: Anthropic/OpenRouter API).
> Kurulum: [`../KURULUM.md`](../KURULUM.md)

## Modüller

| # | Modül | Cron | Topic | Açıklama |
|---|---|---|---|---|
| 1 | `briefing` | Her gün 08:00 | #132 | Günlük operasyon bülteni + AI strateji |
| 2 | `wp` | Her gün 09:00 | #132 | Work permit 30/15/7/0 gün uyarı |
| 3 | `tm30` | Her gün 09:00 | #132 | TM30 bildirim hatırlatma (24 saat) |
| 4 | `bureaucratic` | Her gün 09:00 | #133 | VAT/SSO/Bordro/PND50 deadline |
| 5 | `agency` | İsteğe bağlı | #133 | Acente ödeme takibi |
| 6 | `supplier` | İsteğe bağlı | #133 | Tedarikçi sözleşme süresi |
| 7 | `financial` | Pzt 10:00 | #132 | Haftalık P&L + anomali tespiti |
| 8 | `electricity` | Pzt 10:00 | #130 | Elektrik faturası +%20 uyarı |
| 9 | `reconciliation` | Pzt 10:00 | #133 | Banka vs muhasebe mutabakat |
| 10 | `ota` | İsteğe bağlı | #132 | OTA yorum sentiment analizi |
| 🏷️ | `competitor` | Pzt+Per 07:00 | #133 | Rakip fiyat izleme + AI öneri |

## Dosyalar
- `hotel_data.py` — Veri katmanı (7 otel, 19 personel, 9 acente, 16 tedarikçi)
- `automation_engine.py` — 10 modüllü ana motor
- `competitor_monitor.py` — Rakip fiyat izleme + dinamik fiyatlandırma
- `data/hotel_db.json` — Çalışan veritabanı (seed edilmiş)

## Çalıştırma
```bash
# Tek modül
python3 automation_engine.py briefing

# Tüm modüller
python3 automation_engine.py

# Rakip izleme
python3 competitor_monitor.py
```

## Cron Jobs (Hermes)
- `fd347c853747` — Günlük bülten (08:00)
- `ddf8f9475a85` — WP/TM30/Bürokratik (09:00)
- `246cade5111a` — Haftalık finansal (Pzt 10:00)
- `40de123981d8` — Rakip fiyat (Pzt+Per 07:00)
