# 🤖 Otel Otomasyon Modülleri — Telegram Entegrasyonu

> Mevcut Telegram grubu (Phuket-Lato, 6+1 topic) üzerine inşa edilen otomasyon botları.
> Her modül bağımsız çalışır, `@Latotranslate_bot` (çeviri) gibi ayrı bot token'ları kullanır.

## Modüller

| # | Modül | Bot | Topic | Durum |
|---|---|---|---|---|
| 0 | **Çeviri** | @Latotranslate_bot | #146 🌐 | ✅ Aktif |
| 1 | **Günlük Bülten** | @LatoBrief_bot | #132 🛎️ | 🟡 Kod hazır |
| 2 | **TM30 + WP Alert** | @LatoBrief_bot | #130 ⚡ | 🟡 Kod hazır |
| 3 | **Fatura OCR** | @LatoBrief_bot | #133 📦 | 🟡 Kod hazır |
| 4 | **Rakip Fiyat** | @LatoBrief_bot | #133 📦 | 🔴 Planlandı |
| 5 | **Finansal Özet** | @LatoBrief_bot | #132 🛎️ | 🔴 Planlandı |

## Ortak Altyapı

Tüm modüller şu kaynakları kullanır:
- **HOTEL_DB**: 7 otel, aylık doluluk/ADR/gelir verileri
- **PERSONEL GOREV**: 19 personel, WP bitiş tarihleri, departmanlar
- **OPERASYON YONETIMI**: Bürokratik takvim, ceza bilgileri
- **Elektraweb API**: Brook için rezervasyon/doluluk verisi (ID: 101027)

## Entegrasyon Noktaları

```
Excel (HOTEL_DB)  ←→  PostgreSQL/JSON  ←→  Telegram Bot
                         ↑
                    Cron Jobs (Hermes)
                    ├── 08:00 → Günlük bülten
                    ├── Check-in event → TM30 alert
                    ├── WP -30/-15/-7 gün → Alert
                    └── Pazartesi 09:00 → Finansal özet
```
