# Lato Knowledge Base

> **Lato Elektrik Danışman** — Phuket, Tayland'da 7 otel için danışman asistan
> **Pilot**: The Brook Pool Resort (31 oda) | **Toplam**: 7 otel, 819 oda

Bu repo, Lato otelleri için **versiyonlanmış, audit-trail'li, uzun vadeli bilgi bankası**dır.

## 📂 Klasör Yapısı

| Klasör | Ne | Kullanım |
|---|---|---|
| `oteller/` | Her otel için detay data file (slug bazlı) | `brook-pool-resort.md` pilot; diğer 6 placeholder |
| `ekipman/` | Trafo, jeneratör, pano, pompa, kablo envanteri | Marka, model, kVA, kW, yaş, son bakım |
| `hesaplar/` | Hesap defteri (kablo kesiti, gerilim düşümü, kısa devre, kompanzasyon) | `YYYY/AY/<konu>.md` |
| `olaylar/` | Arıza, müdahale, denetim kaydı | `YYYY/AY/GG-konu.md` |
| `kisiler/` | Baş mühendis, teknisyen, tedarikçi kontak | `<isim>-<rol>.md` |
| `spec/` | Standartlar, kabul kriterleri, hesap yöntemleri | Konu bazlı markdown |
| `planlar/` | Proje planları, sprint'ler, TODO | `<plan-adi>.md` |
| `audit/` | Değişiklik logu, commit geçmişi özetleri | `change-log.md` |

## 🤖 Bot Erişimi

Bu repo'ya yazan: **Lato Hermes** (`@Latotry_bot`, lato profili)
Bu repo'dan okuyan: lato session'daki agent, Brook Pool sorguları, hesap doğrulama

## 🔐 Erişim

- **Private repo**: Leblepito/lato-knowledge
- **Token**: GitHub PAT (`lato-knowledge`, 90 gün geçerli, `repo` scope)
- **Rotation**: Token süresi dolunca yenisini üretip `lato/.env`'e yaz

## 📜 Versiyon

- **v1.0.0** (2026-06-08): İlk kurulum. Brook Pool pilot. 7 otel data file sync.
- Lato profil: `~/.hermes/profiles/lato/`
- Notion workspace: (eş zamanlı çalışır, Lato sayfası + 6 veritabanı)
- Cross-reference: `lato-otel/<slug>.md` ↔ `oteller/<slug>.md` ↔ Notion Oteller DB
