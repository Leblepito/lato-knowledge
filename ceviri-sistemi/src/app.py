#!/usr/bin/env python3
"""
Lato Unified Çeviri Server — PTT WebSocket + Telegram Bot.
Tek port (8088): HTTP (/) + WebSocket (/ws) + Telegram polling.
"""
import asyncio
import base64
import json
import logging
import os
import sys
import tempfile
import time
import wave
from pathlib import Path

import httpx
from aiohttp import web, WSMsgType

import config
from stt_engine import transcribe
from translation_engine import translate_text, detect_language_simple
from tts_engine import synthesize
from voice_registry import (
    identify_speaker, register_speaker, get_voice_id,
    get_speaker_gender, get_speaker_by_telegram_id, list_speakers,
)
from accent_memory import apply_corrections, add_correction

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("lato-translate")

# ── Config ─────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TRANSLATE_BOT_TOKEN", "")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
GROUP_CHAT_ID = config.GROUP_CHAT_ID
TOPIC_ID = config.TRANSLATION_TOPIC_ID
HTTP_PORT = 8088
ADMIN_USER_IDS = {6756699467}
pending_registrations = {}
# Corrections log path
CORRECTIONS_LOG = Path("/app/data/corrections_log.json")
if not CORRECTIONS_LOG.exists():
    CORRECTIONS_LOG.write_text("[]", encoding="utf-8")

if not BOT_TOKEN:
    logger.error("❌ TRANSLATE_BOT_TOKEN yok!")
    sys.exit(1)

# Pre-load Whisper
logger.info("⏳ Whisper yükleniyor...")
from stt_engine import get_model as _gw
_gw()
logger.info("✅ Whisper hazır")

FLAG = {"th": "🇹🇭", "tr": "🇹🇷", "en": "🇬🇧"}
LNAME = {"th": "Tayca", "tr": "Türkçe", "en": "English"}


# ── Telegram API ──────────────────────────────────────────────────
async def tg(method, **kwargs):
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{API_BASE}/{method}", json=kwargs)
        return r.json()

async def tg_upload(method, fields, file_field, file_path):
    async with httpx.AsyncClient(timeout=120) as c:
        with open(file_path, "rb") as f:
            files = {file_field: (os.path.basename(file_path), f, "audio/ogg")}
            r = await c.post(f"{API_BASE}/{method}", data=fields, files=files)
            return r.json()

async def download_file(file_id):
    result = await tg("getFile", file_id=file_id)
    fp = result["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
    tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False, dir="/tmp")
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(url)
        tmp.write(r.content)
    tmp.close()
    return tmp.name


# ── Pipeline ──────────────────────────────────────────────────────
async def do_translate(original, source_lang, sender_name="Konuşmacı",
                       speaker_name=None, apply_accent=False):
    # Accent düzeltme
    if apply_accent and speaker_name:
        original = apply_corrections(original, speaker_name)

    targets = [l for l in config.ACTIVE_LANGUAGES if l != source_lang]
    translations = translate_text(original, source_lang, targets, speaker_name)
    return {"original": original, "source_lang": source_lang,
            "translations": translations, "sender_name": sender_name,
            "speaker_name": speaker_name}

def build_text(result, elapsed=0):
    sl = result["source_lang"]
    display_name = result.get("speaker_name") or result["sender_name"]
    badge = ""
    sp = result.get("speaker_name")
    if sp and sp != result["sender_name"]:
        badge = f" 👤{sp}"
    lines = [f"🗣 **{display_name}**{badge}  {FLAG.get(sl,'🗣')} {LNAME.get(sl,sl)}:",
             result["original"], ""]
    for l, t in result["translations"].items():
        if t:
            lines += [f"{FLAG[l]} **{LNAME[l]}**:", t, ""]
    if elapsed:
        lines.append(f"⏱ {elapsed:.1f}s")
    return "\n".join(lines).strip()

