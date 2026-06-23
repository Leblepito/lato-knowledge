# 🏨 Brook+6 Otel Yönetim Sistemi — Kapsamlı Analiz & Otomasyon Yol Haritası

> **Kaynak**: The Brook_6 Operasyon Görev ve Takip.xlsx (22 sheet, 7 otel, 819 oda)
> **Tarih**: 2026-06-23 | **Analiz**: Lato Agent

---

## 📊 Mevcut Sistem Analizi — 22 Sheet Özeti

### 1. Operasyonel Çekirdek

| Sheet | İçerik | Veri Durumu |
|---|---|---|
| **DASHBOARD** | 7 otel portföy KPI'sı: 819 oda, %54 doluluk, yıllık 350M THB gelir projeksiyonu | ✅ Canlı veri |
| **HOTEL_DB** | Otel bazlı aylık doluluk/ADR/gelir tablosu (7 otel × 12 ay) | ✅ Brook gerçek, diğerleri mock |
| **REZERVASYON** | Rezervasyon girişi, oda envanteri (31 oda, 4 tip), sezonluk fiyatlandırma | ⚠️ Boş — veri girişi bekliyor |
| **PERSONEL GOREV** | 19 personel, 9 departman, bordro (383K THB/ay), organizasyon şeması | ✅ Dolu — Brook özel |

### 2. Finansal Yönetim

| Sheet | İçerik | Kritik Bulgular |
|---|---|---|
| **FINANSAL** | Aylık P&L (Oca-Tem), mevsimsel performans, break-even ADR | ❌ May-Tem zarar (-183K ila -201K THB/ay) |
| **ACENTE ODEMELERI** | 9 acente (5 TA + 4 OTA), komisyon takibi | Sunmar Tour ödeme gecikmiş |
| **MUTABAKAT** | 3 otel banka ekstresi vs muhasebe karşılaştırma | ❗ Brook'ta banka 303K vs muhasebe 129K — %135 uyumsuzluk |
| **ISLETME GELIR-GIDER** | İşletme gelir-gider analizi | Boş — veri bekliyor |

### 3. Tedarik & Operasyon

| Sheet | İçerik | Kritik Bulgular |
|---|---|---|
| **TEDARIKCI YONETIMI** | 16 tedarikçi, ödeme takibi, fatura mutabakatı | ⚠️ 1 sözleşme süresi geçmiş |
| **OPERASYON YONETIMI** | İdari/ekonomik/güvenlik görevleri, bürokratik takvim | TM30, yangın, WP takibi aktif |
| **GUNLUK RAPOR & ANALIS** | Günlük acente performansı, kanal analizi | Şablon hazır |
| **FIYAT & PAZARLAMA** | 7 rakip otel fiyat izleme, dijital pazarlama takvimi | Haftalık 14 içerik planı, 11 kanal stratejisi |

### 4. Otomasyon & Denetim

| Sheet | İçerik | Kritik Bulgular |
|---|---|---|
| **OTOMASYON ANALIZI** | 4 aşamalı otomasyon yol haritası, skorlama | 16 otomasyon fırsatı tanımlanmış |
| **TEKNIK MIMARI** | LINE bot + OCR + AI sınıflandırma + n8n mimarisi | Tam teknik plan hazır, ~1,200 THB/ay |
| **YON_DENETIM_LOG** | Gizli fatura fark tespiti (>%1), sef onay takibi | Şablon hazır, veri yok |
| **VERI_GIRIS_LOG** | AI agent sessiz tutarsızlık tespiti | Şablon hazır, veri yok |

### 5. Altyapı

| Sheet | İçerik |
|---|---|
| **KULLANIM KILAVUZU** | 6 dilli (EN/TR/RU/TH/MY/VI) departman bazlı kullanım rehberi |
| **ADMIN PANEL** | Rol bazlı erişim matrisi (Super Admin, GM, Müdür, Şef, Personel) |
| **DIL PAKETLERI** | 6 dilli mesaj şablonları |
| **API AYARLARI** | Elektraweb PMS API config (ID: 101027), OTA kanal bağlantıları |
| **OTEL SECIM / OTELLER** | Otel seçici dropdown + liste |

