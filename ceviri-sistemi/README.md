# 🌐 Lato Çeviri Sistemi

> Phuket otel grubu için **gerçek zamanlı çok dilli çeviri** — Türkçe ↔ Tayca ↔ İngilizce
> Telegram botu + WebSocket Push-to-Talk web app + Ses klonlama altyapısı

## 📋 İçindekiler

- [Mimari](#mimari)
- [Özellikler](#özellikler)
- [Kurulum](#kurulum)
- [Çalışma Akışı](#çalışma-akışı)
- [Modüller](#modüller)
- [Konfigürasyon](#konfigürasyon)
- [Ses Klonlama](#ses-klonlama)
- [Deploy](#deploy)
- [Sorun Giderme](#sorun-giderme)

---

## Mimari

```
                    ┌─────────────────────────────────────┐
                    │       Docker Container               │
                    │    (lato-translator:8088)            │
                    │                                      │
  Telegram Voice ──→│  ┌─────────┐  ┌──────────┐  ┌─────┐│──→ Topic #146
  Message (ogg)     │  │ Whisper  │→│ GPT-4o   │→│ TTS ││    (metin + ses)
                    │  │ (STT)    │  │ (çeviri) │  │     ││
  PTT Web App  ────→│  └─────────┘  └──────────┘  └─────┘│──→ Topic #146
  (WebSocket WSS)   │         ↑                       ↑   │
                    │    faster-whisper          Edge TTS  │
                    │    base model              +11Labs   │
                    └─────────────────────────────────────┘
                                        ↑
                              Caddy HTTPS reverse proxy
                         translate.178-104-122-91.nip.io
```

**Tek container, üç giriş noktası:**

| Giriş | Nasıl | Hız |
|---|---|---|
| **PTT Web App** | Topic'teki buton → WebSocket streaming | ~2-3s |
| **Voice Mesaj** | Telegram sesli mesaj → Whisper | ~3-5s |
| **Metin** | Telegram metin mesajı → çeviri | ~1-2s |

---

## Özellikler

### ✅ Mevcut
- **3 dil**: Türkçe (🇹🇷), Tayca (🇹🇭), İngilizce (🇬🇧) — otel/resort bağlamı
- **Push-to-Talk**: Basılı tut → konuşurken canlı çeviri gör → bırak → topic'e gönder
- **Voice Mesaj**: Telegram sesli mesaj gönder → otomatik çeviri + sesli yanıt
- **Text Çeviri**: Metin yaz → çevirileri al
- **Canlı Partial**: Konuşurken her 1.5s'de ara sonuç + çeviri (PTT modunda)
- **Sesli Çeviri**: Her hedef dil için TTS voice message otomatik gönderilir
- **Otomatik Dil Tespiti**: Whisper dili otomatik tanır
- **Türkçe Karakter Düzeltme**: 100+ kelime, bigram, trigram düzeltme tablosu
- **Otel Bağlamı**: Whisper initial_prompt ile otel/havuz/elektrik kelime hazinesi

### 🔧 Geliştirilebilir (altyapı hazır)
- **Ses Klonlama** (`voice_registry.py`): MFCC konuşmacı tanıma + ElevenLabs klonlama
- **Aksan Hafızası** (`accent_memory.py`): Kişiye özel telaffuz düzeltmeleri
- **Gemini Live API**: Gerçek zamanlı audio-to-audio çeviri (paid tier gerekli)

---

## Kurulum

### Gereksinimler
- Docker + Docker Compose
- Caddy reverse proxy (HTTPS için)
- Telegram Bot Token (`@BotFather`'dan)
- OpenRouter API Key (çeviri için)
- Google API Key (Gemini fallback için — opsiyonel)

### .env Değişkenleri

```bash
# .env dosyasına eklenecek
TRANSLATE_BOT_TOKEN=*** token>
OPENROUTER_API_KEY=*** key>
GOOGLE_API_KEY=*** key>
ELEVENLABS_API_KEY=*** (opsiyonel, ses klonlama için)
```

### Adımlar

1. **Bot oluştur**: `@BotFather` → `/newbot` → `@Latotranslate_bot`
2. **Gruba ekle**: Bot'u `Phuket-Lato` grubuna ekle, **admin yap**
3. **Kod kopyala**:
   ```bash
   git clone https://github.com/Leblepito/lato-knowledge.git
   cp -r lato-knowledge/ceviri-sistemi/src/* /opt/lato-translator/
   cp lato-knowledge/ceviri-sistemi/docker/* /opt/lato-translator/
   ```
4. **Build + Deploy**: `bash docs/deploy.sh`
5. **Caddy config**: `docs/caddy-config.conf`'u Caddyfile'a ekle, reload

---

## Çalışma Akışı

### Push-to-Talk (önerilen)

```
Kullanıcı                    Server                     Telegram Topic
   │                           │                              │
   │──WebSocket bağlan────────→│                              │
   │                           │                              │
   │──"start" (basıldı)───────→│                              │
   │←──"listening"─────────────│                              │
   │                           │                              │
   │──audio chunks (PCM 16k)──→│                              │
   │   (her 1.5s'de)           │──Whisper + Çeviri (partial)  │
   │←──"partial" (canlı metin)─│                              │
   │                           │                              │
   │──"stop" (bırakıldı)──────→│──Whisper (final)             │
   │                           │──GPT-4o-mini (çeviri)        │
   │←──"done" (sonuç)──────────│──Edge TTS (ses)              │
   │                           │──sendMessage─────────────────→│ (metin)
   │                           │──sendVoice──────────────────→│ (ses ×N)
   │←──"status: done"──────────│                              │
```

### Voice Mesaj (fallback)

```
Kullanıcı → Telegram voice mesaj → Bot indirir (getFile)
  → Whisper STT → dil tespiti + transkripsiyon
  → GPT-4o-mini çeviri (diğer 2 dile)
  → Edge TTS ses üretimi (her dil için)
  → Topic'e metin + sesli mesajlar gönderilir
```

---

## Modüller

### `src/config.py` — Konfigürasyon
Tüm ayarlar: dil listesi, API keys, model boyutu, Telegram chat/topic ID'leri.

### `src/stt_engine.py` — Speech-to-Text
- **Engine**: `faster-whisper` (CTranslate2 backend, CPU)
- **Model**: `base` (streaming için hızlı) / `small` (doğruluk için)
- **VAD**: Sessizlik bölümleri otomatik filtrelenir
- **Initial Prompt**: Otel/havuz/elektrik kelime hazinesi
- **Türkçe Düzeltme**: 100+ kelime, bigram, trigram tablosu
  - `calismiyor → çalışmıyor`
  - `oda da → odada`
  - `sigorta atmis → sigorta atmış`

### `src/translation_engine.py` — Çeviri Motoru
- **Provider**: OpenRouter (`openai/gpt-4o-mini`)
- **Prompt**: Phuket otel çevirmeni kişiliği
- **Toplu çeviri**: Tek istekte tüm hedef dillere çeviri
- **Fallback**: Hata durumunda tek tek deneme
- **Dil tespiti**: Tayca karakter aralığı + Türkçe karakter kontrolü

### `src/tts_engine.py` — Text-to-Speech
- **Primary**: ElevenLabs (`eleven_multilingual_v2`) — klonlanmış ses
- **Fallback**: Microsoft Edge TTS (ücretsiz, 3 dil)
  - TH: `th-TH-PremwadeeNeural`
  - TR: `tr-TR-EmelNeural`
  - EN: `en-US-AriaNeural`
- **Format**: OGG Opus (Telegram voice message)

### `src/voice_registry.py` — Konuşmacı Tanıma + Ses Klonlama
- **Algorithm**: MFCC (Mel-Frequency Cepstral Coefficients) + cosine similarity
- **Threshold**: 0.72 cosine similarity
- **ElevenLabs**: Instant Voice Clone (IVC) API
- **Registry**: `data/voice_registry.json` (fingerprint + voice_id)

### `src/accent_memory.py` — Aksan Düzeltme Hafızası
- **Kişiye özel**: Her konuşmacı için ayrı düzeltme listesi
- **Persistent**: `data/accent_corrections.json`
- **Örnek**: Somchai "eletrik" derse → "elektrik" olarak düzeltilir ve hatırlanır

### `src/app.py` — Unified Server
- **aiohttp** HTTP server (port 8088): PTT web app (`/`) + WebSocket (`/ws`)
- **Telegram polling** (background): voice + text mesajları dinler
- **Pipeline**: STT → Çeviri → TTS → Telegram gönderimi
- **Partial streaming**: PTT sırasında her 1.5s'de ara sonuç

---

## Konfigürasyon

### Telegram
| Ayar | Değer | Açıklama |
|---|---|---|
| Bot | `@Latotranslate_bot` | Çeviri botu (Hermes'ten ayrı) |
| Group | `-1003776134843` | Phuket-Lato grubu |
| Topic | `146` | 🌐 Çeviri / Translation / การแปล |
| Admin | Gerekli | Bot mesajları okuyabilmek için |

### Docker
```yaml
services:
  lato-translator:
    build: .
    container_name: lato-translator
    restart: always
    volumes:
      - ./data:/app/data
    env_file:
      - /root/.hermes/profiles/lato/.env
    networks:
      - efloud-bot_default
```

### Whisper Model Seçimi

| Model | Boyut | Hız | Doğruluk | Kullanım |
|---|---|---|---|---|
| `tiny` | ~75MB | ~0.5s | Düşük | Hız kritik |
| `base` | ~145MB | ~1.0s | Orta | **Mevcut** (streaming) |
| `small` | ~488MB | ~2.5s | Yüksek | Final pass |
| `medium` | ~1.5GB | ~5s | Çok yüksek | Sunucu yeterliyse |

---

## Ses Klonlama

### Nasıl Çalışır
1. Konuşmacıdan ses örneği alınır (rehber formu ile)
2. MFCC fingerprint çıkarılır → `voice_registry.json`'a kaydedilir
3. ElevenLabs ile ses klonlanır → voice_id alınır
4. Sonraki konuşmalarda:
   - MFCC ile konuşmacı tanınır (cosine similarity ≥ 0.72)
   - Tanınırsa klonlanmış ses kullanılır
   - Tanınmazsa varsayılan Edge TTS ses kullanılır

### Kayıt Formu
Bkz: `rehber/ses-kaydi-formu.md`

Her kullanıcı için:
- 3 dilde en az 30 saniye temiz ses kaydı
- Sabit telefon mesafesi, sessiz ortam
- OGG/MP3 format

---

## Deploy

### Sıfırdan Kurulum
```bash
# 1. Dosyaları kopyala
mkdir -p /opt/lato-translator
cp src/*.py /opt/lato-translator/
cp docker/* /opt/lato-translator/

# 2. .env hazırla
echo "TRANSLATE_BOT_TOKEN=***" >> /root/.hermes/profiles/lato/.env
echo "OPENROUTER_API_KEY=***" >> /root/.hermes/profiles/lato/.env

# 3. Build + Run
cd /opt/lato-translator
docker build -t lato-translator-lato-translator:latest .
docker run -d --name lato-translator --restart always \
    --network efloud-bot_default \
    --env-file /root/.hermes/profiles/lato/.env \
    -v $(pwd)/data:/app/data \
    lato-translator-lato-translator:latest
```

### Güncelleme
```bash
cd /opt/lato-translator
# Kodu güncelle (repo'dan kopyala)
docker stop lato-translator && docker rm lato-translator
docker build -t lato-translator-lato-translator:latest .
docker run -d --name lato-translator --restart always \
    --network efloud-bot_default \
    --env-file /root/.hermes/profiles/lato/.env \
    -v $(pwd)/data:/app/data \
    lato-translator-lato-translator:latest
```

### Log İzleme
```bash
docker logs lato-translator -f --tail 50
```

---

## Sorun Giderme

| Sorun | Çözüm |
|---|---|
| Bot mesajları görmüyor | Gruba admin olarak eklendiğinden emin ol |
| WebSocket bağlanmıyor | Caddy WebSocket proxy config'ini kontrol et |
| Whisper yavaş | Model'i `tiny` yap veya GPU ekle |
| Türkçe karakter bozuk | `ensure_ascii=False` ve `charset=utf-8` kullanıldığından emin ol |
| Çeviri hatası | OpenRouter API key'i kontrol et, quota dolmamış mı |
| TTS boş | Edge TTS voice adını kontrol et, internet bağlantısı gerekli |
| Mikrofon izni | HTTPS zorunlu (Caddy otomatik sağlar) |

### Gemini Live API (opsiyonel)
Sistemin Gemini Live API entegrasyonu hazırdır (paid tier gerekli):
- Model: `gemini-3.5-live-translate-preview`
- Avantaj: Audio → audio çeviri, STT+Translate+TTS tek adımda
- Dezavantaj: Free tier quota limiti

---

## Versiyon Geçmişi

| Sürüm | Tarih | Değişiklik |
|---|---|---|
| v1.0 | 2026-06-23 | İlk sürüm: PTT + Voice + Text, 3 dil, Docker |
