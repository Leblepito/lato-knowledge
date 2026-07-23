# 🔍 Telegram Otomasyonu — Kod Review & Geliştirme Raporu

> Tarih: 2026-07-23 | Kapsam: `otomasyon-modulleri/`, `line-bot/`, `ceviri-sistemi/` (config)
> Bu review'daki tüm 🔴/🟠 bulgular aynı gün kod tarafında düzeltildi.

## Özet

Sistem mimarisi sağlam (webhook + cron + topic routing doğru kurgulanmış). Ancak
canlıda sessiz hata üreten 4 kritik bug vardı: OCR alan uyuşmazlığı, Telegram'da
bozuk bold formatı, kaydedilmeyen personel kaydı ve yanlış otel verisi.
Tümü düzeltildi; AI katmanı **Claude Sonnet 5**'e taşındı.

## 🔴 Kritik Bulgular (düzeltildi)

| # | Dosya | Bulgu | Düzeltme |
|---|---|---|---|
| 1 | `line_bot.py` OCR | Gemini prompt'u İngilizce serbest JSON istiyordu, kod `tutar/firma/tarih` anahtarlarını okuyordu → **her fatura 0 THB / "?" görünüyordu** | Prompt sabit Türkçe şemaya bağlandı, güvenli parse + float dönüşümü eklendi |
| 2 | `hotel_data.py` | Seed'deki 7 otel gerçek portföyle uyuşmuyordu (Patong Heritage, Kata Sea View... toplam 246 oda ≠ 819). Bültenler yanlış portföy raporluyordu | AGENTS.md'deki gerçek 7 otel + oda sayılarıyla değiştirildi (819 oda), personel slug'ları remap edildi, `hotel_db.json` yeniden üretildi |
| 3 | `line_bot.py` `tg_send` | `**bold**` yazılıyor ama `parse_mode` gönderilmiyordu → Telegram'da çift yıldızlar metin olarak görünüyordu | Markdown parse_mode + tek `*` bold + düz metin fallback |
| 4 | `line_bot.py` `/register` | Kayıt **hiç kaydedilmiyordu** ("yönetici onayı" mesajı atıp veriyi çöpe atıyordu) → herkes "Bilinmeyen/GENEL" kalıyordu | Registry'ye gerçek yazma + departman doğrulama + yönetime bildirim |
| 5 | `line-bot/docker-compose.yml` | Kopya `lato-translator` servisi LINE imajından build ediliyordu — gerçek çeviri container'ıyla **aynı isimle çakışıyordu** | Kopya servis kaldırıldı |
| 6 | `line_bot.py` `verify_signature` | Secret tanımsızsa **tüm istekleri kabul ediyordu** (imzasız sahte webhook riski) | Secret yoksa reddet; sadece `LINE_ALLOW_INSECURE=1` ile dev bypass |

## 🟠 Orta Bulgular (düzeltildi)