async def send_tts(result, thread_id):
    speaker_name = result.get("speaker_name")
    voice_id = get_voice_id(speaker_name) if speaker_name else None
    for l, t in result["translations"].items():
        if not t:
            continue
        try:
            ogg = synthesize(t, voice_id=voice_id, language=l, speaker_name=speaker_name)
            await tg_upload("sendVoice",
                fields={"chat_id": str(GROUP_CHAT_ID),
                        "message_thread_id": str(thread_id),
                        "caption": f"{FLAG[l]} {LNAME[l]}"},
                file_field="voice", file_path=ogg)
        except Exception as e:
            logger.error(f"TTS [{l}]: {e}")


# ── Corrections logging ─────────────────────────────────────────
async def _log_correction(speaker, wrong, right):
    """Log correction to JSON file (persisted in volume)."""
    try:
        import json
        entry = {
            "speaker": speaker,
            "wrong": wrong,
            "right": right,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        data = json.loads(CORRECTIONS_LOG.read_text("utf-8"))
        data.append(entry)
        CORRECTIONS_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        logger.info(f"📝 Correction logged: {wrong} → {right} ({speaker})")
    except Exception as e:
        logger.error(f"Log correction: {e}")

async def run_whisper(audio_path, lang_hint=None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, transcribe, audio_path, lang_hint)


# ── WAV helper ────────────────────────────────────────────────────
def chunks_to_wav(chunks):
    if not chunks:
        return None
    all_data = b"".join(chunks)
    if len(all_data) < 3200:  # < 0.1s
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp")
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(all_data)
    tmp.close()
    return tmp.name


# ── PTT HTML (v3 — Google Translate style, HTTP POST + SSE, no WebSocket) ──
PTT_HTML = r"""<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>🌐 Lato Çeviri</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0e1621;color:#e8e8e8;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
.header{background:#1a2837;padding:10px 16px;text-align:center;border-bottom:1px solid #2a3a4a;flex-shrink:0}
.header h1{font-size:15px;font-weight:600}
.header .sub{font-size:11px;color:#6ab2f2}
#translation-box{flex:1;overflow-y:auto;padding:12px 16px;display:flex;flex-direction:column;gap:8px;min-height:0}
.msg-block{background:#1a2837;border-radius:10px;padding:12px;border-left:3px solid #6ab2f2;animation:fadeIn .2s}
.msg-block .lang-label{font-size:10px;color:#6ab2f2;margin-bottom:3px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.msg-block .text{font-size:14px;line-height:1.5;word-wrap:break-word}
.msg-block.partial{opacity:.85;border-left-color:#ff9800}
.msg-block.partial .lang-label{color:#ff9800}
#status-bar{padding:6px 16px;text-align:center;font-size:12px;color:#6ab2f2;min-height:28px;flex-shrink:0}
#input-area{background:#1a2837;border-top:1px solid #2a3a4a;padding:8px 12px 16px;flex-shrink:0;display:flex;flex-direction:column;gap:8px}
#text-input{width:100%;padding:12px 16px;border-radius:24px;border:1px solid #3a4a5a;background:#0e1621;color:#e8e8e8;font-size:15px;outline:none;transition:border-color .2s}
#text-input:focus{border-color:#6ab2f2}
#text-input::placeholder{color:#5a6a7a}
.voice-row{display:flex;align-items:center;gap:12px}
#ptt-btn{flex-shrink:0;width:56px;height:56px;border-radius:50%;border:none;background:#2a5298;color:white;font-size:24px;cursor:pointer;user-select:none;-webkit-user-select:none;touch-action:none;transition:all .15s;box-shadow:0 2px 8px rgba(0,80,200,.3);display:flex;align-items:center;justify-content:center}
#ptt-btn.recording{background:#d32f2f;transform:scale(1.08);box-shadow:0 0 20px rgba(255,50,50,.5);animation:pulse 1s infinite}
#ptt-btn:active{transform:scale(.92)}
#ptt-btn.disabled{opacity:.4;pointer-events:none}
#voice-status{font-size:12px;color:#8a9aaa;flex:1;min-height:18px}
@keyframes pulse{0%,100%{box-shadow:0 0 12px rgba(255,50,50,.4)}50%{box-shadow:0 0 28px rgba(255,50,50,.7)}}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes spin{to{transform:rotate(360deg)}}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #6ab2f2;border-top-color:transparent;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;margin-right:6px}
</style></head><body>
<div class="header"><h1>🌐 Lato Çeviri</h1><div class="sub">🇹🇷 ↔ 🇹🇭 ↔ 🇬🇧 — Konuş veya yaz, anında çevir</div></div>
<div id="translation-box"><div class="msg-block" style="border-left-color:#555;text-align:center"><div class="text" style="color:#888;font-size:13px">👇 Aşağıya yaz veya mikrofon butonuna bas<br>Çeviri burada canlı görünecek</div></div></div>
<div id="status-bar">Hazır</div>
<div id="input-area">
<input id="text-input" type="text" placeholder="Bir şey yaz veya mikrofonu kullan..." autocomplete="off" enterkeyhint="send">
<div class="voice-row">
<button id="ptt-btn">🎤</button>
<div id="voice-status">Basılı tut ve konuş</div>
</div>
</div>
<script>
const FLAG={tr:'🇹🇷',th:'🇹🇭',en:'🇬🇧'};
const NAME={tr:'Türkçe',th:'Tayca',en:'English'};
const box=document.getElementById('translation-box');
const statusBar=document.getElementById('status-bar');
const btn=document.getElementById('ptt-btn');
const vs=document.getElementById('voice-status');
const inp=document.getElementById('text-input');
let rec=null,ctx=null,isRecording=false,chunks=[],sendInterval=null;

function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}

function showBlock(type,data){
  const el=document.createElement('div');
  el.className='msg-block'+(type==='partial'?' partial':'');
  let h='';
  if(data.original){
    h+=`<div class="lang-label">${FLAG[data.source_lang]||'🗣'} ${NAME[data.source_lang]||data.source_lang}</div>`;
    h+=`<div class="text">${esc(data.original)}</div>`;
  }
  if(data.translations){
    for(const[l,t]of Object.entries(data.translations)){
      if(t){h+=`<div class="lang-label" style="margin-top:5px">${FLAG[l]} ${NAME[l]}</div><div class="text">${esc(t)}</div>`;}
    }
  }
  if(data.note){h+=`<div style="margin-top:4px;font-size:11px;color:#4caf50">${esc(data.note)}</div>`;}
  el.innerHTML=h||'<div class="text">...</div>';
  box.appendChild(el);box.scrollTop=box.scrollHeight;
}

function showSpinner(t){
  vs.innerHTML=`<span class="spinner"></span>${esc(t)}`;
}

// ── Text input (instant translate like Google Translate) ──
let textTimer=null;
inp.addEventListener('input',function(){
  clearTimeout(textTimer);
  const t=this.value.trim();
  if(!t){return;}
  textTimer=setTimeout(()=>{
    fetch('/translate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})})
    .then(r=>r.json()).then(d=>{if(d.ok)showBlock('final',d);})
    .catch(()=>{});
  },400);
});

// ── Voice (PTT via HTTP POST streaming) ──
async function startRec(){
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:{sampleRate:16000,channelCount:1,echoCancellation:true,noiseSuppression:true}});
    ctx=new(window.AudioContext||window.webkitAudioContext)({sampleRate:16000});
    const src=ctx.createMediaStreamSource(stream);
    const proc=ctx.createScriptProcessor(4096,1,1);
    chunks=[];isRecording=true;btn.classList.add('recording');btn.classList.remove('disabled');
    vs.textContent='🔴 Konuşuyor... (çeviri canlı)';
    statusBar.textContent='🔴 Dinleniyor';
    proc.onaudioprocess=e=>{
      if(!isRecording)return;
      const f32=e.inputBuffer.getChannelData(0);
      const i16=new Int16Array(f32.length);
      for(let i=0;i<f32.length;i++){const s=Math.max(-1,Math.min(1,f32[i]));i16[i]=s<0?s*0x8000:s*0x7FFF;}
      chunks.push(i16.buffer);
    };
    src.connect(proc);proc.connect(ctx.destination);
    rec=stream;
    // Start sending audio chunks every 1.5s for partial transcription
    sendAudioLoop();
  }catch(e){vs.textContent='❌ Mikrofon: '+e.message;btn.classList.remove('recording');btn.classList.remove('disabled');}
}

function stopRec(){
  isRecording=false;btn.classList.remove('recording');btn.classList.add('disabled');
  vs.textContent='⏳ İşleniyor...';statusBar.textContent='⏳ Çevriliyor';
  if(sendInterval){clearInterval(sendInterval);sendInterval=null;}
  if(proc){proc.disconnect();proc=null;}
  if(rec){rec.getTracks().forEach(t=>t.stop());rec=null;}
  if(ctx){setTimeout(()=>{ctx.close();ctx=null;},500);}
  // Send final chunk
  sendAudio(true);
}

function sendAudioLoop(){
  if(sendInterval)clearInterval(sendInterval);
  sendInterval=setInterval(()=>sendAudio(false),1500);
}

async function sendAudio(isFinal){
  if(chunks.length===0&&!isFinal)return;
  const audioBlob=new Blob(chunks,{type:'application/octet-stream'});
  if(!isFinal)chunks=[];
  const form=new FormData();
  form.append('audio',audioBlob,'audio.pcm');
  form.append('final',isFinal?'1':'0');
  try{
    const r=await fetch('/voice-translate',{method:'POST',body:form});
    const d=await r.json();
    if(d.ok){
      if(d.partial)showBlock('partial',{original:d.original,source_lang:d.source_lang,translations:d.translations});
      if(d.final){
        box.querySelectorAll('.msg-block.partial').forEach(e=>e.remove());
        showBlock('final',{original:d.original,source_lang:d.source_lang,translations:d.translations,note:'✅ Topic\'e gönderildi'});
        vs.textContent='✅ Tamamlandı';
        statusBar.textContent='Hazır';
        btn.classList.remove('disabled');
      }
    }
  }catch(e){console.error('sendAudio:',e);}
}

function pStart(e){e.preventDefault();if(btn.classList.contains('disabled'))return;startRec();}
function pEnd(e){e.preventDefault();if(!isRecording)return;stopRec();}

btn.addEventListener('touchstart',pStart,{passive:false});
btn.addEventListener('touchend',pEnd,{passive:false});
btn.addEventListener('touchcancel',pEnd,{passive:false});
btn.addEventListener('mousedown',pStart);
btn.addEventListener('mouseup',pEnd);
btn.addEventListener('mouseleave',e=>{if(isRecording)pEnd(e);});
btn.addEventListener('contextmenu',e=>e.preventDefault());
</script></body></html>"""


# ── HTTP handlers (v3 — POST /translate + /voice-translate, no WebSocket) ───
async def http_index(request):
    return web.Response(text=PTT_HTML, content_type="text/html", charset="utf-8")

async def handle_translate(request):
    """POST /translate — text translate (Google Translate style, instant)."""
    try:
        body = await request.json()
        text = body.get("text", "").strip()
        if not text:
            return web.json_response({"ok": False, "error": "empty"}, status=400)

        src = detect_language_simple(text)
        result = await do_translate(text, src, "Kullanıcı")
        return web.json_response({
            "ok": True,
            "original": result["original"],
            "source_lang": result["source_lang"],
            "translations": result["translations"],
        }, dumps=lambda o: json.dumps(o, ensure_ascii=False))
    except Exception as e:
        logger.error(f"Translate: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)

async def handle_voice_translate(request):
    """POST /voice-translate — audio chunk translate (PTT style)."""
    try:
        reader = await request.multipart()
        audio_data = None
        is_final = False

        async for part in reader:
            if part.name == "audio":
                audio_data = await part.read(decode=True)
            elif part.name == "final":
                val = await part.text()
                is_final = val == "1"

        if not audio_data or len(audio_data) < 3200:
            return web.json_response({"ok": False, "error": "too short"}, status=400)

        # Save raw PCM to temp file and convert to WAV
        tmp = tempfile.NamedTemporaryFile(suffix=".pcm", delete=False, dir="/tmp")
        tmp.write(audio_data)
        tmp.close()
        pcm_path = tmp.name

        wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp").name
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-f", "s16le", "-ar", "16000", "-ac", "1",
             "-i", pcm_path, wav_path],
            capture_output=True, timeout=10,
        )
        os.unlink(pcm_path)

        stt = await run_whisper(wav_path)
        os.unlink(wav_path)
        text = stt["text"].strip()

        if not text:
            return web.json_response({"ok": False, "error": "no speech"}, status=400)

        result = await do_translate(text, stt["language"], "Kullanıcı")

        resp = {
            "ok": True,
            "partial": not is_final,
            "final": is_final,
            "original": result["original"],
            "source_lang": result["source_lang"],
            "translations": result["translations"],
        }

        # If final — also post to Telegram topic
        if is_final:
            await tg("sendMessage",
                chat_id=GROUP_CHAT_ID, message_thread_id=TOPIC_ID,
                text=build_text(result, 0))
            asyncio.create_task(send_tts(result, TOPIC_ID))

        return web.json_response(resp, dumps=lambda o: json.dumps(o, ensure_ascii=False))

    except Exception as e:
        logger.error(f"Voice-translate: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)


# ── Telegram voice handler (2-aşamalı: önce metin, sonra ses) ────
async def handle_voice(msg):
    chat_id = msg["chat"]["id"]
    thread_id = msg.get("message_thread_id", TOPIC_ID)
    sender = msg.get("from", {})
    sender_id = sender.get("id", 0)
    sender_name = sender.get("first_name", "?")
    file_id = msg.get("voice", {}).get("file_id")

    t0 = time.time()

    # ── Registration flow ──
    reg = pending_registrations.get(sender_id)
    if reg and time.time() < reg["expires"]:
        try:
            ogg = await download_file(file_id)
            register_speaker(name=reg["name"], audio_path=ogg,
                             telegram_user_id=sender_id, gender=reg["gender"])
            os.unlink(ogg)
            del pending_registrations[sender_id]
            await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
                     text=f"✅ **{reg['name']}** sesi kaydedildi! ({reg['gender']})\n\n"
                          "Artık konuştuğunda otomatik tanınacaksın.\n"
                          "Çeviriler senin ses özelliklerine göre yapılacak.")
            logger.info(f"✅ Speaker registered: {reg['name']}")
        except Exception as e:
            logger.error(f"Registration: {e}")
            await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
                     text=f"❌ Kayıt hatası: {str(e)[:200]}")
        return

    # Cleanup expired
    expired = [uid for uid, r in pending_registrations.items() if time.time() >= r["expires"]]
    for uid in expired:
        del pending_registrations[uid]

    # AŞAMA 0: Hemen "işleniyor" mesajı gönder
    proc_msg = await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
                        text=f"🎧 **{sender_name}** → ⏳ ses işleniyor...")
    msg_id = proc_msg.get("result", {}).get("message_id")
    if not msg_id:
        logger.error("Voice: couldn't get msg_id for processing message")
        return

    try:
        ogg = await download_file(file_id)

        # ── Konuşmacı tanı (paralel değil, voice_registry MFCC) ──
        speaker_name = None
        try:
            speaker_name, conf = identify_speaker(ogg)
            if speaker_name:
                logger.info(f"👤 Speaker: {speaker_name} (conf={conf:.2f})")
            else:
                logger.info(f"👤 Unidentified (best={conf:.2f})")
        except Exception as e:
            logger.warning(f"Speaker ID skipped: {e}")

        # AŞAMA 1: Whisper STT → metni hemen göster (~1-2 sn)
        stt = await run_whisper(ogg)
        original = stt["text"].strip()
        if not original:
            await tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                     text=f"🔇 **{sender_name}** → Anlaşılamadı. Lütfen tekrar dene.")
            os.unlink(ogg)
            return

        # Metin çevirisini yap ve göster
        result = await do_translate(original, stt["language"], sender_name,
                                    speaker_name=speaker_name, apply_accent=True)
        stt_elapsed = time.time() - t0
        text_preview = build_text(result, stt_elapsed)
        text_preview += "\n\n⏳ Sesli çeviri hazırlanıyor..."
        await tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                 text=text_preview)
        logger.info(f"✅ Metin hazır ({stt_elapsed:.1f}s) — TTS başlıyor")

        # AŞAMA 2: TTS arkada hazırlanırken mesaj zaten ekranda
        await send_tts(result, thread_id)

        # TTS bitti → metin mesajını güncelle (ses hazır işareti)
        elapsed = time.time() - t0
        final_text = build_text(result, elapsed)
        final_text += "\n\n🎤 Sesli çeviri gönderildi ✅"
        await tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                 text=final_text)
        logger.info(f"✅ Voice tamam ({elapsed:.1f}s) speaker={speaker_name}")

        os.unlink(ogg)

    except Exception as e:
        logger.error(f"Voice: {e}")
        try:
            await tg("editMessageText", chat_id=chat_id, message_id=msg_id,
                     text=f"❌ Hata: {str(e)[:200]}")
        except Exception:
            pass


