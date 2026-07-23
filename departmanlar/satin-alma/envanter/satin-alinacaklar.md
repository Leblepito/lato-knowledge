# 📦 Satın Alınacaklar — Envanter Listesi

> Kaynak: `spec/phuket-elektrik-context.md` zorunlulukları + `analizler/brook-6-otel-sistem-analizi.md`
> + departman olay kayıtları. Fiyatlar **tahmini** (THB, VAT %7 hariç) — sipariş öncesi teklif alınır.
> Miktar bazı: pilot **Brook Pool Resort (31 oda)**; diğer oteller saha envanteri sonrası eklenir (TBD).
> Güncelleme kuralı: her olay dosyasında "Satın alma gerekli: evet" çıktığında buraya satır eklenir.

## A. Elektrik — Muson & Standart Zorunlulukları (spec gereği)

| # | Kalem | Spec | Adet | Tahmini THB | Öncelik | Tedarikçi adayı |
|---|---|---|---|---|---|---|
| 1 | SPD Tip 1 (ana pano) | IEC 61643, muson zorunlu | 1 | 8,000–15,000 | 🔴 KRİTİK | Electrical Plus Phuket |
| 2 | SPD Tip 2 (alt panolar) | muson zorunlu | TBD (pano sayısı saha) | 3,000–6,000/adet | 🔴 KRİTİK | Electrical Plus Phuket |
| 3 | Kaçak akım rölesi 30mA | havuz + ıslak hacim devreleri | TBD | 800–2,500/adet | 🔴 KRİTİK | Global House |
| 4 | IP55 dış mekan pano | dış mekan zorunlu | TBD | 2,500–8,000/adet | 🟠 YÜKSEK | Thai Watsadu |
| 5 | IP67 dış mekan buat + rakor seti | muson zorunlu | 20+ | ~100–300/adet | 🟠 YÜKSEK | Thai Watsadu |
| 6 | UV dayanımlı XLPE kablo (kesitler hesap sonrası) | dış mekan | TBD m | hesapla | 🟡 NORMAL | Electrical Plus Phuket |
| 7 | Topraklama çubuğu + iletken (≤5Ω hedef) | ölçüm sonrası | TBD | 5,000–20,000 | 🟠 YÜKSEK | Electrical Plus Phuket |
| 8 | Acil aydınlatma armatürü (1+ saat yedek) | yangın güvenlik | TBD | 900–2,000/adet | 🟠 YÜKSEK | Global House |

## B. Havuz (TS EN 60364-7-702 / TIS 1706)

| # | Kalem | Spec | Adet | Tahmini THB | Öncelik | Tedarikçi adayı |
|---|---|---|---|---|---|---|
| 9 | SELV 12V havuz aydınlatma trafo + armatür | Zone 0 zorunlu | TBD | 3,000–9,000/set | 🔴 KRİTİK | Pool Pro Thailand |
| 10 | Yedek havuz pompası ön filtre sepeti | 23.07 olay örneği | 2 | 500–1,500 | 🟡 NORMAL | Pool Pro Thailand |
| 11 | Havuz kimyasalları aylık stok (klor, pH-, alg önleyici) | rutin | aylık | ~8,200/ay (mevcut ort.) | 🟡 NORMAL | Pool Pro Thailand |
| 12 | Su test kiti (klor/pH/alkalinite) | günlük log | 2 | 1,500–3,000 | 🟠 YÜKSEK | Pool Pro Thailand |

## C. Ölçüm & Test Cihazları (teknik ekip)

| # | Kalem | Kullanım | Adet | Tahmini THB | Öncelik |
|---|---|---|---|---|---|
| 13 | Pens ampermetre (true RMS) | arıza teşhis | 2 | 2,500–6,000 | 🟠 YÜKSEK |
| 14 | İzolasyon test cihazı (250/500V megger) | kabul testi ≥0.5MΩ | 1 | 8,000–15,000 | 🟠 YÜKSEK |
| 15 | Topraklama direnci ölçer | ≤5Ω doğrulama | 1 | 10,000–25,000 | 🟡 NORMAL |
| 16 | RCD test cihazı (30mA, ≤30ms) | kabul testi | 1 | 6,000–12,000 | 🟡 NORMAL |
| 17 | Termal kamera (pano/busbar yıllık tarama) | koruyucu bakım | 1 | 15,000–40,000 | 🟡 NORMAL |

## D. Teknik Bakım Sarf (klima + tesisat)

| # | Kalem | Kullanım | Adet | Tahmini THB | Öncelik |
|---|---|---|---|---|---|
| 18 | R32 / R410A soğutucu gaz tüpü | klima gaz dolum | 1+1 | 3,000–6,000/tüp | 🟠 YÜKSEK |
| 19 | Klima filtre temizlik kimyasalı + fin tarağı | periyodik bakım | stok | 1,000–2,000 | 🟡 NORMAL |
| 20 | PPR boru + fitting acil onarım seti | su kaçağı | stok | 2,000–4,000 | 🟠 YÜKSEK |
| 21 | Marine grade (316) vida/kelepçe seti | plaj kenarı korozyon | stok | 1,500–3,000 | 🟡 NORMAL |
| 22 | Yedek kapı kilidi (elektronik/mekanik) | oda arızaları | 3 | 1,000–4,000/adet | 🟡 NORMAL |

## Süreç

1. Teknik ekip ihtiyacı olay dosyasında işaretler → bu listeye satır eklenir
   (veya ihtiyaç mesajı #133'e atılır — bot satır formatında öneri üretir)
2. Satın alma 2+ teklif alır (Global House / Thai Watsadu / Electrical Plus / Pool Pro)
3. Onay: Leb → sipariş → **fatura fotoğrafı Telegram #133'e** → bot (Sonnet 5)
   firma/tutar/tarih çıkarır, mutabakat özeti verir
4. Teslimatta envanter kartı açılır: `departmanlar/<departman>/envanter/<otel>-<ekipman>.md`
5. Satır bu listeden "✅ alındı (tarih, PO no)" notuyla kapatılır

> ⚠️ Adetleri kesinleştirmek için Brook saha envanteri gerekli — `oteller/brook-pool-resort.md`
> hâlâ TBD ağırlıklı. İlk saha ziyaretinde pano sayısı, dış mekan hat uzunlukları ve
> havuz ekipman etiketleri toplanmalı (bkz. `departmanlar/INPUT-REHBERI.md` §3).
