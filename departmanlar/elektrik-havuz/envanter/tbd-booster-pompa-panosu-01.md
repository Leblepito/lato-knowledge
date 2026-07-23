# Envanter: TBD — Booster Pompa Kontrol Panosu #01

> Yol: `departmanlar/elektrik-havuz/envanter/tbd-booster-pompa-panosu-01.md`
> Kaynak: şema fotoğrafı `339-foto.jpg` (Booster pump control panel, ACME CO., LTD)

| Alan | Değer | Kaynak |
|---|---|---|
| **Otel** | TBD — saha doğrulaması gerekli | — |
| **Konum** | TBD — muhtemelen havuz makine dairesi, teyit gerekli | saha |
| **Ekipman** | Booster pompa kontrol panosu (3 pompa hattı) | şema |
| **Marka / Model** | ACME CO., LTD (panel imalatçısı) / motor markası TBD | şema/etiket |
| **Seri No** | TBD | etiket |
| **Güç** | 3 × 3kW (toplam 9kW), motor başına 7.15A | şema |
| **Voltaj / Faz** | 380/220V, 3 faz 4 tel (3PH 4W) | şema |
| **Akım** | Motor başına 7.15A; ana kesici MCCB 50A/60AF 3P | şema |
| **IP Sınıfı** | TBD (şemada belirtilmemiş — dış mekan min IP55, havuz bölgesi ise spec'e bkz.) | TBD |
| **Üretim Yılı / Yaş** | TBD | etiket |
| **Son Bakım** | — (yeni kurulum) | — |
| **Sonraki Bakım** | TBD | plan |
| **Durum** | Kurulum aşamasında | saha |
| **Sorumlu** | Leb | Telegram |

## Şema Detayları (kaynak: 339-foto.jpg)
- Ana kesici: MCCB 50AT / 60AF, 3P
- Motor hattı başına: MCB 15AT/30AF 3P (NF30-CS) + kontaktör (MC1/MC2/MC3) + termal aşırı yük rölesi (TH-T18, ayar aralığı ~7.15A)
- Ölçüm: Ampermetre 0-30/5A, Voltmetre 0-500V
- Uzaktan kontrol terminalleri: Remote P1/P2/P3 D/L, Remote Breaker Trip, Remote Low Level, Common
- Topraklama (E) hattı şemada mevcut, R/S/T/N/E dağıtım

## Phuket Uygunluk Kontrolü (spec/phuket-elektrik-context.md)
- [ ] Dış mekan → IP55+ | Havuz Zone 1 → IPX4 + SELV + 30mA RCD — **panel konumu TBD, teyit gerekli**
- [ ] Plaj kenarı otel → marine grade (316 paslanmaz / epoksi) — **otel bilinmiyor, TBD**
- [x] Muson → SPD koruması var mı → **ŞEMADA GÖRÜNMÜYOR, eksik olabilir, saha/panel imalatçısı ile teyit edilmeli**
- [x] 30mA kaçak akım rölesi (RCD) → **ŞEMADA GÖRÜNMÜYOR — havuz pompa devresiyse TIS 1706/IEC 60364-7-702 gereği zorunlu, kurulum öncesi eklenmeli**
- [ ] Topraklama direnci ≤5Ω → kurulum sonrası ölçülüp kayıt edilmeli
- [ ] Kablolar UV dayanımlı mı (XLPE/PE) → TBD, saha kablo spesifikasyonu şemada yok

## Notlar & Fotoğraflar
339-foto.jpg (şema, sayfa 1) — TBD: panel genel görünüm ve etiket fotoğrafı kurulum sonrası eklenmeli.

## Önerilen Satın Alma (satin-alinacaklar.md formatı)
| Malzeme | Miktar | Sebep | Öncelik |
|---|---|---|---|
| 30mA RCD, 3P, uygun akım değeri | 1 adet | Havuz pompa devresi zorunlu koruma (TIS 1706) | YUKSEK |
| SPD Type 2, 3P | 1 adet | Muson/yıldırım koruması, şemada eksik | YUKSEK |
