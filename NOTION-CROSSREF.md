# Notion ↔ Repo Cross-Reference

> Bu repo, Lato verilerinin 3 katmanlı hafıza yapısının bir parçası.
> Aynı verinin 3 yerde yaşadığını ve senkron kuralını belgeler.

## 3 Katman

| Katman | Teknoloji | Lokal | Bulut | Erişim |
|---|---|---|---|---|
| **L1** Kısa kalıcı | Markdown dosya | `~/.hermes/profiles/lato/memories/MEMORY.md` | — | Hermes her açılışta okur |
| **L3** Per-otel data | Markdown dosya | `~/.hermes/profiles/lato/lato-otel/<slug>.md` | Bu repo: `oteller/<slug>.md` | Agent, vibecoder, teknisyen |
| **L4** Operasyonel DB | Notion | — | Lato-Hermes sayfası + 6 veritabanı | Bot (`Lato Hermes`) + insan |

## Notion Yapısı

- **Workspace**: "utku uysal's Space" (Utku'nun kişisel)
- **Integration**: "Lato Hermes" (bot)
- **Sayfa**: Lato-Hermes (`37901095-d68e-8013-a371-e11ea99637a9`)
- **Sayfa**: Efloud-u2Algo (`37901095-d68e-813d-b5a1-d7357af38129`) — paralel

### Lato-Hermes altında 6 veritabanı:

| DB | data_source_id | İçerik |
|---|---|---|
| Oteller | `0be8ffcb-b2e8-4fd2-ad1f-3497e26243c0` | 7 otel (Brook Pool pilot + 6 placeholder) |
| Ekipman | `a4c64cdd-2b47-4aa2-9060-ab21ace72b5b` | Trafo, jeneratör, pano, pompa, kablo |
| Hesaplar | `a34a4a4b-97cb-49f7-9f5e-13c3399841e5` | Kablo kesiti, gerilim düşümü, kısa devre, kompanzasyon |
| Olaylar (Lato) | `bad63894-424d-4aa7-86e1-1bd10580b910` | Arıza, müdahale, denetim |
| Kişiler | `70d21f53-d574-4692-8f91-bfe6e727a3e9` | Chief engineer, teknisyen, tedarikçi |
| Planlar | `8742af28-ac8b-4c5f-afbb-a3b143d38bf9` | Proje planları, sprintler |

### Efloud-u2Algo altında 6 veritabanı:

| DB | data_source_id | İçerik |
|---|---|---|
| Pozisyonlar | `de7987a0-0c46-4c2d-9dd1-420c3037066d` | Açık pozisyonlar + v2 shadow sinyalleri |
| İşlemler | `4dd8cc2a-3ce9-4050-b5a5-6b10e0151385` | Kapanmış trade'ler (PnL, süre, setup) |
| PRs | `cfccdebe-2ed8-4adf-975a-c7c106f54f6a` | GitHub PR lifecycle (16 PR) |
| Konfig | `26c2dd30-15f8-4a9a-94b5-722578563b0b` | Config snapshot + değişiklik logu |
| Olaylar (Efloud) | `63dc10ac-4d8a-4656-9d76-07e633c3afa6` | Incident, alert, circuit breaker |
| Notlar | `ca023dd2-866a-4deb-9010-e61ce009e43e` | Serbest notlar (PR review, deploy) |

## Senkron Kuralı

**Yazma önceliği** (her zaman):
1. **Source of truth** = GitHub repo (bu) — versiyonlu, denetim izli
2. Notion DB = operasyonel sorgu için (filter, sort, view)
3. lato-otel/ data file = lokal hızlı erişim
4. MEMORY.md = kalıcı kısa not

**Akış** (yeni veri geldiğinde):
```
Yeni veri → bu repo (commit) → Notion DB (create page) → lato-otel/ (sync) → MEMORY.md (güncelle)
```

**Çakışma durumu**: GitHub en yeni tarih kazanır. Notion değişiklikleri manuel olarak GitHub'a da işlenir.

## API Önemli Not

Notion 2025-09-03 versiyonunda property'ler `database` üzerinde değil, `data_source` üzerinde.

- POST `/v1/databases` → sadece kabuk oluşturur (boş `data_sources` ile)
- PATCH `/v1/data_sources/{id}` → property ekle
- Page oluştururken: `parent: {"data_source_id": "..."}`

## Versiyon

- v1.0.0 (2026-06-08): İlk kurulum, 12 veritabanı, 31 satır veri
