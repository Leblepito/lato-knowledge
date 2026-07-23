# 🤖 Lato Telegram Bot — Departman Input İşleyici

> Personel input dosyasını **hangi departman topic'ine atarsa, çıktı o departmana göre** hazırlanır.
> AI: **sadece Claude Sonnet 5** — Claude Pro/Max aboneliği üzerinden `claude` CLI ile,
> **token ücreti ödemeden** (plan limitleri dahilinde). LINE yok, her şey Telegram içinde.

## Akış

```
Telegram Topic (#1 Genel  VEYA  #130-135 doğrudan departman)
   │  📄 md/txt/csv  📸 foto  📕 pdf  💬 @mention veya /lato
   ▼
lato_telegram_bot.py
   ├─ "🔍 Alındı, inceliyorum..." anında onay + "yazıyor" göstergesi (4sn'de bir yenilenir)
   ├─ #1 Genel'e dosya atıldıysa: classify_department() ile hedef departmanı bul
   │  (ayrı hafif Claude çağrısı) → orijinal mesaj copyMessage ile doğru topic'e taşınır
   ├─ bağlam: departman README + dil paketi (tr.md) + şablonlar + spec (hedef departmandan)
   ├─ Claude Sonnet 5 (claude_client.py: CLI → API → OpenRouter sırası)
   ▼
Doğru departman topic'ine: TR cevap + kaydedilen dosya (Telegram'a doğrudan yüklenir, GitHub gerekmez)
   ▼
translation_engine.py (aynı süreç, ek servis yok) → 📄 TR.txt + 📄 EN.txt + 🔊 TH.mp3 (edge-tts sesli)
   ▼
Bilgi bankasına kayıt (departmanlar/<slug>/olaylar|envanter|hesaplar/...) + GitHub push
```

Not: girdi + kalıcı kayıt Türkçe kalır (audit-trail tek dilde tutarlı); teknisyen için
üretilen **cevap** TR+EN metin dosyası ve TH sesli dosya olarak da paylaşılır
(`LATO_TRANSLATE=0` ile kapatılabilir). #1 Genel'e atılan girdi otomatik doğru
departmana yönlendirilir; departman gerçekten belirsizse #1'de kısa özet + öneri kalır.

## Departman Çıktı Profilleri

| Topic | Departman | Input örneği | Üretilen çıktı |
|---|---|---|---|
| 130 | ⚡ Elektrik & Havuz | arıza foto, etiket, ölçüm | olay kaydı / envanter kartı / hesap + spec uygunluk (IP, SPD, SELV, 30mA) |
| 131 | 🔧 Teknik Bakım | klima arıza, bakım listesi | olay kaydı / bakım planı / envanter kartı |
| 132 | 🛎️ Operasyon | occupancy, vardiya raporu | özet rapor + aksiyonlar + TM30 hatırlatma |
| 133 | 📦 Satın Alma | fatura foto, teklif listesi | fatura özeti (firma/tutar/tarih) + satin-alinacaklar satırı |
| 134 | 🍽️ F&B | sıcaklık logu, menü | HACCP uygunluk + ihlal/aksiyon listesi |
| 135 | 💻 IT & Muhasebe | ekstre, bordro | mutabakat özeti + anomali işaretleme |
| 1 | Genel | herhangi | **otomatik yönlendirme**: dosya doğru departmana taşınır, çıktı orada üretilir. Departman gerçekten belirsizse #1'de kısa özet + öneri |

## Kurulum — Railway (önerilen)

Adım adım: **[`../KURULUM.md`](../KURULUM.md)**. Özet:

1. PC'de `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` kopyala (abonelik = ücretsiz Sonnet 5)
2. Railway → Deploy from GitHub → bu repo (build: kökteki `Dockerfile.railway`, `railway.json` otomatik)
3. Variables: `TELEGRAM_BOT_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `GITHUB_TOKEN` (Contents RW)
4. Deploy → log: `🚀 Lato Telegram Bot aktif` — port/domain gerekmez (long polling)

**Railway'de kalıcılık**: disk ephemeral olduğu için bot her kaydı GitHub'a
**commit + push** eder (`LATO_GIT_PUSH=1`, başlangıçta token'la taze klon alır).
**Cron'lar gömülü** (`LATO_CRON=1`): 08:00 bülten, 09:00 WP/TM30/vergi,
Pzt 10:00 finansal, Pzt+Per 07:00 rakip — hepsi ICT, ayrı servis gerekmez.

<details><summary>Alternatif: VPS / systemd kurulumu</summary>

```bash
bash /opt/lato-knowledge/deploy-v2.sh   # repo pull → CLI kontrol → systemd kur+başlat
journalctl -u lato-telegram-bot -f      # log takibi
```
</details>

## Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | zorunlu (@Latotry_bot) |
| `CLAUDE_CODE_OAUTH_TOKEN` | — | abonelik token'ı (`claude setup-token`) — headless ortamda zorunlu |
| `LATO_AI_MODEL` | `claude-sonnet-5` | tek model — Sonnet 5 |
| `LATO_REPO_DIR` | repo kökü | bilgi bankası konumu |
| `LATO_AUTO_SAVE` | `1` | üretilen kaydı repoya yaz (0 = sadece öner) |
| `LATO_GIT_PUSH` | `0` (Railway image'ında `1`) | kayıtları GitHub'a commit+push et |
| `GITHUB_TOKEN` | — | push-back için PAT (Contents RW, sadece bu repo) |
| `LATO_CRON` | `1` | gömülü cron bültenleri (0 = kapat) |
| `LATO_GROUP_ID` | `-1003776134843` | Telegram grup |
| `LATO_TRANSLATE` | `1` | cevabı TR+EN .txt ve TH .mp3 (sesli) olarak da paylaş (0 = kapat) |
| `ANTHROPIC_API_KEY` | — | opsiyonel ücretli fallback |
| `OPENROUTER_API_KEY` | — | opsiyonel ücretli fallback (yine Sonnet 5) |

## Notlar

- **"Ücretsiz" ne demek**: `claude setup-token` ile CLI, Claude Pro/Max aboneliğinin
  kotasını kullanır — token başına fatura çıkmaz. Yoğun kullanımda plan limitine
  takılırsa bot fallback'e geçer (key tanımlıysa) veya hata mesajı verir.
- Bot mesajlarını sırayla işler (tek worker) — kota ve CLI süreç yığılması koruması.
- Kaydedilen dosyalar sadece `departmanlar/` altına yazılır (path traversal korumalı);
  commit/push otomatik (`LATO_GIT_PUSH=1`) — aynı dosya ayrıca Telegram'a da
  belge olarak yüklenir, teknisyen GitHub'a girmeden görür.
- **Çeviri**: `ceviri-sistemi/src/translation_engine.py` doğrudan bu süreçte
  çağrılır (claude CLI → ücretsiz); @Latotranslate_bot'un ses/PTT servisi ayrı ve
  şu an Railway'de deploy edilmedi (bkz. AGENTS.md § Çeviri Sistemi). Voice mesaj
  girdisi hâlâ bu botta kapsam dışı (sadece çıktı tarafında TH ses üretiliyor).
- **Tayca ses**: `edge-tts` (Microsoft, ücretsiz, API key gerekmez) — ağ erişimi
  yoksa/başarısızsa sessizce atlanır, TR/EN metin çıktısı yine gelir.
- **#1 Genel yönlendirme**: `classify_department()` ayrı bir Claude çağrısıyla
  hedef departmanı belirler, sonra üretim O departmanın gerçek bağlamıyla
  (README+dil paketi+spec) yapılır — doğrudan o topic'e atmakla aynı kalite,
  sadece bir adım daha yavaş (2 Claude çağrısı).
- Eski LINE köprüsü **deprecated**: `line-bot/` artık kurulum gerektirmiyor.
