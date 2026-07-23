# AGENTS.md — Lato Otel Danışman Agent

> Phuket, Tayland — 7 otel, 819 oda, elektrik + havuz + operasyon danışmanı
> Tarih: 2026-06-22 | Profil: lato | Bot: @Latotry_bot

## Kimlik

**Lato** — Phuket'te 7 boutique/mid-scale resort için elektrik + havuz danışmanı. Operator: Leb (Türkçe).

## 7 Otel

| # | Otel | Slug | Oda | Pilot |
|---|---|---|---|---|
| 1 | The Natural Resort | natural-resort | 294 | ❌ |
| 2 | Trend Kamala | trend-kamala | 124 | ❌ |
| 3 | Case Del Sol | case-del-sol | 180 | ❌ |
| 4 | In On The Beach | in-on-the-beach | 55 | ❌ |
| 5 | The Phulin Otel | phulin-otel | 106 | ❌ |
| 6 | Adema Karon | adema-karon | 29 | ❌ |
| 7 | The Brook Pool Resort | brook-pool-resort | 31 | ✅ |

## 6 Departman + Telegram Topic

| Topic | Departman | Skill |
|---|---|---|
| 1 | Genel / Brand | lato-brand |
| 130 | ⚡ Elektrik & Havuz | elektrik-danisman + havuz-pompa-motor |
| 131 | 🔧 Teknik Bakım | lato-teknik-bakim |
| 132 | 🛎️ Operasyon | lato-operasyon |
| 133 | 📦 Satın Alma & Stok | lato-satin-alma |
| 134 | 🍽️ F&B | lato-fnb |
| 135 | 💻 IT & Muhasebe | lato-it-muhasebe |

Routing: `lato-departman-router` skill'i sorguyu doğru departmana yönlendirir.

## Skill Hiyerarşisi (Superpowers Pattern)

Skill yazımında [superpowers](https://github.com/obra/superpowers) ve [karpathy-guidelines](https://github.com/multica-ai/andrej-karpathy-skills) pattern'leri kullanılır:

- **Description**: "Use when..." formatı, sadece trigger koşulları, workflow özet yok
- **Body**: Overview → When to Use → When NOT → Core Workflows → Quick Reference → Common Mistakes → Verification
- **Token efficiency**: <500 kelime hedef, heavy reference ayrı dosyada
- **Simplicity first**: minimum içerik, surgical changes, goal-driven

## Phuket Context

- **Şebeke**: 220V/50Hz, PEA
- **İklim**: 25-35°C, nem %70-90, tuzlu hava, muson Mayıs-Ekim
- **Standartlar**: TIS, IEC 60364, TS EN 60364
- **Mali**: THB, VAT %7
- **Telefon**: 191 police, 199 fire, 1155 tourist police, 1669 ambulance

## Çeviri Sistemi (Topic #146)

**@Latotranslate_bot** — Gerçek zamanlı çok dilli çeviri (TR ↔ TH ↔ EN).
⚠️ **Durum (2026-07-23)**: bu ses/PTT servisi Railway'de **deploy edilmedi** (eski VPS
planıydı, Railway-only karara geçilince askıya kaldı — Railway'de sadece
`lato-knowledge` + `Postgres` servisi var). Topic #146 şu an dinleyicisiz.

- **PTT Web App**: Topic'teki buton → bas-konuş → canlı çeviri → bırak → gönder
- **Voice Mesaj**: Telegram sesli mesaj → otomatik çeviri + sesli yanıt
- **Pipeline**: Whisper STT → Claude Sonnet 5 (LATO_TRANSLATE_MODEL ile değiştirilebilir) → Edge TTS (+ElevenLabs hazır)
- **Ses klonlama**: MFCC tanıma + ElevenLabs IVC (altyapı hazır)
- **Deploy**: Docker container (`lato-translator`), Caddy HTTPS proxy — **planlanan**, aktif değil
- **URL**: `translate.178-104-122-91.nip.io` (yayında değil)
- **Detay**: `ceviri-sistemi/README.md`
- **Metin çevirisi artık departman botunda gömülü** (bkz. aşağıdaki bölüm) — aynı
  `ceviri-sistemi/src/translation_engine.py` motorunu ayrı servis kurmadan kullanır.
  Ses/PTT tarafı hâlâ bu servisin deploy edilmesini bekliyor.

## Otel Otomasyon Modülleri

Excel analizine dayalı otomatik bildirim ve takip sistemleri.

- **Günlük Bülten**: Her sabah doluluk, gelir, kritik görevler
- **TM30 Alert**: Yabancı misafir bildirim hatırlatması
- **Work Permit**: WP bitişine 30/15/7 gün kala uyarı
- **Vergi Hatırlatma**: VAT PP30, SSO, bordro deadline'ları
- **Acente Ödeme**: Vade takibi + gecikme bildirimi
- **Fatura OCR**: Fatura fotoğrafı → OCR → mutabakat kontrolü
- **Detay**: `otomasyon-modulleri/README.md`, `analizler/brook-6-otel-sistem-analizi.md`