---

## 🚨 Kritik Bulgular (Acil Aksiyon Gerektiren)

### 1. Mutabakat Uyumsuzluğu — BROOK
```
Banka ekstresi gider:  303,620 THB
Muhasebe kaydı:        129,290 THB
Fark:                  174,330 THB (%135 uyumsuzluk!)
```
**Sebep**: PEA elektriği bankadan 68,608 THB çekilmiş, muhasebe 9,290 THB kaydetmiş.
Maaş + servis charge tutarsız. Çamaşırhane ve temizlik muhasebede yok.

### 2. Düşük Sezon Zararı
```
Mayıs:    -183,350 THB/ay
Haziran:  -201,440 THB/ay
Temmuz:   -198,729 THB/ay
```
ADR break-even'ın altında (479 THB vs 684 THB break-even).

### 3. TM30 Ceza Riski
Her yabancı misafir için 24 saat içinde bildirim zorunlu. Ceza: 1,600 THB/ihlal.
**Otomasyon kritik** — manuel takip hataya açık.

---

## 🤖 Yeni Otomasyon Önerileri — Telegram'a Entegre Edilebilir

### A. Hemen Kurulabilir (Telegram bot olarak)

| # | Otomasyon | Açıklama | Telegram Entegrasyonu |
|---|---|---|---|
| 1 | **📅 Günlük Operasyon Bülteni** | Her sabah 08:00'de doluluk, check-in/out, gelir özeti | Cron job → Topic #132 |
| 2 | **🔔 TM30 Hatırlatma** | Yabancı misafir check-in → 24 saat içinde bildirim hatırlatması | Voice mesaj → otomatik task |
| 3 | **👷 Work Permit Expiry Alert** | WP bitişine 30/15/7 gün kala bildirim | Cron job → GM DM |
| 4 | **🔧 Bakım Talebi Bot** | Personel arıza bildirir → departmana yönlendir → takip | Topic bazlı task routing |
| 5 | **📸 Fatura OCR + Mutabakat** | Fatura fotoğrafı → Google Vision → tutar kontrolü | Fotoğraf → OCR → mutabakat |
| 6 | **💰 Acente Ödeme Hatırlatma** | Vadesi gelen acente ödemesi için bildirim | Cron job → Muhasebe topic |
| 7 | **📊 Haftalık Finansal Özet** | Her Pazartesi önceki hafta P&L özeti | Cron job → Yönetim topic |
| 8 | **🏷️ Rakip Fiyat İzleme** | Booking.com/Agoda rakip fiyat çekme → karşılaştırma | Web scraping → Fiyat topic |
| 9 | **⚡ Elektrik Faturası Anomali** | PEA faturası geçen aya göre +%20 ise uyarı | Cron job → Elektrik topic |
| 10 | **⭐ OTA Yorum İzleme** | Booking/Agoda yorumları çek → sentiment analizi | Cron job → Pazarlama topic |

### B. Kısa Vadede (1-2 ay)

| # | Otomasyon | Açıklama | Teknoloji |
|---|---|---|---|
| 11 | **🏨 Misafir WhatsApp Bot** | Check-in info, WiFi, oda servisi, şikayet — 6 dil | WhatsApp Business API |
| 12 | **📈 Dinamik Fiyat Motoru** | Doluluk + rakip + sezon → fiyat önerisi AI | GPT-4o + Elektraweb API |
| 13 | **🔄 OTA Senkronizasyon** | Tüm OTA kanallarında anlık fiyat/gün güncelleme | Elektraweb Channel Manager |
| 14 | **📋 Eğitim Takip Sistemi** | Personel eğitimleri, sertifika yenileme hatırlatma | Telegram task system |
| 15 | **🧾 Otomatik Vergi Hatırlatma** | VAT/SSO son gün bildirimleri | Cron → calendar sync |

### C. Orta Vadede (3-6 ay) — Mobile App Hedefi