# ── Command handler ───────────────────────────────────────────────
async def handle_command(msg):
    chat_id = msg["chat"]["id"]
    thread_id = msg.get("message_thread_id", TOPIC_ID)
    text = msg.get("text", "").strip()
    sender = msg.get("from", {})
    sender_id = sender.get("id", 0)
    sender_name = sender.get("first_name", "?")

    parts = text.split()
    cmd = parts[0].lower().split("@")[0]
    args = parts[1:]

    if cmd in ("/komutlar", "/help", "/start"):
        await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
            text="🌐 **Çeviri Botu v2.0 Komutları**\n\n"
                 "🎙 **Voice mesaj gönder** → otomatik çevirir\n"
                 "💬 **Metin yaz** → otomatik çevirir\n\n"
                 "**Komutlar:**\n"
                 "`/kayit [isim] [e/bayan]` — Sesini kaydet (klonlama için)\n"
                 "`/sesler` — Kayıtlı konuşmacıları listele\n"
                 "`/dil` — Aktif diller\n"
                 "`/düzelt [yanlış] > [doğru]` — Kelime düzeltmesi ekle\n"
                 "`/komutlar` — Bu mesaj\n\n"
                 "🇹🇷 Türkçe ↔ 🇹🇭 Tayca ↔ 🇬🇧 İngilizce")

    elif cmd in ("/kayit", "/kaydol"):
        if not args:
            await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
                text="📝 **Ses Kaydı**\n\n"
                     "Kullanım: `/kayit [isim] [e/bayan]`\n"
                     "Örnek: `/kayit Ahmet e`\n\n"
                     "Komuttan sonra 30 sn içinde sesli mesaj gönder.")
            return

        name = args[0]
        gender = "female"
        if len(args) >= 2 and args[1].lower() in ("e", "erkek", "male", "m"):
            gender = "male"

        pending_registrations[sender_id] = {
            "name": name, "gender": gender, "expires": time.time() + 30,
        }
        await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
            text=f"🎙 **{name}** ({gender}) için ses kaydı başladı!\n\n"
                 "Şimdi bir **sesli mesaj gönder** (5-15 sn):\n"
                 f"\"Merhaba, benim adım {name}.\"\n\n⏱ 30 sn süre var.")

    elif cmd == "/sesler":
        speakers = list_speakers()
        if not speakers:
            await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
                text="🔇 Henüz kayıtlı konuşmacı yok.\n`/kayit [isim] [e/bayan]` ile kaydol.")
            return
        lines = ["👥 **Kayıtlı Konuşmacılar:**\n"]
        for name, data in speakers.items():
            icon = "👨" if data.get("gender") == "male" else "👩"
            cloned = " 🔊" if data.get("voice_id") else ""
            lines.append(f"{icon} **{name}**{cloned} — {data.get('registered_samples', 0)} örnek")
        await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id, text="\n".join(lines))

    elif cmd == "/dil":
        langs = [f"{FLAG[l]} {LNAME[l]}" for l in config.ACTIVE_LANGUAGES]
        await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
            text=f"🌐 **Aktif Diller:**\n{'  •  '.join(langs)}")

    elif cmd in ("/düzelt", "/duzelt"):
        full = " ".join(args)
        if ">" not in full:
            await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
                text="Kullanım: `/düzelt [yanlış] > [doğru]`\nÖrnek: `/düzelt calismiyor > çalışmıyor`")
            return
        wrong, right = full.split(">", 1)
        sp = get_speaker_by_telegram_id(sender_id) or sender_name
        add_correction(sp, wrong.strip(), right.strip())
        await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
            text=f"✅ Düzeltme kaydedildi: **{sp}** için\n`{wrong.strip()}` → `{right.strip()}`\n\n📝 Bu düzeltme kalıcı kaydedildi. Bir daha aynı hatayı yapmam.")

        # Arkada repo'ya commit et (Railway/Supabase'a gitsin) — async task
        asyncio.create_task(_log_correction(sp, wrong.strip(), right.strip()))


