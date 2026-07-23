# Envanter: TBD — Booster Pompa Kontrol Panosu #01

> Yol: `departmanlar/elektrik-havuz/envanter/tbd-booster-pompa-kontrol-panosu-01.md`
> Kaynak: foto `335-foto.jpg` (Booster pump control şeması, çizen: ACME CO., LTD)

| Alan | Değer | Kaynak |
|---|---|---|
| **Otel** | TBD — saha doğrulaması gerekli | — |
| **Konum** | TBD — muhtemelen havuz/booster pompa makine dairesi | saha |
| **Ekipman** | Booster pompa kontrol panosu (3 pompa motoru kontrolü) | foto/şema |
| **Marka / Model** | Panel builder: ACME CO., LTD — pompa motor markası TBD | etiket/şema |
| **Seri No** | TBD | etiket |
| **Güç** | 3× 3 kW (motor M1/M2/M3), toplam ~9 kW | şema |
| **Voltaj / Faz** | 380/220V, 3P4W, 50Hz | şema |
| **Akım** | Motor başına 7.15A (3φ); Ana kesici MCCB 3P 50AT/60AF (NF63-CV) | şema |
| **Alt kesiciler** | CB1/CB2/CB3: 3P 15AT/30AF (NF30-CS) — her motor için | şema |
| **Kontaktör / Termik röle** | MC1/MC2/MC3 (S-11 serisi) + TH-T18 termik aşırı yük röle (7-11A ayar aralığı) | şema |
| **Ölçüm cihazları** | Ampermetre 30/5A, Voltmetre 0-500V | şema |
| **Uzaktan kontrol terminalleri** | Remote P1/P2/P3 D/L, Remote Breaker Trip, Remote Low Level, Common | şema |
| **IP Sınıfı** | TBD (dış mekan min IP55, havuz bölgesi bkz. spec) | etiket — saha kontrolü gerekli |
| **Üretim Yılı / Yaş** | TBD | etiket |
| **Son Bakım** | — (yeni kurulum) | — |
| **Sonraki Bakım** | Kurulum sonrası 6 ay | plan |
| **Durum** | Kurulum planlanıyor | saha (Leb, 2026-07-24) |
| **Sorumlu** | Leb | Telegram bildirimi |

## Phuket Uygunluk Kontrolü (spec/phuket-elektrik-context.md)
- [ ] Dış mekan → IP55+ | Havuz Zone 1 → IPX4 + SELV + 30mA RCD — TBD, şemada IP sınıfı belirtilmemiş
- [ ] Plaj kenarı otel → marine grade (316 paslanmaz / epoksi) — TBD, otel/lokasyon bilinmiyor
- [ ] Muson → SPD koruması var mı, buat IP67 mü — **EKSİK**: şemada SPD (Tip 1/Tip 2) görünmüyor, eklenmesi önerilir
- [ ] Kablolar UV dayanımlı mı (XLPE/PE) — TBD, şemada kablo tipi belirtilmemiş
- [ ] 30mA kaçak akım rölesi besleme hattında — TBD, şemada net görünmüyor, doğrulanmalı
- [ ] Topraklama direnci ≤5Ω — kurulum sonrası ölçülüp kaydedilmeli (E terminali mevcut)

## Notlar & Fotoğraflar
`335-foto.jpg` — Booster pump control panosu tek hat şeması (ACME CO., LTD), sayfa 1/2 görüldü (2. sayfa kontrol devresi/kumanda şeması kesik, tam görünmüyor).

Eksik bilgiler saha doğrulaması ile tamamlanmalı: otel adı, kurulum konumu, IP sınıfı, SPD/RCD varlığı, marine grade ihtiyacı.