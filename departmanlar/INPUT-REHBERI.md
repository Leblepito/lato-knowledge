# 📥 Departman Input Dosyaları — Yapılış Rehberi

> Otel departmanlarından (özellikle **teknik ekip**) gelen bilgilerin bilgi bankasına
> nasıl input dosyası olarak işleneceğini adım adım anlatır.
> **Kısa yol**: input dosyasını doğrudan ilgili Telegram topic'ine at —
> bot (Sonnet 5) departmana göre çıktıyı hazırlar ve kaydeder (bkz. §5-A).
> Bot cevap verirken bu dosyaları kaynak olarak kullanır —
> **dosya yoksa "TBD — saha doğrulaması gerekli" der, uydurmaz.**

## 1. Şema — Üç Dosya Tipi

Her departman klasörü aynı şemayı kullanır:

```
departmanlar/<departman-slug>/
├── olaylar/YYYY/AY/GG-konu.md      → arıza, müdahale, denetim kaydı
├── hesaplar/YYYY/AY/<konu>.md      → teknik hesap (kablo kesiti, debi, yük...)
└── envanter/<ekipman>.md           → ekipman kartı (marka, model, yaş, bakım)
```

| Tip | Ne zaman açılır | Adlandırma | Örnek |
|---|---|---|---|
| **Olay** | Arıza / müdahale / denetim olduğunda | `olaylar/2026/07/23-havuz-pompa-ariza.md` | Tarih dosya adında |
| **Hesap** | Bir teknik hesap yapıldığında | `hesaplar/2026/07/brook-havuz-debi.md` | Otel + konu |
| **Envanter** | Yeni ekipman kaydı / güncelleme | `envanter/brook-havuz-pompa-1.md` | Otel + ekipman + no |

Departman slug'ları: `elektrik-havuz` (Topic 130), `teknik-bakim` (131), `operasyon` (132),
`satin-alma` (133), `fnb` (134), `it-muhasebe` (135).

**Kural**: Türkçe karaktersiz, küçük harf, tire ile: `23-jenerator-ats-testi.md` ✅ — `23 Jeneratör ATS Testi.md` ❌

## 2. Adım Adım — Olay Dosyası (Teknik Ekip)

Saha personeli LINE/Telegram'a "havuz pompası bozuk" yazdığında süreç:

1. **Şablonu kopyala**: `departmanlar/_sablonlar/olay-sablonu.md`
2. **Doğru yola kaydet**: `departmanlar/elektrik-havuz/olaylar/2026/07/23-brook-havuz-pompa.md`
   (yıl ve ay klasörü yoksa oluştur)
3. **Üst bilgiyi doldur**: tarih, otel slug'ı, bildiren kişi, öncelik (KRITIK/YUKSEK/NORMAL/DUSUK)
4. **Belirtiyi yaz**: personelin bildirdiği ham mesaj + gözlem (foto varsa dosya adıyla referans ver)
5. **Müdahaleyi yaz**: ne yapıldı, kim yaptı, hangi parça kullanıldı
6. **Sonuç + takip**: çözüldü mü, satın alma gerekiyor mu (→ `satin-alma/envanter/satin-alinacaklar.md`'ye satır ekle), sonraki kontrol tarihi
7. **Bilinmeyeni TBD bırak** — tahmin yazma
8. **Commit**: `git add + commit` — mesaj formatı: `olay: brook havuz pompa arıza (2026-07-23)`

## 3. Adım Adım — Envanter Kartı (Teknik Ekip)

Teknik ekipten istenen input: **her cihazın etiket fotoğrafı + aşağıdaki alanlar.**

1. Şablonu kopyala: `_sablonlar/envanter-sablonu.md`
2. `departmanlar/<departman>/envanter/<otel>-<ekipman>-<no>.md` olarak kaydet
3. Etiketten oku ve doldur: **marka, model, seri no, güç (kW/kVA), voltaj/faz, akım, IP sınıfı, üretim yılı**
4. Saha bilgisi ekle: konum (hangi bina/kat/oda), son bakım tarihi, durumu, sorumlu kişi
5. Phuket kontrolü (bkz. `spec/phuket-elektrik-context.md`): dış mekansa IP55+, plaj kenarıysa marine grade, havuz bölgesindeyse SELV/30mA notu düş
6. Okunamayan alan = TBD + "etiket silik, saha doğrulaması gerekli"

## 4. Adım Adım — Hesap Dosyası

1. Şablon: `_sablonlar/hesap-sablonu.md` → `hesaplar/YYYY/AY/<otel>-<konu>.md`
2. **Girdiler** bölümüne tüm varsayımları yaz (kaynağıyla: etiket, ölçüm, TBD)
3. **Formül + adımlar**: hesap adım adım, birimleriyle
4. **Sonuç + karar**: seçilen kesit/pompa/şalter ve gerekçesi
5. **Standart referansı**: TIS / IEC 60364 / TS EN maddesi (`spec/phuket-elektrik-context.md`'den)

## 5. Kullanım — İki Yol

**A) Otomatik (önerilen)** — `telegram-bot/lato_telegram_bot.py` çalışıyorsa:

1. Input dosyasını (md/txt/csv/foto/pdf) **doğrudan ilgili departman topic'ine at**
   — örn. arıza fotoğrafını #131 Teknik Bakım'a
2. Bot (Sonnet 5) departmanı topic'ten anlar, şablona döker, **çıktıyı aynı topic'e yazar**
   ve dosyayı `departmanlar/<slug>/...` altına kaydeder (`💾 kaydedildi: yol` mesajı)
3. Kayıtlar haftalık gözden geçirilip commit edilir (Leb onayı)

**B) Manuel** — bot kapalıysa veya elle düzenleme gerekiyorsa: §2-§4'teki adımlarla
şablondan dosyayı kendin oluştur.

Sorgulama: ilgili topic'te `@Latotry_bot Brook havuz pompası ne durumda?` — bot
`olaylar/`, `envanter/`, `hesaplar/` dosyalarını okur, **kaynak yol belirterek** cevaplar;
dosya yoksa TBD der. **Telegram mesajı arşiv değildir, dosya arşivdir.**

## 6. Kurallar (AGENTS.md ile uyumlu)

1. Her dosyada kaynak belirt (etiket foto, ölçüm, personel bildirimi, fatura)
2. Bilinmeyene TBD yaz — uydurma
3. Dil: Türkçe öncelikli, teknik terim İngilizce serbest
4. Commit'ler Leb onayıyla, `lato-otel-bot` PAT ile
5. Para birimi THB, tarih formatı `YYYY-MM-DD`

## 7. Kurulum

Sistemin sıfırdan kurulumu (sunucu, env, Docker, cron, Telegram/LINE) için: **[`../KURULUM.md`](../KURULUM.md)**

Şablonlar: [`_sablonlar/`](_sablonlar/) — olay, hesap, envanter + doldurulmuş teknik örnek.
