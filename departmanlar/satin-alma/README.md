# Satın Alma & Stok — PO kayıtları, stok raporları

> Bu klasör `satin-alma` departmanı için olaylar, hesaplar ve envanter dosyalarını içerir.
> Telegram Topic: **#133** | Skill: `lato-satin-alma`

## Yapı

```
satin-alma/
├── olaylar/YYYY/AY/GG-konu.md      → acil alım, tedarikçi sorunu kayıtları
├── hesaplar/YYYY/AY/<konu>.md      → maliyet karşılaştırma, stok hesapları
└── envanter/
    └── satin-alinacaklar.md        → 📌 SATIN ALINACAKLAR LİSTESİ (aktif)
```

## Aktif Liste

**[`envanter/satin-alinacaklar.md`](envanter/satin-alinacaklar.md)** — teknik ekip + spec
zorunluluklarından derlenen alım listesi (öncelik, tahmini THB, tedarikçi adayı).

Süreç: teknik ekip ihtiyacı olay dosyasında işaretler → listeye satır eklenir →
2+ teklif → Leb onayı → sipariş → fatura foto Telegram #133'e (bot mutabakat özeti çıkarır) →
teslimatta envanter kartı açılır, satır kapatılır.

Dosya yapılış kuralları: [`../INPUT-REHBERI.md`](../INPUT-REHBERI.md)
