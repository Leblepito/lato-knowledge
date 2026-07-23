# Lato Departman Yapısı

6 departman, 7 otel, 819 oda — Phuket, Tayland.

## Departmanlar

| # | Departman | Telegram Topic | Skill | Sorumluluk |
|---|---|---|---|---|
| 1 | ⚡ Elektrik & Havuz | 130 | elektrik-danisman + havuz-pompa-motor | Pano, kablo, jeneratör, ATS, kompanzasyon, havuz filtrasyon, klorlama |
| 2 | 🔧 Teknik Bakım | 131 | lato-teknik-bakim | Tesisat, AC/klima, onarım, bina bakım |
| 3 | 🛎️ Operasyon | 132 | lato-operasyon | Resepsiyon + güvenlik, check-in/out, CCTV |
| 4 | 📦 Satın Alma & Stok | 133 | lato-satin-alma | Tedarik, envanter, vendor, maliyet |
| 5 | 🍽️ F&B | 134 | lato-fnb | Mutfak, restoran, bar, breakfast, HACCP |
| 6 | 💻 IT & Muhasebe | 135 | lato-it-muhasebe | WiFi, ağ, PMS, booking, fatura, bordro |

## Routing

Sorgu geldiğinde `lato-departman-router` skill'i doğru departmana yönlendirir.

## Klasör Yapısı

```
departmanlar/
├── INPUT-REHBERI.md    → 📥 input dosyası yapılış rehberi (BURADAN BAŞLA)
├── _sablonlar/         → olay / hesap / envanter şablonları + örnek
├── elektrik-havuz/     → olaylar, hesaplar, envanter
├── teknik-bakim/       → bakım planları, arıza kayıtları
├── operasyon/          → occupancy raporları, güvenlik logları
├── satin-alma/         → PO kayıtları, stok raporları, satin-alinacaklar.md
├── fnb/                → menü, HACCP logları, ekipman envanteri
└── it-muhasebe/        → ağ şemaları, mali raporlar
```

Input dosyası nasıl yazılır (özellikle teknik ekip): **[`INPUT-REHBERI.md`](INPUT-REHBERI.md)**
Aktif alım listesi: [`satin-alma/envanter/satin-alinacaklar.md`](satin-alma/envanter/satin-alinacaklar.md)

## Referans Repolar

- [karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) — skill yazım pattern'leri
- [superpowers](https://github.com/obra/superpowers) — skill yapısı, TDD, verification
