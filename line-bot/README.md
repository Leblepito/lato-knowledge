# 📱 Lato LINE Bot — ⚠️ DEPRECATED (2026-07-23)

> **Bu köprü devre dışı.** Karar: her şey Telegram içinde çalışacak.
> Yeni sistem: [`../telegram-bot/`](../telegram-bot/) — personel input dosyasını
> doğrudan departman topic'ine atar, Sonnet 5 departmana göre çıktı üretir.
> Aşağıdaki dokümantasyon arşiv amaçlı tutulmaktadır — **deploy etmeyin**.

---

> Tayland'da personel LINE kullanır. Bu bot LINE mesajlarını AI ile sınıflandırır,
> Telegram'a aktarır ve departmanlara yönlendirir.

## Mimari

```
Tayland Personel (LINE App)
        │
        ▼
   LINE Messaging API (Webhook)
        │
        ▼
  ┌──────────────────────────────────┐
  │   lato-line-bot (Port 8089)      │
  │                                  │
  │  1. Mesaj al (text/foto/voice)   │
  │  2. AI sınıflandır               │
  │     (Claude Sonnet 5, OpenRouter)│
  │     - mesaj tipi / departman     │
  │     - öncelik / dil + çeviri     │
  │  3. Foto → OCR (Gemini)          │
  │  4. Telegram'e aktar             │
  │  5. LINE'a onay mesajı           │
  └──────────────────────────────────┘
        │
        ▼
  Telegram Phuket-Lato Grubu
  ├── #130 ⚡ Elektrik & Havuz (pano/pompa/jeneratör)
  ├── #131 🔧 Teknik Bakım (klima/tesisat/onarım)
  ├── #132 🛎️ Operasyon (resepsiyon/HK/güvenlik)
  ├── #133 📦 Satın Alma (fatura/ödemeler)
  ├── #134 🍽️ F&B (mutfak)
  └── #135 💻 IT & Muhasebe (WiFi/PMS)
```

## Özellikler

### Mesaj Tipleri
| Tip | LINE Input | AI Analiz | Telegram Output |
|---|---|---|---|
| **Text** | "Havuz pompası bozuk" | GOREV / TEKNIK / KRITIK | #130'a mesaj |
| **Photo (fatura)** | Fatura fotoğrafı | OCR → tutar/firma | #133'e fotoğraf + tutar |
| **Voice** | Sesli mesaj | (Whisper'a yönlendirilecek) | Voice olarak #1'e |

### AI Sınıflandırma Çıktısı
```json
{
  "mesaj_tipi": "GOREV",
  "kaynak_dil": "TR",
  "oncelik": "KRITIK",
  "departman": "TEKNIK",
  "ozet_tr": "Havuz pompası arızalı",
  "ozet_th": "ปั๊มน้ำสระว่ายน้ำเสีย",
  "ozet_en": "Pool pump is broken",
  "eylem": "Havuz pompa acil müdahale"
}
```

### Departman Yönlendirme
| LINE Mesaj İçeriği | Departman | Telegram Topic |
|---|---|---|
| Elektrik, pano, havuz, pompa, jeneratör | ELEKTRIK | #130 |
| Klima/AC, tesisat, su kaçağı, onarım | TEKNIK | #131 |
| Oda, temizlik, çarşaf, havlu | HK | #132 |
| Misafir, check-in, rezervasyon | ON_BURO | #132 |
| Fatura, ödeme, para | MUHASEBE | #133 |
| Yemek, kahvaltı, mutfak | FB | #134 |
| WiFi, internet, PMS, bilgisayar | IT | #135 |

## Kurulum

### 1. LINE Official Account Oluştur
1. https://developers.line.biz → Login (LINE Business ID)
2. Create Provider → "Lato Hotels"
3. Create Channel → Messaging API
4. Settings:
   - Webhook URL: `https://line.178-104-122-91.nip.io/webhook`
   - Use webhook: **ON**
   - Auto-reply messages: **OFF**
   - Greeting messages: **ON**
5. Channel Access Token + Channel Secret al → `.env`'e ekle

### 2. Environment Variables
```bash
LINE_CHANNEL_ACCESS_TOKEN=*** token>
LINE_CHANNEL_SECRET=*** secret>          # boşsa webhook REDDEDİLİR (LINE_ALLOW_INSECURE=1 sadece dev)
TRANSLATE_BOT_TOKEN=*** (mevcut)
OPENROUTER_API_KEY=*** (mevcut)
LATO_AI_MODEL=anthropic/claude-sonnet-5  # sınıflandırma modeli (varsayılan)
GOOGLE_API_KEY=*** (mevcut, Gemini OCR için)
```

### 3. Deploy
```bash
cd /opt/lato-line
docker build -t lato-line .
docker run -d --name lato-line --restart always \
    --network efloud-bot_default \
    --env-file /root/.hermes/profiles/lato/.env \
    -p 8089:8089 \
    lato-line
```

### 4. Caddy Config
```
line.178-104-122-91.nip.io {
    reverse_proxy lato-line:8089
}
```

## Personel Kayıt

Personel LINE bot'a ilk mesaj attığında `/register` komutu ile kaydolur:

```
/register Somchai TEKNIK
/register Nong HK
/register Kanya FB
/register Siriporn MUHASEBE
```

Kayıt sonrası her mesajı otomatik olarak doğru departmana yönlendirilir.

## Maliyet

| Bileşen | Maliyet |
|---|---|
| LINE Messaging API | Ücretsiz (200 mesaj/gün) |
| OpenRouter (Claude Sonnet 5, $2/$10 per 1M) | ~350–700 THB/ay (~50 mesaj/gün sınıflandırma) |
| Google Gemini (OCR) | ~200 THB/ay (~1000 foto/ay) |
| **Toplam** | **~550–900 THB/ay (~$16–26/ay)** |

> Maliyet artarsa `.env` → `LATO_AI_MODEL` ile daha ucuz modele tek satırda dönülür.

## LINE ↔ Telegram Köprüsü

```
LINE (personel)                    Telegram (yönetim)
     │                                  │
     ├── text mesaj ──→ AI sınıfla ──→ ├── departman topic
     ├── fatura foto ──→ OCR ────────→ ├── muhasebe topic (foto+tutar)
     ├── voice mesaj ──→ (Whisper) ──→ ├── yönetim topic (voice)
     │                                  │
     │ ←── onay mesajı ────────────── ├── cevap/manuel komut
```

Yönetim Telegram'dan cevap yazdığında, bot LINE'da ilgili personele push mesaj gönderir (TODO).
