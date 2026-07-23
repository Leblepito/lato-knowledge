# 🛠️ Lato Sistemi — Sıfırdan Kurulum Rehberi

> Tamamı **Telegram içinde** çalışan Lato otomasyonunun kurulumu:
> departman input botu + otomasyon modülleri + çeviri.
> AI: **sadece Claude Sonnet 5**, Claude Pro/Max aboneliği üzerinden `claude` CLI ile —
> **token ücreti YOK** (plan limitleri dahilinde). LINE köprüsü kaldırıldı (deprecated).
> Hedef sunucu: Ubuntu/Debian VPS (mevcut: `178.104.122.91`).

## 0. Önkoşullar

| Gerekli | Nereden | Not |
|---|---|---|
| VPS (Python 3.11+) | mevcut | Docker opsiyonel |
| Telegram supergroup + Topics | Telegram | Grup: `-1003776134843`, forum modu açık |
| Ana bot | @BotFather → @Latotry_bot | Gruba admin ekle |
| Çeviri botu | @BotFather → @Latotranslate_bot | Gruba admin ekle (Topic #146) |
| **Claude Pro/Max aboneliği** | claude.ai | Sonnet 5'in ücretsiz çalışma yolu |
| GitHub PAT | github.com | `repo` scope, 90 gün — bilgi bankası commit'leri |

Artık **gerekmeyen**ler: ~~OpenRouter key~~ ~~Google/Gemini key~~ ~~LINE channel~~
(OCR dahil her şeyi Sonnet 5 vision yapıyor; API key'ler sadece opsiyonel fallback).

Telegram topic ID'leri:
`1` Genel · `130` ⚡ Elektrik & Havuz · `131` 🔧 Teknik Bakım · `132` 🛎️ Operasyon ·
`133` 📦 Satın Alma · `134` 🍽️ F&B · `135` 💻 IT & Muhasebe · `146` 🌐 Çeviri

## 1. Repo + Claude CLI (ücretsiz Sonnet 5)

```bash
cd /opt
git clone https://github.com/Leblepito/lato-knowledge.git

# Claude CLI — abonelik girişi (tek seferlik, API faturası çıkarmaz)
npm install -g @anthropic-ai/claude-code
claude setup-token          # tarayıcıda Claude hesabınla onayla

# Doğrula (Sonnet 5 cevap veriyorsa hazırsın):
claude -p --model claude-sonnet-5 "tek kelimeyle: hazır mısın?"
```

## 2. Ortam Değişkenleri (.env)

Tek merkezi dosya: `/root/.hermes/profiles/lato/.env`

```bash
# Telegram
TELEGRAM_BOT_TOKEN=***        # @Latotry_bot (input botu + otomasyon)
TRANSLATE_BOT_TOKEN=***       # @Latotranslate_bot

# AI — tek model
LATO_AI_MODEL=claude-sonnet-5   # değiştirme noktası (varsayılan zaten bu)

# Opsiyonel ÜCRETLİ fallback'ler (CLI kotası dolarsa — boş bırakılabilir)
# ANTHROPIC_API_KEY=***
# OPENROUTER_API_KEY=***

# Opsiyonel
# ELEVENLABS_API_KEY=***      # sesli bülten; yoksa Edge TTS (ücretsiz)
```

## 3. Departman Input Botu (ANA SİSTEM)

Kullanıcı hangi topic'e input dosyası atarsa, çıktı o departmana göre hazırlanır.

**Tek komut kurulum** (adım 1-2 tamamsa):

```bash
bash /opt/lato-knowledge/deploy-v2.sh
```

Manuel test için:

```bash
cd /opt/lato-knowledge/telegram-bot
pip3 install httpx
set -a; source /root/.hermes/profiles/lato/.env; set +a
python3 lato_telegram_bot.py     # kalıcı çalıştırma deploy-v2.sh ile (systemd)
```

Test: #131 Teknik Bakım'a bir arıza fotoğrafı at → bot olay kaydı taslağı üretip
`departmanlar/teknik-bakim/olaylar/...` altına kaydetmeli. Detay: `telegram-bot/README.md`

## 4. Otomasyon Modülleri (cron bültenleri)

```bash
cd /opt/lato-knowledge/otomasyon-modulleri
python3 hotel_data.py                        # 7 otel / 819 oda seed
python3 automation_engine.py briefing        # test → #132'ye bülten
```

Zamanlama (crontab, Asia/Bangkok):

```cron
0 8 * * *   cd /opt/lato-knowledge/otomasyon-modulleri && python3 automation_engine.py briefing
0 9 * * *   ... automation_engine.py wp && ... automation_engine.py tm30 && ... automation_engine.py bureaucratic
0 10 * * 1  ... automation_engine.py financial && ... automation_engine.py electricity && ... automation_engine.py reconciliation
0 7 * * 1,4 cd /opt/lato-knowledge/otomasyon-modulleri && python3 competitor_monitor.py
```

## 5. Çeviri Sistemi (Topic #146)

```bash
cd /opt/lato-knowledge/ceviri-sistemi/docker
docker compose up -d --build
```

Çeviri de önce claude CLI dener (ücretsiz); container'da CLI yoksa OpenRouter
fallback'i için key gerekir — CLI'lı kurulum için `telegram-bot/Dockerfile`'daki
node+claude-code kalıbını kullan. Caddy: `translate.178-104-122-91.nip.io → lato-translator:8088`.

## 6. Doğrulama Checklist

- [ ] `claude -p --model claude-sonnet-5 "test"` cevap veriyor (abonelik OK)
- [ ] #131'e foto at → olay kaydı taslağı + `💾 kaydedildi` cevabı geldi
- [ ] #133'e fatura fotoğrafı at → firma/tutar/tarih özeti geldi
- [ ] `/help` her departman topic'inde kullanım özetini basıyor
- [ ] `automation_engine.py briefing` → #132'ye bülten + "🤖 AI Öneri" satırı
- [ ] `systemctl status lato-telegram-bot` → active (running)

## 7. Bakım

| Periyot | İş |
|---|---|
| 90 gün | GitHub PAT yenile → `.env` güncelle |
| Aylık | `hotel_db.json` gerçek verilerle güncelle |
| Gerekirse | `claude setup-token` yenile (oturum düşerse bot uyarı verir) |
| Haftalık | `departmanlar/` altına botun yazdığı kayıtları gözden geçir + commit (Leb onayı) |

**Maliyet**: 0 THB/ay ek AI gideri — Sonnet 5 mevcut Claude aboneliğinin kotasından
çalışır. Kota dolarsa bot bekletir/uyarır; istenirse `.env`'e API key eklenerek
ücretli fallback açılır (o da Sonnet 5).
