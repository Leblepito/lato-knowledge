# 🛠️ Lato Sistemi — Kurulum (Railway)

> Tamamı **Telegram içinde** çalışan Lato otomasyonu — **Railway'de tek servis**:
> departman input botu + gömülü cron bültenleri aynı süreçte.
> AI: **sadece Claude Sonnet 5**, Claude Pro/Max aboneliği üzerinden — **token faturası YOK**.
> Kayıtlar ephemeral diske değil, **GitHub'a push-back** ile kalıcı olur.

## Mimari (Railway)

```
Railway Service: lato-telegram-bot  (Dockerfile.railway — repo kökü)
 ├── Telegram long polling (webhook/port GEREKMEZ)
 ├── Topic → departman input işleme (Sonnet 5, CLAUDE_CODE_OAUTH_TOKEN ile)
 ├── Gömülü cron: 08:00 bülten, 09:00 WP/TM30/vergi, Pzt 10:00 finansal, Pzt+Per 07:00 rakip (ICT)
 └── Kayıt → departmanlar/<slug>/... → git commit + push (GITHUB_TOKEN)
Railway PostgreSQL  (sonraki adım — hotel_db + kayıt indeksi)
```

## 1. Hazırlık (kendi bilgisayarında, 2 dakika)

```bash
# a) Claude abonelik token'ı (ücretsiz Sonnet 5'in anahtarı)
npm install -g @anthropic-ai/claude-code
claude setup-token
# → çıkan sk-ant-oat... değerini kopyala = CLAUDE_CODE_OAUTH_TOKEN
```

b) **GitHub token** (kayıt push-back için): GitHub → Settings → Developer settings →
Fine-grained tokens → Generate: Repository access = **Only lato-knowledge**,
Permissions → **Contents: Read and write**. → `GITHUB_TOKEN`

c) Telegram bot token'ı hazırda yoksa @BotFather → `TELEGRAM_BOT_TOKEN`
(⚠️ aynı token'ı başka bir sistem getUpdates ile dinliyorsa 409 çatışır — bu bota ayrı token en temizi).

## 2. Railway'de Servisi Aç (5 dakika)

1. [railway.com](https://railway.com) → **New Project** → **Deploy from GitHub repo** → `Leblepito/lato-knowledge`
2. Build otomatik: repo kökündeki `railway.json` → `Dockerfile.railway` (replica=1 ayarlı — değiştirme, polling çatışır)
3. Service → **Variables** → ekle:

| Variable | Değer | Zorunlu |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather token | ✅ |
| `CLAUDE_CODE_OAUTH_TOKEN` | `claude setup-token` çıktısı | ✅ |
| `GITHUB_TOKEN` | fine-grained PAT (Contents RW) | ✅ (push-back için) |
| `LATO_GROUP_ID` | `-1003776134843` | varsayılan zaten bu |
| `LATO_CRON` | `1` | varsayılan açık |
| `LATO_GIT_PUSH` | `1` | varsayılan açık (Dockerfile) |
| `ANTHROPIC_API_KEY` | — | ❌ opsiyonel ücretli fallback |

4. **Deploy** → Logs'ta şunu gör: `🚀 Lato Telegram Bot aktif — @... | model=claude-sonnet-5 | git_push=True` ve `⏰ Gömülü cron aktif`

Port/domain ayarı GEREKMEZ — bot polling ile çalışır, inbound trafik yok.

## 3. Doğrulama Checklist

- [ ] Logs: `Lato Telegram Bot aktif` + `Gömülü cron aktif` + `REPO_DIR → /tmp/lato-repo (git push-back aktif)`
- [ ] Herhangi bir departman topic'inde `/help` → kullanım kartı geldi
- [ ] #131'e arıza fotoğrafı → olay kaydı + `💾 kaydedildi ... ☁️ GitHub'a push edildi`
- [ ] GitHub'da commit görünüyor: `kayit: departmanlar/teknik-bakim/olaylar/...`
- [ ] #133'e fatura fotoğrafı → firma/tutar/tarih özeti
- [ ] Ertesi sabah 08:00 (Phuket) → #132'ye günlük bülten düştü

## 4. Sonraki Adım: PostgreSQL (Railway)

Railway → **New** → **Database** → **PostgreSQL** → `DATABASE_URL` otomatik gelir.
Plan: `hotel_db.json` (oteller/personel/tedarikçi) + kayıt indeksi tablolara taşınacak;
bilgi bankasının kendisi (md dosyaları) **git'te kalır** — audit-trail tasarımı bu.
Bu migrasyon ayrı bir iş — istenince şema + kod hazırlanır.

Çeviri sistemi (#146) da istenirse ikinci Railway servisi olarak açılır
(`ceviri-sistemi/docker/Dockerfile`, port 8088 + public domain) — şimdilik kapsam dışı.

## 5. Bakım

| Periyot | İş |
|---|---|
| Gerekirse | `claude setup-token` yenile → Railway'de `CLAUDE_CODE_OAUTH_TOKEN` güncelle |
| 90 gün | `GITHUB_TOKEN` yenile |
| Aylık | `hotel_db.json` gerçek verilerle güncelle (repo'ya commit → redeploy otomatik) |
| Push sonrası | Railway GitHub entegrasyonu her push'ta otomatik redeploy eder |

**Maliyet**: AI = 0 (abonelik kotası) · Railway = seçilen plan (bot hafif: ~256MB RAM yeter).

---

<details><summary>Alternatif: VPS kurulumu (eski yöntem)</summary>

VPS'te çalıştırmak istersen: `bash deploy-v2.sh` (systemd servisi kurar).
Detay: `telegram-bot/README.md`. Railway varken gerekmez.
</details>