# ── Telegram polling ──────────────────────────────────────────────
update_offset = 0

async def poll_loop():
    global update_offset
    logger.info("🔄 Telegram polling...")
    async with httpx.AsyncClient(timeout=120) as client:
        while True:
            try:
                r = await client.post(f"{API_BASE}/getUpdates", json={
                    "offset": update_offset, "timeout": 30,
                    "allowed_updates": json.dumps(["message"]),
                })
                data = r.json()
                if not data.get("ok"):
                    await asyncio.sleep(5); continue
                for u in data.get("result", []):
                    update_offset = u["update_id"] + 1
                    m = u.get("message")
                    if not m: continue
                    if m.get("chat", {}).get("id") != GROUP_CHAT_ID: continue
                    if m.get("message_thread_id") != TOPIC_ID: continue

                    txt = m.get("text", "")
                    if txt.startswith("/"):
                        await handle_command(m)
                    elif "voice" in m:
                        await handle_voice(m)
                    elif "text" in m and txt.strip():
                        name = m.get("from", {}).get("first_name", "?")
                        sender_id = m.get("from", {}).get("id", 0)
                        sp = get_speaker_by_telegram_id(sender_id)
                        src = detect_language_simple(txt)
                        result = await do_translate(txt, src, name,
                                                    speaker_name=sp, apply_accent=True)
                        await tg("sendMessage", chat_id=GROUP_CHAT_ID,
                                 message_thread_id=m.get("message_thread_id", TOPIC_ID),
                                 text=build_text(result))
            except Exception as e:
                logger.error(f"Poll: {e}")
                await asyncio.sleep(5)


# ── Main ──────────────────────────────────────────────────────────
async def main():
    me = await tg("getMe")
    if not me.get("ok"):
        logger.error(f"Bot: {me}"); sys.exit(1)
    logger.info(f"✅ @{me['result']['username']}")

    # Register commands (ASCII only for Telegram)
    await tg("setMyCommands", commands=[
        {"command": "komutlar", "description": "Komut listesi"},
        {"command": "kayit", "description": "Ses kaydi — isim ve cinsiyet"},
        {"command": "sesler", "description": "Kayitli konusmacilar"},
        {"command": "dil", "description": "Aktif diller"},
        {"command": "duzelt", "description": "Kelime duzeltme: yanlis > dogru"},
    ])

    app = web.Application()
    app.router.add_get("/", http_index)
    app.router.add_post("/translate", handle_translate)
    app.router.add_post("/voice-translate", handle_voice_translate)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()
    logger.info(f"🌐 HTTP: port {HTTP_PORT} — /translate + /voice-translate")

    asyncio.create_task(poll_loop())
    logger.info("🚀 Hazır! v2.0 — PTT + Voice + Text + Speaker ID + Commands")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
