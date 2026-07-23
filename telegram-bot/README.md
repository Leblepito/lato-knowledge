# 🤖 Lato Telegram Bot — Departman Input İşleyici

> Personel input dosyasını **hangi departman topic'ine atarsa, çıktı o departmana göre** hazırlanır.
> AI: **sadece Claude Sonnet 5** — Claude Pro/Max aboneliği üzerinden `claude` CLI ile,
> **token ücreti ödemeden** (plan limitleri dahilinde). LINE yok, her şey Telegram içinde.

## Akış

```
Telegram Topic (#130-135)
   │  📄 md/txt/csv  📸 foto  📕 pdf  💬 @mention veya /lato
   ▼
lato_telegram_bot.py
   ├─ topic → departman eşleme
   ├─ bağlam: departman README + dil paketi (tr.md) + şablonlar + spec
   ├─ Claude Sonnet 5 (claude_client.py: CLI → API → OpenRouter sırası)
   ▼
Aynı topic'e cevap + bilgi bankasına kayıt (departmanlar/<slug>/olaylar|envanter|hesaplar/...)
```

## Departman Çıktı Profilleri

| Topic | Departman | Input örneği | Üretilen çıktı |
|---|---|---|---|
| 130 | ⚡ Elektrik & Havuz | arıza foto, etiket, ölçüm | olay kaydı / envanter kartı / hesap + spec uygunluk (IP, SPD, SELV, 30mA) |
| 131 | 🔧 Teknik Bakım | klima arıza, bakım listesi | olay kaydı / bakım planı / envanter kartı |
| 132 | 🛎️ Operasyon | occupancy, vardiya raporu | özet rapor + aksiyonlar + TM30 hatırlatma |
| 133 | 📦 Satın Alma | fatura foto, teklif listesi | fatura özeti (firma/tutar/tarih) + satin-alinacaklar satırı |
| 134 | 🍽️ F&B | sıcaklık logu, menü | HACCP uygunluk + ihlal/aksiyon listesi |
| 135 | 💻 IT & Muhasebe | ekstre, bordro | mutabakat özeti + anomali işaretleme |
| 1 | Genel | herhangi | analiz + departman yönlendirme |

## Kurulum (ücretsiz — abonelik ile)

```bash
# 1) claude CLI kur ve abonelikle giriş yap (API faturası YOK)
npm install -g @anthropic-ai/claude-code
claude setup-token        # tarayıcıda Claude hesabınla onayla (Pro/Max)

# 2) Bağımlılık
pip3 install httpx

# 3) Çalıştır
export TELEGRAM_BOT_TOKEN=...   # @Latotry_bot
cd /opt/lato-knowledge/telegram-bot
python3 lato_telegram_bot.py
```

Kalıcı kurulum (önerilen — tek komut, repo kökünden):

```bash
bash /opt/lato-knowledge/deploy-v2.sh
```

Script: repo pull → claude CLI kontrol → bağımlılık → systemd servisi
([`lato-telegram-bot.service`](lato-telegram-bot.service)) kur + başlat.
Log takibi: `journalctl -u lato-telegram-bot -f`

## Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | zorunlu (@Latotry_bot) |
| `LATO_AI_MODEL` | `claude-sonnet-5` | tek model — Sonnet 5 |
| `LATO_REPO_DIR` | repo kökü | bilgi bankası konumu |
| `LATO_AUTO_SAVE` | `1` | üretilen kaydı repoya yaz (0 = sadece öner) |
| `LATO_GROUP_ID` | `-1003776134843` | Telegram grup |
| `ANTHROPIC_API_KEY` | — | opsiyonel ücretli fallback |
| `OPENROUTER_API_KEY` | — | opsiyonel ücretli fallback (yine Sonnet 5) |

## Notlar

- **"Ücretsiz" ne demek**: `claude setup-token` ile CLI, Claude Pro/Max aboneliğinin
  kotasını kullanır — token başına fatura çıkmaz. Yoğun kullanımda plan limitine
  takılırsa bot fallback'e geçer (key tanımlıysa) veya hata mesajı verir.
- Bot mesajlarını sırayla işler (tek worker) — kota ve CLI süreç yığılması koruması.
- Kaydedilen dosyalar sadece `departmanlar/` altına yazılır (path traversal korumalı);
  commit/push manuel (AGENTS.md kural 4 — Leb onayı).
- Voice mesaj bu botta kapsam dışı — #146'daki @Latotranslate_bot'a atın.
- Eski LINE köprüsü **deprecated**: `line-bot/` artık kurulum gerektirmiyor.
