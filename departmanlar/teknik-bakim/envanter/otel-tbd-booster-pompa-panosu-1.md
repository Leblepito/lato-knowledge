# Envanter: TBD — saha doğrulaması gerekli — Booster Pompa Kontrol Panosu #1

> Yol: `departmanlar/teknik-bakim/envanter/otel-tbd-booster-pompa-panosu-1.md`
> Teknik ekip inputu: şema fotoğrafı (332-foto.jpg) + saha doğrulaması ile bu kartın tamamlanması gerekiyor.

| Alan | Değer | Kaynak |
|---|---|---|
| **Otel** | TBD — saha doğrulaması gerekli | — |
| **Konum** | TBD — saha doğrulaması gerekli (muhtemel: havuz makine dairesi / pompa odası) | saha |
| **Ekipman** | Booster pompa kontrol panosu (3 pompalı) | 332-foto.jpg |
| **Marka / Model** | ACME CO., LTD / model no belirtilmemiş — TBD | şema |
| **Seri No** | TBD | etiket (kurulum sonrası) |
| **Güç** | 3 x 3 kW motor (M1, M2, M3) — toplam 9 kW | şema (332-foto.jpg) |
| **Voltaj / Faz** | 380V/220V, 3 faz 4 tel (3PH 4W) | şema |
| **Akım** | Motor nominal: 7.15A x3 | Ana kesici: MCCB 3P 50AT/60AF | Motor koruma: CB1-CB3 3P 15AT/30AF (NF30-CS) | şema |
| **IP Sınıfı** | TBD (dış mekan min IP55, havuz bölgesi bkz. spec) | saha |
| **Üretim Yılı / Yaş** | TBD | etiket |
| **Son Bakım** | — (yeni kurulum) | — |
| **Sonraki Bakım** | TBD | plan |
| **Durum** | Kurulum aşamasında | saha bildirimi (Leb, 2026-07-24) |
| **Sorumlu** | Leb | Telegram bildirimi |

## Şema Detayları (332-foto.jpg)
- Kontaktörler: KM1, KM2, KM3
- Termik aşırı yük röleleri: TH-71B (S-112E)
- Ampermetre: 30V/5A (CT üzerinden)
- Voltmetre: 0-500V
- Uzaktan kontrol terminalleri: Remote P1 D/L, Remote P2 D/L, Remote P3 D/L, Remote Breaker Trip, Remote Low Level, Common

## Phuket Uygunluk Kontrolü (spec/phuket-elektrik-context.md)
- [ ] Dış mekan → IP55+ | Havuz Zone 1 → IPX4 + SELV + 30mA RCD — TBD, konum netleşmeden değerlendirilemez
- [ ] Plaj kenarı otel → marine grade (316 paslanmaz / epoksi) — TBD, otel netleşmeden değerlendirilemez
- [ ] Muson → SPD koruması var mı, buat IP67 mü — TBD, saha kurulumunda kontrol edilmeli
- [ ] Kablolar UV dayanımlı mı (XLPE/PE) — TBD, dış mekan kablo güzergahı varsa gerekli
- [ ] Kablo kesiti hesabı: 7.15A x3 motor yükü, 40°C ortam düzeltmesiyle — TBD, hesaplar/ klasörüne ayrı hesap dosyası açılmalı

## Notlar & Fotoğraflar
- 332-foto.jpg: Booster pump control panosu tek hat şeması (ACME CO., LTD)
- Otel, konum, seri no ve IP sınıfı bilgileri kurulum sonrası saha doğrulaması ile tamamlanacak
