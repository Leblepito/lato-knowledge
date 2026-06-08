# Phuket Elektrik Context — Tüm 7 Otel İçin Geçerli

> Referans dokümanı. Yeni hesap/spec/olay oluştururken buradan kopyala-yapıştır yap.

## 🌐 Şebeke

- **Voltaj**: 220V / 50Hz (Türkiye 230V / 50Hz — yakın ama cihaz uyumu kontrol)
- **Faz**: Tek faz (konut) / Üç faz (ticari — oteller için tipik)
- **Şebeke operatörü**: PEA (Provincial Electricity Authority) — Türkiye TEDAŞ karşılığı
- **Bağlantı tipi**: Direk AG (çoğu Phuket otel) veya ring (büyük resortlar)

## 📐 Standartlar

### Tayland
- **TIS** (Thai Industrial Standards)
- **TIS 11** — Elektrik tesisat ana standard
- **TIS 4-2553** — Elektrik tesisat yönetmeliği
- **TIS 1706** — Havuz elektrik standardı (TS EN 60364-7-702 ile uyumlu)

### Uluslararası (Türkiye ile uyumlu)
- **IEC 60364** ailesi — Tesisat
- **IEC 60364-7-702** — Havuz ve benzeri yerler
- **IEC 60909** — Kısa devre hesapları
- **TS EN 60364** — Türkiye karşılığı

## 🌡️ İklim Etkileri (KRİTİK)

### Sıcaklık
- 25-35°C yıl boyu
- Kablo kesiti hesabında **ortam 40°C+** varsayılmalı
- PVC kablolar için düzeltme katsayısı uygula

### Nem
- %70-90 sürekli
- **IP55+** tüm dış mekan panoları
- **IP44+** iç mekan nemli bölgeler (havuz machine room, banyo)

### Tuzlu Hava (Plaj Kenarı)
- Deniz kenarında korozyon çok yüksek
- **Marine grade** (316 paslanmaz, epoksi kaplı) şart
- **Plaj kenarı oteller**: In On The Beach, Case Del Sol, Brook Pool (?)
- **İç bölge**: Trend Kamala, Phulin, Adema Karon (daha az kritik)
- The Natural Resort: lokasyona bağlı

### Muson (Mayıs - Ekim)
- Yoğun yağış + sık yıldırım
- **SPD Tip 1** (ana giriş) + **Tip 2** (alt panolar) **zorunlu**
- Topraklama direnci ≤ **5Ω** hedef, ≤ 10Ω kabul edilebilir
- Drenaj + su birikintisi kontrolü kritik
- Dış mekan buat/bağlantı **IP67+**

### UV
- Tropikal güneş → dış mekan kablolar **UV dayanımlı** (XLPE, PE, vs.)

## 🏊 Havuz Elektrik (Phuket)

- TS EN 60364-7-702 + TIS 1706
- **SELV (12V/24V)** havuz içi aydınlatma zorunlu
- **30 mA kaçak akım rölesi** havuz devrelerinde
- **Zone 1/2/3** IP kontrolü:
  - Zone 0 (havuz içi): SELV only, IPX8
  - Zone 1 (0-2m çevre): IPX4 min, SELV + 30mA
  - Zone 2 (2-5m çevre): IPX2 min
  - Zone 3 (>5m): standart
- **Eşpotansiyel kuşak** tüm metal parçalar

## 🔥 Yangın Güvenliği

- Sprinkler + alarm sistemleri
- Acil aydınlatma (1+ saat yedek)
- Kaçış yolu işaretleri
- Yangın pompa devresi ayrı koruma

## 📋 Kabul Testleri (Tipik)

- **Topraklama direnci** ≤ 5Ω (yıldırım için ≤ 10Ω)
- **İzolasyon direnci** ≥ 0.5MΩ (250V ile)
- **Kaçak akım rölesi** 30mA, açma süresi ≤ 30ms
- **Kısa devre** hesap doğrulaması
- **Yük dağılımı** üç faz dengeleme
- **Termal görüntüleme** (panel, busbar) — yıllık

## 🔗 İlgili Dokümanlar

- Türkiye karşılığı: TEDAŞ, TS EN standartları
- Havuz: `havuz-pompa-motor` skill (lato profili)
- Genel elektrik: `elektrik-danisman` skill (lato profili)
