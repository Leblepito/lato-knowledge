#!/usr/bin/env python3
"""STT Engine — faster-whisper ile sesli mesaj transkripsiyonu + dil tespiti."""
import logging
import re
from faster_whisper import WhisperModel
import config

logger = logging.getLogger(__name__)
_model = None

# Whisper "initial_prompt" — Türkçe otel/havuz/elektrik kelime hazinesi
# Whisper'a bağlam verir, yanlış duymayı azaltır
TURKISH_PROMPT = (
    "Phuket otel elektrik havuz klima motor pompa pano sigorta rezistans "
    "trafo jeneratör kompanzasyon topraklama kaçak akım röleşi şalter "
    "oda banyo tuvalet sıcak soğuk su tesisat musluk vana boru "
    "resepsiyon misafir müşteri kahvaltı mutfak çamaşır temizlik "
    "çalışıyor çalışmıyor bozuk arıza tamir kontrol bakım "
    "şı çı ği İ Ş Ç Ğ Ö Ü "
    "acil lütfen yardım haber ver haber verir haber çalış çalışır çalışırsan"
)

THAI_PROMPT = (
    "โรงแรม สระว่ายน้ำ ไฟฟ้า แอร์ ห้อง น้ำ ส้วม พัดลม "
    "เต้ารับ เบรกเกอร์ รั่ว ซ่อม ด่วน ช่วยด้วย"
)


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info(f"Loading whisper model: {config.WHISPER_MODEL_SIZE}")
        _model = WhisperModel(
            config.WHISPER_MODEL_SIZE,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper model loaded.")
    return _model


def _normalize_turkish(text: str) -> str:
    """
    Whisper'ın sık yaptığı Türkçe karakter hatalarını düzeltir.
    Kelime + bigram + bağlam tabanlı düzeltme.
    """
    # Önce metni koru, küçük harfe çevir
    text_lower = text.lower()

    # ── 1. Tek kelime düzeltmeleri ───────────────────────
    word_fixes = {
        # Fiiller
        "calismiyor": "çalışmıyor", "calisiyor": "çalışıyor",
        "calismiyorsa": "çalışmıyorsa", "calisirsan": "çalışırsan",
        "calisirsa": "çalışırsa", "calistir": "çalıştır",
        "calisirma": "çalıştırma", "calisan": "çalışan",
        "calisanlar": "çalışanlar", "calismali": "çalışmalı",
        "calismak": "çalışmak", "calistim": "çalıştım",
        "calistik": "çalıştık", "calissin": "çalışsın",
        "cakisiyor": "çakışıyor",
        # Isı/sıcaklık
        "soguk": "soğuk", "sogutma": "soğutma",
        "sogutmuyor": "soğutmuyor", "sogutuyor": "soğutuyor",
        "sogutmaz": "soğutmaz", "soguklugunda": "soğukluğunda",
        "isiyor": "ısıyor", "isiniyor": "ısınıyor",
        "isinmiyor": "ısınmıyor", "isinirsa": "ısınırsa",
        "isiyorsa": "ısıyorsa", "isitmiyor": "ısıtmıyor",
        "isitiyor": "ısıtıyor",
        # Görüş/gönderme
        "gorunmuyor": "görünmüyor", "gorunuyor": "görünüyor",
        "goruyor": "görüyor", "gordum": "gördüm",
        "gormus": "görmüş", "gormuyor": "görmüyor",
        "gonder": "gönder", "gonderiyor": "gönderiyor",
        "gonderdi": "gönderdi", "gonderirim": "gönderirim",
        "gonderir": "gönderir", "gondermem": "göndermem",
        "gondereyim": "göndereyim", "gondermeli": "göndermeli",
        # Zamirler/edatlar
        "bugun": "bugün", "dun": "dün", "yarin": "yarın",
        "degil": "değil", "degilse": "değilse",
        "gerekiyor": "gerekiyor", "gerekli": "gerekli",
        # Kısaltmalar
        "kisa": "kısa", "kisaltma": "kısaltma",
        "kismi": "kısmi", "kirik": "kırık",
        "kirildi": "kırıldı", "kiriyor": "kırıyor",
        # Güzel/özür/öneri
        "guzel": "güzel", "guzelde": "güzelse",
        "ozur": "özür", "oneri": "öneri",
        "olmek": "ölmek", "ortmek": "örtmek",
        "ortusu": "örtüsü",
        # Üzerine
        "uzerine": "üzerine", "uzerinde": "üzerinde",
        "uzere": "üzerine", "uzun": "uzun",
        # Lütfen/yardım
        "lutfen": "lütfen", "yardim": "yardım",
        "tesekkur": "teşekkür", "tesekkurler": "teşekkürler",
        # Yapmak/vermek
        "yapmiyor": "yapmıyor", "yapiyor": "yapıyor",
        "verecegim": "vereceğim", "yapacagim": "yapacağım",
        # Miş/mış
        "atmis": "atmış", "atmistir": "atmıştır",
        "durmus": "durmış", "koymus": "koymuş",
        "vermis": "vermiş", "gormus": "görmüş",
        # Sigorta/pano
        "sigortasi": "sigortası", "sigortasinda": "sigortasında",
        "panosu": "panosu", "panosunda": "panosunda",
        "panonun": "panonun",
        # Pompa/motor
        "pompasi": "pompası", "moturu": "motoru",
        "klimasi": "kliması", "klimayi": "klimayı",
        "klimada": "klimada",
        # Oda
        "odasi": "odası", "odanin": "odanın",
        "odaya": "odaya", "odada": "odada",
        # Diğer
        "respsiyon": "resepsiyon", "misafir": "misafir",
        "kacak": "kaçak", "kaciyor": "kaçıyor",
        "akimiyor": "akmıyor", "akmiyor": "akmıyor",
        "akitiyor": "akıtıyor", "akitmiyor": "akıtmıyor",
        "damliyor": "damlıyor", "damlatiyor": "damlatıyor",
        "sesvar": "ses var", "sesyok": "ses yok",
        "suyok": "su yok", "suvaryok": "su var yok",
    }

    for wrong, right in word_fixes.items():
        pattern = r'\b' + re.escape(wrong) + r'\b'
        text_lower = re.sub(pattern, right, text_lower, flags=re.IGNORECASE)

    # ── 2. Bigram (iki kelime) düzeltmeleri ──────────────
    bigram_fixes = {
        "sigorta atmis": "sigorta atmış",
        "sigorta atti": "sigorta attı",
        "sigorta atar": "sigorta atar",
        "su damliyor": "su damlıyor",
        "su akiyor": "su akıyor",
        "su gelmiyor": "su gelmiyor",
        "su yok": "su yok",
        "haber ver": "haber ver",
        "haber verir": "haber verir",
        "haber vereyim": "haber vereyim",
        "oda da": "odada",   # Whisper "odada" → "oda da" hatası
        "oda nin": "odanın",
        "oda ya": "odaya",
        "oda larin": "odaların",
        "pano da": "panoda",
        "havuz da": "havuzda",
        "banyo da": "banyoda",
        "mutfak ta": "mutfakta",
        "resepsiyon da": "resepsiyonda",
    }

    for wrong, right in bigram_fixes.items():
        text_lower = text_lower.replace(wrong, right)

    # ── 3. Üç kelime kalıpları ──────────────────────────
    trigram_fixes = {
        "oda da calisirsan": "odada çalışırsan",
        "oda da calisiyorsan": "odada çalışıyorsan",
        "pano da sigorta": "panoda sigorta",
        "havuz motoru calismiyor": "havuz motoru çalışmıyor",
        "klima sogutmuyor": "klima soğutmuyor",
    }

    for wrong, right in trigram_fixes.items():
        text_lower = text_lower.replace(wrong, right)

    # ── 4. Genel Türkçe karakter geri-yükleme ───────────
    # Whisper bazen c→ç, s→ş, g→ğ, o→ö, u→ü dönüşümünü atlar
    # Kelime sonu şahıs ekleri
    suffix_fixes = {
        r'\bacak\b': 'acak',   # correct
        r'\bcek\b': 'çek',
        r'\bci\b': 'cı',      # hacı vs
    }

    # ── 5. İlk harfi büyüt ──────────────────────────────
    if text_lower:
        text_lower = text_lower[0].upper() + text_lower[1:]

    return text_lower


def transcribe(audio_path: str, language_hint: str = None) -> dict:
    """
    Transcribe audio file → {text, language, probability}.

    Args:
        audio_path: Path to audio file (ogg/mp3/wav).
        language_hint: Bilinen dil ('tr', 'th', 'en') veya None (oto tespit).

    Returns:
        dict: {"text": str, "language": str, "probability": float}
    """
    model = get_model()

    # Choose initial_prompt based on hint or auto-detect
    if language_hint == "tr":
        prompt = TURKISH_PROMPT
        lang_param = "tr"
    elif language_hint == "th":
        prompt = THAI_PROMPT
        lang_param = "th"
    elif language_hint == "en":
        prompt = None
        lang_param = "en"
    else:
        prompt = TURKISH_PROMPT  # Default prompt helps mixed TR/EN
        lang_param = None  # auto-detect

    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=lang_param,
        initial_prompt=prompt,
        condition_on_previous_text=False,  # hallucination önler
        vad_filter=True,  # sessizlik bölümlerini atla
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    lang = info.language if info.language in config.ACTIVE_LANGUAGES else "en"

    # Türkçe karakter normalizasyonu
    if lang == "tr":
        text = _normalize_turkish(text)

    return {
        "text": text,
        "language": lang,
        "probability": round(info.language_probability, 3),
    }