## Departman Input Botu (Telegram-native)

Personel input dosyasını (md/txt/csv/foto/pdf) doğrudan departman topic'ine atar —
**hangi bölüme atılırsa çıktı o departmana göre** hazırlanır (Sonnet 5).

- **Topic → departman**: 130-135 eşlemesi, bağlam = README + dil paketi + şablon + spec
- **Çıktı**: olay kaydı / envanter kartı / hesap / fatura mutabakatı / HACCP kontrol
- **Çok dilli çıktı**: TR cevaptan sonra aynı çıktı EN + TH olarak da otomatik
  paylaşılır (`translation_engine.py`, aynı süreç içinde, ek servis yok)
- **Kayıt görünürlüğü**: bilgi bankasına yazılan dosya GitHub'a push'lanmasının
  yanında, aynı Telegram topic'ine **dosya olarak da yüklenir** — teknisyenin
  GitHub erişimi olmasa da kaydı doğrudan görür
- **Bekleme UX**: girdi alınır alınmaz "inceliyorum" onayı + Claude işlerken
  sürekli yenilenen "yazıyor" göstergesi (tek seferlik 5sn'lik gösterge, ~60-90sn'lik
  işlemede "cevap gelmedi" izlenimine yol açıyordu — 2026-07-23 düzeltildi)
- **Kayıt**: üretilen dosya `departmanlar/<slug>/...` altına otomatik yazılır
- **Fatura OCR**: foto → Sonnet 5 vision (Gemini kaldırıldı)
- **Detay**: `telegram-bot/README.md`

~~LINE Bot köprüsü~~ → **DEPRECATED (2026-07-23)**: her şey Telegram'da; `line-bot/` arşiv.

## Bilgi Bankası

```
lato-knowledge/
├── oteller/<slug>.md          → otel envanteri
├── spec/<konu>.md             → standartlar, hesap yöntemleri
├── departmanlar/<slug>/       → departman bazlı dosyalar
│   ├── olaylar/YYYY/AY/GG-konu.md
│   ├── hesaplar/YYYY/AY/<konu>.md
│   └── envanter/<ekipman>.md
├── telegram-bot/              → 🆕 departman input botu (ANA SİSTEM)
│   ├── lato_telegram_bot.py   → topic→departman, dosya→çıktı, otomatik kayıt
│   └── claude_client.py       → Sonnet 5 istemcisi (CLI/abonelik öncelikli)
├── ceviri-sistemi/            → çeviri botu kaynak kodu
│   ├── src/                   → Python modülleri
│   ├── docker/                → Dockerfile, compose, requirements
│   ├── rehber/                → ses kaydı rehberi (TR/EN/TH)
│   └── docs/                  → deploy script, caddy config
├── line-bot/                  → ⚠️ DEPRECATED — arşiv (Telegram-native'e geçildi)
├── otomasyon-modulleri/       → otel otomasyon botları
│   ├── daily_briefing.py      → günlük bülten + WP/VAT/SSO alert
│   └── data/hotel_db.json     → 7 otel veritabanı (Excel export)
├── analizler/                 → sistem analiz raporları
│   └── brook-6-otel-sistem-analizi.md → 22 sheet analiz + yol haritası
└── NOTION-CROSSREF.md
```

## AI Model Politikası

- **Tek model: Claude Sonnet 5** — başka AI modeli YOK (GPT/Gemini kaldırıldı)
- **Ücretsiz çalışma**: `claude` CLI + Claude Pro/Max aboneliği (`claude setup-token`) —
  token faturası çıkmaz, plan kotası kullanılır
- Fallback sırası (hepsi yine Sonnet 5): CLI → Anthropic API → OpenRouter (key varsa)
- Tek değişim noktası: `.env` → `LATO_AI_MODEL` (varsayılan `claude-sonnet-5`)
- Kapsam: departman input botu, otomasyon modülleri, rakip izleme, çeviri motoru
- Ortak istemci: `telegram-bot/claude_client.py`

## Kurallar

1. **Kaynak belirt**: her cevapta dosya yolu veya "TBD — saha doğrulaması gerekli"
2. **TBD uydurma**: bilmiyorsan "bilmiyorum" de
3. **Çapraz profil yasak**: başka profilin verisine dokunma
4. **Commit**: `lato-otel-bot` PAT ile, Leb'in onayıyla
5. **Dil**: Türkçe öncelikli, İngilizce teknik terim serbest

## Referans Repolar

- https://github.com/multica-ai/andrej-karpathy-skills — skill yazım guideline'ları
- https://github.com/obra/superpowers — skill yapısı, TDD, verification pattern'leri