| # | Dosya | Bulgu | Düzeltme |
|---|---|---|---|
| 7 | `automation_engine.py` | Bürokratik pencereler negatif gün üretiyordu (dom=16 → "-1 gün kaldı"); PND50 yanlış aylarda (3/6/9/12) uyarıyordu | Pencereler 8-15 / 20-25'e çekildi; PND50 → Mayıs (FY+150 gün), PND51 → Ağustos eklendi |
| 8 | `automation_engine.py` | Telegram 429 rate-limit'te mesaj sessizce düşüyordu | `retry_after` bekleyip 3 deneme |
| 9 | `line_bot.py` | Sınıflandırıcı TR/EN/TH döndürüyor, bayrak sözlüğü küçük harf bekliyordu → bayrak hiç görünmüyordu | `.lower()` normalizasyonu |
| 10 | `line_bot.py` | TEKNIK her şeyi #130'a (Elektrik & Havuz) atıyordu; #131 Teknik Bakım ve #135 IT hiç kullanılmıyordu | `ELEKTRIK`→130, `TEKNIK`→131, `IT`→135 ayrımı eklendi (AGENTS.md şemasıyla hizalı) |
| 11 | `daily_briefing.py` | v2 şemasındaki liste `occupancy` ile çökiyordu (`list * int` hatası) | Liste/skaler uyumu + DEPRECATED işareti (cron'da `automation_engine.py briefing` kullanın) |
| 12 | `line_bot.py` | `asyncio.create_task` referans tutulmadan çağrılıyordu (GC riski) + LINE API hataları sessizdi | `_spawn` task registry + non-200 loglama |
| 13 | `competitor_monitor.py` | Ortalama ADR hesabında pay/payda uyumsuzdu | Geçerli ADR listesi üzerinden hesap |

## 🤖 Sonnet 5 Geçişi

- Tüm AI çağrıları tek env değişkenine bağlandı: **`LATO_AI_MODEL=anthropic/claude-sonnet-5`** (varsayılan)
- Kapsam: `automation_engine.py` (AI öneriler), `competitor_monitor.py` (fiyat stratejisi), `line_bot.py` (sınıflandırma), `ceviri-sistemi/config.py` (çeviri — ayrıca `LATO_TRANSLATE_MODEL` ile bağımsız ayarlanabilir)
- Claude çıktı uyumluluğu: ```json çitlerini tolere eden `parse_ai_json()` eklendi (response_format'ı desteklemeyen durumlara karşı)
- Maliyet: $2/M input, $10/M output (1M context) — mevcut hacimde ~$10-25/ay; gpt-4o-mini'ye göre artış bilinçli tercih (kalite ↑)

## 🟡 Öneriler (sonraki sprint — kod değişmedi)

1. **OTA yorumları hâlâ mock** (`ota_review_monitor`) — Booking/Agoda gerçek scraping veya API bağlanmalı; şu an rapor gerçek yorum içermiyor
2. **Rakip fiyat simülasyonu**: scraping başarısız olunca rastgele "Tahmini" fiyat üretiliyor ve AI önerisi buna dayanıyor — Tahmini satır sayısı raporda belirtiliyor ama AI'ya "veri simüle" uyarısı da geçilmeli
3. **Telegram → LINE cevap köprüsü** README'de TODO — personele geri dönüş hâlâ manuel
4. **LINE webhook dedup yok** — LINE retry'larında aynı mesaj iki kez işlenebilir (message_id cache önerilir)
5. **Voice → Whisper STT** entegrasyonu TODO (ses şimdilik sadece forward ediliyor)
6. **Test yok** — en azından `classify_message` parse ve deadline pencereleri için pytest önerilir
7. **Brook mutabakat %135 farkı** (banka 303K vs muhasebe 129K) veri tarafında hâlâ açık — otomasyon değil, muhasebe aksiyonu gerekiyor

## Doğrulama

- `python3 -m py_compile` → 5 dosya temiz
- `hotel_data.py` seed → 7 otel / 819 oda / 19 personel üretildi
- Bkz. commit diff — davranış değişiklikleri: TEKNIK routing (130→131), LINE imzasız istek reddi

---

# 🔄 v2 Güncellemesi (aynı gün — Leb kararıyla mimari değişti)

Leb'in kararları: **LINE kaldırıldı** (her şey Telegram içinde), **tek AI = Sonnet 5**
ve **ücretsiz** çalışacak (abonelik üzerinden), **input dosyası hangi topic'e atılırsa
çıktı o departmana göre** hazırlanacak.

## Yapılanlar

1. **`telegram-bot/lato_telegram_bot.py`** (YENİ — ana sistem): long-polling bot;
   topic→departman eşleme (130-135); md/txt/csv inline, foto/pdf dosya olarak Sonnet 5'e;
   departman bağlamı (README + dil paketi + şablonlar + spec) otomatik yüklenir;
   çıktı JSON şemasıyla alınır → cevap topic'e, kalıcı kayıt `departmanlar/<slug>/...`
   altına yazılır (path traversal korumalı, üzerine yazma yok, tek worker kuyruğu)
2. **`telegram-bot/claude_client.py`** (YENİ): tek model Sonnet 5 — sıra:
   `claude` CLI (abonelik, **token ücreti YOK**) → Anthropic API → OpenRouter (ikisi de
   opsiyonel ücretli fallback). Vision/pdf desteği her katmanda.
3. **Otomasyon modülleri** OpenRouter'dan koparıldı → ortak istemciye bağlandı
   (`automation_engine.py`, `competitor_monitor.py`); AI kanalı yoksa bültenler
   AI önerisiz gider, çökmez (test edildi).
4. **Çeviri motoru**: önce claude CLI (ücretsiz), yoksa OpenRouter fallback (yine Sonnet 5).
5. **LINE bot DEPRECATED**: `line-bot/` arşiv; kod ve README'ye uyarı bantları kondu,
   KURULUM'dan çıkarıldı. Gemini OCR bağımlılığı kalktı (fatura okuma artık Sonnet 5 vision).

## Offline test sonuçları

- Fake `claude` binary ile uçtan uca: CLI çağrısı → JSON parse → `departmanlar/`
  altına kayıt ✅ | traversal saldırı yolları reddedildi ✅ | bağlam yükleme ✅ |
  fallback zinciri doğru hata veriyor ✅ | syntax 7 dosya temiz ✅

## Kalan riskler / notlar

- "Ücretsiz" = Claude Pro/Max kotası; yoğun günde limit dolarsa bot bekletir/uyarır
- CLI çağrısı başına ~2-5s gecikme (çeviri için not edildi; `LATO_TRANSLATE_MODEL` ile ayrılabilir)
- Sunucuda tek seferlik `claude setup-token` gerekli (KURULUM §1)
- Webhook yok → getUpdates polling: aynı token'ı başka poller kullanıyorsa 409 çatışır
  (@Latotry_bot'u Hermes de dinliyorsa token ayrıştırılmalı — LATO_BOT_TOKEN olarak yeni bot açılabilir)
