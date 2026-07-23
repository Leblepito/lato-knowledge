#!/usr/bin/env python3
"""
Lato Telegram Bot — departman topic'lerine gelen input dosyalarını Sonnet 5 ile işler.

Akış:
  Personel/yönetici bir departman topic'ine dosya (md/txt/csv/foto/pdf) veya metin atar
    → bot topic'ten departmanı bulur
    → departman bağlamını yükler (README + dil paketi + şablonlar + spec)
    → Claude Sonnet 5 (abonelik üzerinden, ücretsiz) departmana uygun çıktıyı üretir
    → aynı topic'e cevap + (varsa) bilgi bankasına kaydedilecek dosyayı yazar

LINE YOK — her şey Telegram içinde. AI = sadece Claude Sonnet 5 (claude_client.py).

Tetikleme kuralları (gürültü ve kota koruması):
  - Dosya/foto içeren HER mesaj işlenir (caption talimat sayılır)
  - Düz metin sadece bot mention'ı (@...) veya /lato ile başlıyorsa işlenir
  - /help her topic'te kullanım özetini basar

Çalıştırma:
  TELEGRAM_BOT_TOKEN=... python3 lato_telegram_bot.py
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

from claude_client import ask_claude, parse_ai_json, ClaudeError, MODEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("lato-tg")

# ── Config ─────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", os.environ.get("TRANSLATE_BOT_TOKEN", ""))
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
GROUP_ID = int(os.environ.get("LATO_GROUP_ID", "-1003776134843"))

REPO_DIR = Path(os.environ.get("LATO_REPO_DIR", Path(__file__).resolve().parent.parent))
AUTO_SAVE = os.environ.get("LATO_AUTO_SAVE", "1") == "1"   # üretilen dosyayı repoya yaz
WORKDIR = Path(os.environ.get("LATO_WORKDIR", "/tmp/lato-inbox"))
OFFSET_FILE = WORKDIR / "offset.txt"

# ── Git push-back (Railway gibi ephemeral disklerde kalıcılık) ─────
# LATO_GIT_PUSH=1 + GITHUB_TOKEN → her kayıt GitHub'a commit+push edilir.
GIT_PUSH = os.environ.get("LATO_GIT_PUSH", "0") == "1"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_URL = os.environ.get("LATO_REPO_URL", "https://github.com/Leblepito/lato-knowledge.git")
CLONE_DIR = Path(os.environ.get("LATO_CLONE_DIR", "/tmp/lato-repo"))
GIT_BRANCH = os.environ.get("LATO_GIT_BRANCH", "main")


def _auth_url() -> str:
    if GITHUB_TOKEN and REPO_URL.startswith("https://"):
        return REPO_URL.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@", 1)
    return REPO_URL


def _mask(s: str) -> str:
    return s.replace(GITHUB_TOKEN, "***") if GITHUB_TOKEN else s


def _git(*args, timeout: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO_DIR), *args],
                          capture_output=True, text=True, timeout=timeout)


def ensure_repo():
    """GIT_PUSH açıkken her zaman ayrı, token'la klonlanmış temiz bir kopyada çalış.
    (Image içindeki kopya kirli/git'siz olabilir — deterministik davranış için CLONE_DIR.)"""
    global REPO_DIR
    if not GIT_PUSH:
        return
    if (CLONE_DIR / ".git").exists():
        r = subprocess.run(["git", "-C", str(CLONE_DIR), "pull", "--rebase",
                            _auth_url(), GIT_BRANCH],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            logger.warning(f"git pull: {_mask(r.stderr)[:150]}")
    else:
        logger.info(f"Bilgi bankası klonlanıyor → {CLONE_DIR}")
        r = subprocess.run(["git", "clone", "--depth", "50", _auth_url(), str(CLONE_DIR)],
                           capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            logger.error(f"git clone başarısız: {_mask(r.stderr)[:200]} — "
                         f"kayıtlar sadece geçici diske yazılacak (push-back kapalı)")
            return
    REPO_DIR = CLONE_DIR
    logger.info(f"REPO_DIR → {REPO_DIR} (git push-back aktif)")


def git_push_record_sync(rel_path: str) -> bool:
    """Tek kaydı commit'le ve GitHub'a push'la. Başarısızlıkta False (kayıt diskte kalır)."""
    if not (GIT_PUSH and GITHUB_TOKEN):
        return False
    try:
        _git("config", "user.name", "Lato Bot")
        _git("config", "user.email", "lato-bot@users.noreply.github.com")
        _git("add", rel_path)
        c = _git("commit", "-m", f"kayit: {rel_path} (lato-telegram-bot)")
        if c.returncode != 0:
            logger.warning(f"git commit: {_mask(c.stderr or c.stdout)[:150]}")
            return False
        _git("pull", "--rebase", _auth_url(), GIT_BRANCH)
        p = _git("push", _auth_url(), f"HEAD:{GIT_BRANCH}")
        if p.returncode != 0:
            logger.error(f"git push: {_mask(p.stderr)[:200]}")
            return False
        return True
    except Exception as e:
        logger.error(f"git push-back: {_mask(str(e))[:200]}")
        return False

MAX_FILE_MB = 10
MAX_INLINE_CHARS = 30_000       # metin dosyaları prompt'a gömülürken üst sınır
TEXT_EXT = {".md", ".txt", ".csv", ".json", ".log", ".yml", ".yaml"}
BINARY_EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}

# ── Departmanlar (topic → çıktı profili) ───────────────────────────
DEPARTMENTS = {
    130: {
        "slug": "elektrik-havuz", "name": "⚡ Elektrik & Havuz",
        "cikti": ("Girdi arıza bildirimi ise OLAY kaydı, ekipman etiketi/listesi ise ENVANTER kartı, "
                  "ölçüm/boyutlandırma ise HESAP dosyası üret (şablon formatında). "
                  "spec'teki Phuket kurallarına göre uygunluk kontrolü ekle (IP sınıfı, SPD, SELV, "
                  "30mA RCD, topraklama ≤5Ω, marine grade). Malzeme ihtiyacı çıkarsa "
                  "satin-alinacaklar.md formatında satır öner."),
        "spec": True,
    },
    131: {
        "slug": "teknik-bakim", "name": "🔧 Teknik Bakım",
        "cikti": ("Girdi klima/tesisat/bina arızası ise OLAY kaydı, bakım listesi ise BAKIM PLANI, "
                  "cihaz etiketi ise ENVANTER kartı üret (şablon formatında). Dil paketindeki "
                  "terminolojiyi kullan (örn. 'klima bozuk' → 'klima arızalı'). "
                  "Parça ihtiyacı çıkarsa satin-alinacaklar satırı öner."),
        "spec": True,
    },
    132: {
        "slug": "operasyon", "name": "🛎️ Operasyon",
        "cikti": ("Girdi occupancy/vardiya/güvenlik raporu ise ÖZET RAPOR + aksiyon listesi üret. "
                  "Yabancı misafir check-in içeriyorsa TM30 hatırlatması ekle (24 saat, 1,600 THB ceza). "
                  "Kalıcı kayıt gerekiyorsa OLAY dosyası formatında üret."),
        "spec": False,
    },
    133: {
        "slug": "satin-alma", "name": "📦 Satın Alma & Stok",
        "cikti": ("Girdi fatura/dekont fotoğrafı ise: firma, tutar (THB), tarih, fatura no çıkar ve "
                  "kısa mutabakat özeti ver. Teklif/fiyat listesi ise karşılaştırma tablosu üret. "
                  "Alım ihtiyacı ise satin-alinacaklar.md tablo formatında satır(lar) üret "
                  "(kalem, spec, adet, tahmini THB, öncelik, tedarikçi adayı)."),
        "spec": False,
    },
    134: {
        "slug": "fnb", "name": "🍽️ F&B",
        "cikti": ("Girdi sıcaklık logu ise HACCP uygunluk kontrolü yap (soğuk zincir 2-8°C, "
                  "dondurucu ≤-18°C), ihlalleri ve aksiyonları listele. Menü/stok ise özet + "
                  "eksik listesi üret. Kalıcı kayıt gerekiyorsa OLAY dosyası formatında üret."),
        "spec": False,
    },
    135: {
        "slug": "it-muhasebe", "name": "💻 IT & Muhasebe",
        "cikti": ("Girdi banka ekstresi/fatura ise kalem dökümü + mutabakat özeti üret, "
                  "anomalileri işaretle (ör. ortalamadan ±%20 sapma). Ağ/PMS konusu ise "
                  "sorun özeti + adım adım çözüm önerisi ver."),
        "spec": False,
    },
    1: {
        "slug": None, "name": "Genel",
        "cikti": ("Girdiyi analiz et, hangi departmana ait olduğunu söyle ve o departmanın "
                  "formatında çıktı üret. Departman net değilse kısa özet + yönlendirme öner."),
        "spec": False,
    },
}

# ── Bağlam yükleme (repo'dan) ──────────────────────────────────────
def _read_trim(path: Path, limit: int) -> str:
    try:
        t = path.read_text(encoding="utf-8", errors="ignore")
        return t[:limit] + ("\n[... kısaltıldı]" if len(t) > limit else "")
    except OSError:
        return ""

def build_context(dept: dict) -> str:
    """Departman README + dil paketi + şablonlar + (gerekirse) spec."""
    parts = []
    slug = dept["slug"]
    if slug:
        parts.append("## Departman README\n" +
                     _read_trim(REPO_DIR / "departmanlar" / slug / "README.md", 2000))
        parts.append("## Dil Paketi (terminoloji)\n" +
                     _read_trim(REPO_DIR / "departmanlar" / "_dil-paketleri" / slug / "tr.md", 3000))
    if dept.get("spec"):
        parts.append("## Phuket Elektrik Spec\n" +
                     _read_trim(REPO_DIR / "spec" / "phuket-elektrik-context.md", 4000))
    sab = REPO_DIR / "departmanlar" / "_sablonlar"
    for name in ("olay-sablonu.md", "envanter-sablonu.md", "hesap-sablonu.md"):
        parts.append(f"## Şablon: {name}\n" + _read_trim(sab / name, 1500))
    return "\n\n".join(p for p in parts if p.strip())

SYSTEM_PROMPT = """Sen Lato — Phuket'te 7 otel (819 oda) için çalışan departman asistanısın.
Kurallar:
- SADECE Türkçe yaz (teknik terim İngilizce olabilir)
- Bilmediğin değeri UYDURMA — "TBD — saha doğrulaması gerekli" yaz
- Kaynak belirt (girdideki dosya/foto, spec, şablon)
- Telegram Markdown V1 kullan: bold için TEK yıldız *böyle*, çift yıldız YASAK
- Para birimi THB, tarih formatı YYYY-MM-DD

ÇIKTI FORMATI — SADECE şu JSON'u dön (çit/başka metin yazma):
{
  "cevap": "Telegram'a gidecek kısa cevap (max ~1500 karakter, tek yıldız markdown)",
  "dosya": {"yol": "departmanlar/<slug>/olaylar/YYYY/AY/GG-konu.md", "icerik": "tam dosya içeriği"}
}
"dosya" alanı: kalıcı kayıt gerekiyorsa doldur (şablon formatında), gerekmiyorsa null.
"yol" mutlaka departmanlar/ ile başlamalı."""

# ── Telegram API ───────────────────────────────────────────────────
async def tg(method: str, _http_timeout: int = 65, **params):
    """_http_timeout: httpx istemci zaman aşımı (isim çakışmasın diye ayrı) —
    Telegram body'sine 'timeout' (long-poll) göndermek istersen **params ile geç."""
    async with httpx.AsyncClient(timeout=_http_timeout) as c:
        r = await c.post(f"{TG_API}/{method}", json=params)
        data = r.json()
        if not data.get("ok"):
            logger.error(f"TG {method}: {str(data)[:200]}")
        return data

async def send_reply(text: str, thread_id: int, reply_to: int | None = None):
    """Uzun metni böl, Markdown dene, hatada düz metin."""
    chunks = [text[i:i + 3900] for i in range(0, len(text), 3900)] or [""]
    for chunk in chunks:
        params = {"chat_id": GROUP_ID, "message_thread_id": thread_id, "text": chunk,
                  "parse_mode": "Markdown"}
        if reply_to:
            params["reply_to_message_id"] = reply_to
        data = await tg("sendMessage", **params)
        if not data.get("ok"):  # Markdown parse hatası → düz metin
            params.pop("parse_mode", None)
            params["text"] = chunk.replace("*", "").replace("_", "").replace("`", "")
            await tg("sendMessage", **params)
        reply_to = None  # sadece ilk parça reply olsun

async def download_file(file_id: str, dest: Path) -> Path | None:
    info = await tg("getFile", file_id=file_id)
    fp = info.get("result", {}).get("file_path")
    if not fp:
        return None
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}")
        if r.status_code != 200:
            return None
        dest.write_bytes(r.content)
        return dest

# ── Kayıt (bilgi bankasına yazma) ──────────────────────────────────
def safe_repo_path(rel: str) -> Path | None:
    """Path traversal koruması: sadece departmanlar/ altına yazılır."""
    rel = (rel or "").strip().lstrip("/").replace("\\", "/")
    if not rel.startswith("departmanlar/") or ".." in rel.split("/"):
        return None
    p = (REPO_DIR / rel).resolve()
    if not str(p).startswith(str(REPO_DIR.resolve()) + os.sep):
        return None
    return p

def save_output_file(dosya: dict) -> str | None:
    yol, icerik = dosya.get("yol"), dosya.get("icerik")
    if not yol or not icerik:
        return None
    p = safe_repo_path(yol)
    if not p:
        logger.warning(f"Güvensiz yol reddedildi: {yol}")
        return None
    if p.exists():  # üzerine yazma — benzersizleştir
        p = p.with_name(f"{p.stem}-{datetime.now().strftime('%H%M%S')}{p.suffix}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(icerik, encoding="utf-8")
    return str(p.relative_to(REPO_DIR))

# ── Mesaj işleme ───────────────────────────────────────────────────
HELP_TEXT = """🤖 *Lato Departman Asistanı* (Sonnet 5)

Bu topic'e *input dosyası* at, departmana göre çıktı hazırlayayım:
• 📄 .md / .txt / .csv → analiz + şablona dökülmüş kayıt
• 📸 foto (etiket, fatura, arıza) → okuma + kayıt/mutabakat
• 📕 pdf → özet + kayıt
• Yazı ile soru: mesaja @mention ekle veya `/lato soru...`

Üretilen kalıcı kayıtlar bilgi bankasına yazılır (departmanlar/...).
Şablonlar: departmanlar/_sablonlar/ | Rehber: departmanlar/INPUT-REHBERI.md"""

async def process_message(msg: dict, bot_username: str):
    thread_id = msg.get("message_thread_id", 1)
    dept = DEPARTMENTS.get(thread_id)
    if dept is None:
        return  # tanımsız topic (örn. #146 çeviri botuna ait)

    text = msg.get("text") or ""
    caption = msg.get("caption") or ""
    msg_id = msg.get("message_id")
    user = (msg.get("from") or {}).get("first_name", "?")

    # /help — /start
    if text.split("@")[0].strip() in ("/help", "/start"):
        await send_reply(HELP_TEXT, thread_id, msg_id)
        return

    # Girdi topla
    files: list[str] = []
    inline_docs: list[str] = []
    WORKDIR.mkdir(parents=True, exist_ok=True)

    doc = msg.get("document")
    if doc:
        if doc.get("file_size", 0) > MAX_FILE_MB * 1024 * 1024:
            await send_reply(f"⚠️ Dosya çok büyük (limit {MAX_FILE_MB}MB).", thread_id, msg_id)
            return
        fname = doc.get("file_name", "dosya")
        ext = Path(fname).suffix.lower()
        dest = WORKDIR / f"{msg_id}-{Path(fname).name}"
        saved = await download_file(doc["file_id"], dest)
        if not saved:
            await send_reply("⚠️ Dosya indirilemedi, tekrar dener misin?", thread_id, msg_id)
            return
        if ext in TEXT_EXT:
            content = saved.read_text(encoding="utf-8", errors="ignore")[:MAX_INLINE_CHARS]
            inline_docs.append(f"### Girdi dosyası: {fname}\n```\n{content}\n```")
        elif ext in BINARY_EXT:
            files.append(str(saved))
        else:
            await send_reply(f"⚠️ {ext} şimdilik desteklenmiyor. "
                             f"Desteklenen: md, txt, csv, jpg/png, pdf", thread_id, msg_id)
            return

    photos = msg.get("photo")
    if photos:  # en büyük çözünürlük
        best = max(photos, key=lambda p: p.get("file_size", 0))
        dest = WORKDIR / f"{msg_id}-foto.jpg"
        saved = await download_file(best["file_id"], dest)
        if saved:
            files.append(str(saved))

    has_input = bool(files or inline_docs)
    mention = f"@{bot_username}".lower()
    is_command = text.lower().startswith("/lato")
    is_mention = mention in text.lower()

    # Tetikleme kuralı
    if not has_input and not (is_command or is_mention):
        return
    instruction = (caption or text).replace(f"@{bot_username}", "").strip()
    if is_command:
        instruction = instruction[5:].strip()

    logger.info(f"📥 {dept['name']} | {user} | dosya={len(files)+len(inline_docs)} | '{instruction[:50]}'")
    await tg("sendChatAction", chat_id=GROUP_ID, message_thread_id=thread_id, action="typing", _http_timeout=10)

    # Prompt kur
    prompt_parts = [
        f"# Departman: {dept['name']} (Telegram topic #{thread_id})",
        f"# Gönderen: {user} | Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"# Bu departman için çıktı talimatı:\n{dept['cikti']}",
        "",
        "# Departman bağlamı:",
        build_context(dept),
    ]
    if inline_docs:
        prompt_parts += [""] + inline_docs
    if instruction:
        prompt_parts += ["", f"# Kullanıcının talimatı/mesajı:\n{instruction}"]
    if not has_input:
        prompt_parts += ["", "# Not: Dosya yok — sadece soruya cevap ver, dosya null olabilir."]

    try:
        raw = await ask_claude("\n".join(prompt_parts), system=SYSTEM_PROMPT,
                               files=files or None, cwd=str(WORKDIR))
        result = parse_ai_json(raw)
    except ClaudeError as e:
        logger.error(f"Claude: {e}")
        await send_reply("⚠️ Sonnet 5'e ulaşılamadı. Sunucuda `claude setup-token` "
                         "girişini kontrol et (bkz. KURULUM.md §2).", thread_id, msg_id)
        return
    except (json.JSONDecodeError, ValueError):
        # JSON gelmedi — ham cevabı ilet
        await send_reply(raw[:3900], thread_id, msg_id)
        return

    cevap = result.get("cevap") or "✅ İşlendi."
    dosya = result.get("dosya")
    if isinstance(dosya, dict) and AUTO_SAVE:
        saved_rel = save_output_file(dosya)
        if saved_rel:
            cevap += f"\n\n💾 Bilgi bankasına kaydedildi: `{saved_rel}`"
            if GIT_PUSH:
                pushed = await asyncio.to_thread(git_push_record_sync, saved_rel)
                cevap += " ☁️ GitHub'a push edildi" if pushed \
                         else " ⚠️ (GitHub push başarısız — log'a bak)"
        elif dosya.get("yol"):
            cevap += f"\n\n⚠️ Dosya kaydedilemedi (geçersiz yol): {dosya.get('yol')}"
    elif isinstance(dosya, dict) and not AUTO_SAVE:
        cevap += f"\n\n📄 Önerilen kayıt yolu: `{dosya.get('yol')}` (AUTO_SAVE kapalı)"

    await send_reply(cevap, thread_id, msg_id)

    # Geçici dosyaları temizle
    for f in files:
        try:
            os.unlink(f)
        except OSError:
            pass

# ── Gömülü cron (Railway'de ayrı servis gerekmesin) ────────────────
# LATO_CRON=1 (varsayılan): otomasyon bültenleri bot süreci içinde zamanlanır.
CRON_ON = os.environ.get("LATO_CRON", "1") == "1"
CRON_TABLE = [
    # (saat, dakika, günler(None=her gün, 0=Pzt), modüller) — Asia/Bangkok saati
    (8, 0, None, ["briefing"]),
    (9, 0, None, ["wp", "tm30", "bureaucratic"]),
    (10, 0, [0], ["financial", "electricity", "reconciliation"]),   # Pazartesi
    (7, 0, [0, 3], ["competitor"]),                                  # Pzt + Perşembe
]

async def cron_scheduler():
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Bangkok")
    except Exception:
        tz = None
        logger.warning("zoneinfo yok — cron sunucu saatine göre çalışır (TZ=Asia/Bangkok ayarla)")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "otomasyon-modulleri"))
    done: set = set()
    logger.info(f"⏰ Gömülü cron aktif — {len(CRON_TABLE)} zamanlama (Asia/Bangkok)")
    while True:
        now = datetime.now(tz) if tz else datetime.now()
        for hour, minute, days, mods in CRON_TABLE:
            if now.hour != hour or now.minute != minute:
                continue
            if days is not None and now.weekday() not in days:
                continue
            key = (now.strftime("%Y-%m-%d"), hour, minute)
            if key in done:
                continue
            done.add(key)
            logger.info(f"⏰ Cron tetiklendi: {mods}")
            for m in mods:
                try:
                    if m == "competitor":
                        from competitor_monitor import run_competitor_scan
                        await run_competitor_scan()
                    else:
                        from automation_engine import run_module
                        await run_module(m)
                except Exception as e:
                    logger.error(f"cron {m}: {e}")
        if len(done) > 500:
            done = set(sorted(done)[-100:])
        await asyncio.sleep(30)