| # | Otomasyon | Açıklama |
|---|---|---|
| 16 | **📱 Guest App** | QR check-in, dijital anahtar, oda servisi, spa rezervasyonu |
| 17 | **🏠 IoT Enerji Yönetimi** | Oda bazlı klima/ışık kontrolü, boş ota otomatik enerji tasarrufu |
| 18 | **🎯 CRM & Loyalty** | Misafir geçmişi, tercih takibi, tekrar rezervasyon kampanyaları |
| 19 | **🔮 Tahmine Dayalı Analitik** | Sezon projeksiyonu, gelir tahmini, personel ihtiyaç planlaması |
| 20 | **📝 AI Denetim Agent** | Excel'deki tutarsızlıkları otomatik tespit (VERI_GIRIS_LOG mantığı) |

---

## 📱 Mobile Application Roadmap (Android + iOS)

### Faz 1: Yönetim Dashboard (Month 1-2)
```
React Native / Flutter
├── Multi-hotel dashboard (7 otel)
├── Real-time KPI (doluluk, gelir, RevPAR)
├── Push notifications (TM30, WP, ödeme)
├── Fatura foto → OCR → mutabakat
└── Telegram bağlantısı (mevcut)
```

### Faz 2: Operasyon (Month 3-4)
```
├── Personel görev atama & takip
├── Bakım talebi (foto + açıklama)
├── Vardiya programı
├── Envanter yönetimi
└── Çok dilli çeviri (mevcut sistem entegre)
```

### Faz 3: Misafir Deneyimi (Month 5-6)
```
├── Self check-in (QR kod)
├── Oda servisi siparişi
├── Spa/restoran rezervasyonu
├── Çok dilli asistan (AI chatbot)
├── Yorum & geribildirim
└── Loyalty program
```

### Teknoloji Stack
```
Frontend:  React Native (Android + iOS tek kod tabanı)
Backend:   FastAPI (Python) — mevcut Telegram bot ile aynı
Database:  PostgreSQL (Railway/Supabase)
Auth:      Firebase Auth / Supabase Auth
Storage:   AWS S3 / Cloudflare R2
Push:      Firebase Cloud Messaging
Maps:      Google Maps SDK
Payment:   Stripe / Omise (TH)
```

---

## 🔗 Mevcut Sistem → Telegram Entegrasyon Matrisi

| Excel Sheet | Telegram Entegrasyonu | Status |
|---|---|---|
| PERSONEL GOREV | Topic bazlı görev atama + durum güncelleme | 🟡 Planlandı |
| OPERASYON YONETIMI | Cron job ile hatırlatmalar (TM30, WP, vergi) | 🟡 Planlandı |
| ACENTE ODEMELERI | Vade takibi → bildirim | 🟡 Planlandı |
| FINANSAL | Haftalık otomatik özet | 🟡 Planlandı |
| FIYAT & PAZARLAMA | Rakip fiyat izleme + pazarlama takvimi hatırlatma | 🟡 Planlandı |
| MUTABAKAT | Fatura OCR + tutar kontrolü | 🟡 Planlandı |
| TEDARIKCI YONETIMI | Sözleşme yenileme alarmı | 🟡 Planlandı |
| ÇEVİRİ (mevcut) | ✅ Aktif — TR ↔ TH ↔ EN | 🟢 Çalışıyor |
| DIL PAKETLERI | Çeviri botuna entegre | 🟢 Çalışıyor |

---

## 📐 Öncelik Matrisi

```
     YÜKSEK ETKİ
         │
    TM30  │  Rakip Fiyat
    Alert │  İzleme
    ──────┼──────
    WP    │  Dinamik
    Alert │  Fiyat AI
         │
     DÜŞÜK ──────── YÜKSEK
         ZORLUK
```

**Faz 1 (Bu hafta):**
1. Günlük operasyon bülteni (cron)
2. TM30 + WP hatırlatma
3. Fatura OCR mutabakat

**Faz 2 (Önümüzdeki hafta):**
4. Rakip fiyat izleme
5. Acente ödeme hatırlatma
6. Haftalık finansal özet