# ── Ana döngü (long polling) ───────────────────────────────────────
def load_offset() -> int:
    try:
        return int(OFFSET_FILE.read_text().strip())
    except (OSError, ValueError):
        return 0

def save_offset(offset: int):
    WORKDIR.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset))

async def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN tanımsız — çıkılıyor")
        sys.exit(1)

    ensure_repo()  # Railway/ephemeral disk: git push-back için gerçek klon garantile

    me = await tg("getMe", _http_timeout=15)
    bot_username = me.get("result", {}).get("username", "Latotry_bot")
    logger.info(f"🚀 Lato Telegram Bot aktif — @{bot_username} | model={MODEL} | "
                f"repo={REPO_DIR} | auto_save={AUTO_SAVE} | git_push={GIT_PUSH}")

    offset = load_offset()
    queue: asyncio.Queue = asyncio.Queue()

    async def worker():
        """Mesajları sırayla işle (paralel CLI çağrısı yığılmasın)."""
        while True:
            m = await queue.get()
            try:
                await process_message(m, bot_username)
            except Exception as e:
                logger.exception(f"process_message: {e}")
            finally:
                queue.task_done()

    asyncio.create_task(worker())
    if CRON_ON:
        asyncio.create_task(cron_scheduler())

    while True:
        try:
            data = await tg("getUpdates", offset=offset, timeout=50,
                            allowed_updates=["message"], _http_timeout=65)
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                save_offset(offset)
                m = upd.get("message")
                if not m:
                    continue
                if m.get("chat", {}).get("id") != GROUP_ID:
                    continue
                if (m.get("from") or {}).get("is_bot"):
                    continue  # kendi mesajlarımız / diğer botlar → loop koruması
                await queue.put(m)
        except Exception as e:
            logger.error(f"poll: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
