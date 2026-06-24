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


# ── PTT HTML ──────────────────────────────────────────────────────
PTT_HTML = r"""<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>🌐 Lato Çeviri</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0e1621;color:#e8e8e8;height:100vh;display:flex;flex-direction:column;overflow:hidden}
.header{background:#1a2837;padding:12px 16px;text-align:center;border-bottom:1px solid #2a3a4a;flex-shrink:0}
.header h1{font-size:16px;font-weight:600}
.header .sub{font-size:12px;color:#6ab2f2;margin-top:2px}
#display{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
.msg-block{background:#1a2837;border-radius:12px;padding:14px;border-left:3px solid #6ab2f2;animation:fadeIn .3s}
.msg-block.translated{border-left-color:#4caf50}
.msg-block .lang-label{font-size:11px;color:#6ab2f2;margin-bottom:4px;font-weight:600}
.msg-block.translated .lang-label{color:#4caf50}
.msg-block .text{font-size:15px;line-height:1.5;word-wrap:break-word}
.msg-block.partial{opacity:.85;border-left-color:#ff9800}
.msg-block.partial .lang-label{color:#ff9800}
.msg-block.partial::after{content:" ✏️"}
#status-bar{padding:8px 16px;text-align:center;font-size:13px;color:#6ab2f2;min-height:32px;flex-shrink:0}
#status-bar.listening{color:#ff5252}
#status-bar.processing{color:#ff9800}
#status-bar.done{color:#4caf50}
#ptt-container{padding:16px 16px 36px;display:flex;justify-content:center;background:#1a2837;border-top:1px solid #2a3a4a;flex-shrink:0}
#ptt-btn{width:130px;height:130px;border-radius:50%;border:none;background:#2a5298;color:white;font-size:14px;font-weight:700;cursor:pointer;user-select:none;-webkit-user-select:none;touch-action:none;transition:all .15s;box-shadow:0 4px 15px rgba(0,80,200,.4)}
#ptt-btn.recording{background:#d32f2f;transform:scale(1.1);box-shadow:0 0 30px rgba(255,50,50,.6);animation:pulse 1s infinite}
#ptt-btn:active{transform:scale(.95)}
#ptt-btn:disabled{opacity:.5}
@keyframes pulse{0%,100%{box-shadow:0 0 20px rgba(255,50,50,.4)}50%{box-shadow:0 0 40px rgba(255,50,50,.8)}}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
</style></head><body>
<div class="header"><h1>🌐 Lato Çeviri</h1><div class="sub">🇹🇷 ↔ 🇹🇭 ↔ 🇬🇧</div></div>
<div id="display"><div class="msg-block" style="border-left-color:#666;text-align:center"><div class="text" style="color:#888;font-size:13px">🔘 Butona basılı tut ve konuş<br>Konuşurken çeviriyi canlı gör<br>Bırakınca topic'e gönderilir</div></div></div>
<div id="status-bar">Hazır — bas ve konuş</div>
<div id="ptt-container"><button id="ptt-btn">🎤 BAS<br>KONUŞ</button></div>
<script>
const WS_URL=(location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws';
const FLAG={tr:'🇹🇷',th:'🇹🇭',en:'🇬🇧'};
const NAME={tr:'Türkçe',th:'Tayca',en:'English'};
let ws=null,rec=null,ctx=null,proc=null,isRecording=false;
const btn=document.getElementById('ptt-btn'),display=document.getElementById('display'),statusBar=document.getElementById('status-bar');

function connectWS(){
  ws=new WebSocket(WS_URL);
  ws.onopen=()=>statusBar.textContent='Hazır — bas ve konuş';
  ws.onclose=()=>{statusBar.textContent='⚠️ Yeniden bağlanıyor...';setTimeout(connectWS,2000);};
  ws.onmessage=e=>handleMessage(JSON.parse(e.data));
}
connectWS();

function handleMessage(d){
  if(d.type==='status'){
    const map={listening:['🔴 Dinleniyor...','listening'],processing:['⏳ Çevriliyor...','processing'],done:['✅ Topic\'e gönderildi!','done']};
    const m=map[d.status];
    if(m){statusBar.textContent=m[0];statusBar.className=m[1];}
    if(d.status==='done'||d.status==='error'){btn.classList.remove('recording');btn.disabled=false;btn.innerHTML='🎤 BAS<br>KONUŞ';}
  }else if(d.type==='partial'){showPartial(d);}
  else if(d.type==='done'){showFinal(d.result);}
  else if(d.type==='error'){statusBar.textContent='❌ '+d.message;}
}

function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}

function showPartial(d){
  let el=display.querySelector('.msg-block.partial');
  if(!el){el=document.createElement('div');el.className='msg-block partial';display.appendChild(el);}
  let h='';
  if(d.original!==undefined){
    h+=`<div class="lang-label">${FLAG[d.source_lang]||'🗣'} ${NAME[d.source_lang]||d.source_lang} (canlı)</div>`;
    h+=`<div class="text">${esc(d.original)}</div>`;
    if(d.translations)for(const[l,t]of Object.entries(d.translations)){if(t){h+=`<div class="lang-label" style="margin-top:6px">${FLAG[l]} ${NAME[l]}</div><div class="text">${esc(t)}</div>`;}}
  }
  el.innerHTML=h;display.scrollTop=display.scrollHeight;
}

function showFinal(r){
  display.querySelectorAll('.msg-block.partial').forEach(e=>e.remove());
  const b=document.createElement('div');b.className='msg-block translated';
  let h=`<div class="lang-label">${FLAG[r.source_lang]} ${NAME[r.source_lang]}</div><div class="text">${esc(r.original)}</div>`;
  for(const[l,t]of Object.entries(r.translations||{})){if(t){h+=`<div class="lang-label" style="margin-top:8px">${FLAG[l]} ${NAME[l]}</div><div class="text">${esc(t)}</div>`;}}
  h+=`<div style="margin-top:6px;font-size:11px;color:#4caf50">✅ Topic'e gönderildi</div>`;
  b.innerHTML=h;display.appendChild(b);display.scrollTop=display.scrollHeight;
}

async function startRec(){
  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:{sampleRate:16000,channelCount:1,echoCancellation:true,noiseSuppression:true}});
    ctx=new(window.AudioContext||window.webkitAudioContext)({sampleRate:16000});
    const src=ctx.createMediaStreamSource(stream);
    proc=ctx.createScriptProcessor(4096,1,1);
    proc.onaudioprocess=e=>{
      if(!isRecording)return;
      const f32=e.inputBuffer.getChannelData(0);
      const i16=new Int16Array(f32.length);
      for(let i=0;i<f32.length;i++){const s=Math.max(-1,Math.min(1,f32[i]));i16[i]=s<0?s*0x8000:s*0x7FFF;}
      const u8=new Uint8Array(i16.buffer);let bin='';for(let i=0;i<u8.length;i++)bin+=String.fromCharCode(u8[i]);
      if(ws.readyState===1)ws.send(JSON.stringify({type:'audio',data:btoa(bin)}));
    };
    src.connect(proc);proc.connect(ctx.destination);
    isRecording=true;rec=stream;
    ws.send(JSON.stringify({type:'start',sender:'Kullanıcı',topic_id:146}));
  }catch(e){statusBar.textContent='❌ Mikrofon: '+e.message;btn.disabled=false;btn.classList.remove('recording');btn.innerHTML='🎤 BAS<br>KONUŞ';}
}

function stopRec(){
  isRecording=false;
  if(ws&&ws.readyState===1)ws.send(JSON.stringify({type:'stop'}));
  if(proc){proc.disconnect();proc=null;}
  if(rec){rec.getTracks().forEach(t=>t.stop());rec=null;}
  if(ctx){setTimeout(()=>{ctx.close();ctx=null;},500);}
  btn.classList.remove('recording');btn.disabled=true;btn.innerHTML='⏳ İŞLENİYOR';
}

function pStart(e){e.preventDefault();if(btn.disabled)return;btn.classList.add('recording');btn.innerHTML='🔴 KONUŞUYOR<br>BIRAK=GÖNDER';display.querySelectorAll('.msg-block.partial').forEach(el=>el.remove());startRec();}
function pEnd(e){e.preventDefault();if(!isRecording)return;stopRec();}

btn.addEventListener('touchstart',pStart,{passive:false});
btn.addEventListener('touchend',pEnd,{passive:false});
btn.addEventListener('touchcancel',pEnd,{passive:false});
btn.addEventListener('mousedown',pStart);
btn.addEventListener('mouseup',pEnd);
btn.addEventListener('mouseleave',e=>{if(isRecording)pEnd(e);});
btn.addEventListener('contextmenu',e=>e.preventDefault());
</script></body></html>"""


# ── HTTP + WebSocket handlers (aiohttp, same port) ────────────────
async def http_index(request):
    return web.Response(text=PTT_HTML, content_type="text/html", charset="utf-8")

async def ws_handler(request):
    ws = web.WebSocketResponse(max_msg_size=0)
    await ws.prepare(request)
    logger.info(f"🔌 WS bağlandı: {request.remote}")

    audio_chunks = []
    sender_name = "Konuşmacı"
    topic_id = TOPIC_ID
    last_partial = 0
    recording = False

    async for msg in ws:
        if msg.type != WSMsgType.TEXT:
            continue
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            continue

        mtype = data.get("type")

        if mtype == "start":
            audio_chunks = []
            recording = True
            sender_name = data.get("sender", "Konuşmacı")
            topic_id = data.get("topic_id", TOPIC_ID)
            last_partial = time.time()
            logger.info(f"🎙 PTT başladı: {sender_name}")
            await ws.send_str(json.dumps({"type": "status", "status": "listening"}))

        elif mtype == "audio" and recording:
            raw = base64.b64decode(data["data"])
            audio_chunks.append(raw)
            now = time.time()
            if now - last_partial > 1.5 and len(audio_chunks) > 5:
                last_partial = now
                # Partial transcription in background
                asyncio.create_task(_partial(ws, list(audio_chunks)))

        elif mtype == "stop" and recording:
            recording = False
            logger.info(f"⏹ PTT bitti ({len(audio_chunks)} chunks)")
            await ws.send_str(json.dumps({"type": "status", "status": "processing"}))

            wav_path = chunks_to_wav(audio_chunks)
            if not wav_path:
                await ws.send_str(json.dumps({"type": "error", "message": "Ses kısa"}))
                continue

            stt = await run_whisper(wav_path)
            os.unlink(wav_path)
            original = stt["text"].strip()

            if not original:
                await ws.send_str(json.dumps({"type": "error", "message": "Anlaşılamadı"}))
                continue

            t0 = time.time()
            result = await do_translate(original, stt["language"], sender_name)
            elapsed = time.time() - t0

            await ws.send_str(json.dumps({
                "type": "done", "result": result,
                "elapsed": round(elapsed, 1)
            }, ensure_ascii=False))

            # Post to topic
            await tg("sendMessage",
                chat_id=GROUP_CHAT_ID, message_thread_id=topic_id,
                text=build_text(result, elapsed))

            await send_tts(result, topic_id)

            await ws.send_str(json.dumps({
                "type": "status", "status": "done", "topic_posted": True
            }))
            logger.info(f"✅ Topic'e gönderildi ({elapsed:.1f}s)")

    logger.info("🔌 WS kapandı")
    return ws

async def _partial(ws, chunks):
    """Send partial transcription + translation to client."""
    try:
        wav = chunks_to_wav(chunks)
        if not wav:
            return
        stt = await run_whisper(wav)
        os.unlink(wav)
        text = stt["text"].strip()
        if not text:
            return
        targets = [l for l in config.ACTIVE_LANGUAGES if l != stt["language"]]
        translations = translate_text(text, stt["language"], targets)
        await ws.send_str(json.dumps({
            "type": "partial",
            "original": text,
            "source_lang": stt["language"],
            "translations": translations,
        }, ensure_ascii=False))
    except Exception as e:
        logger.debug(f"Partial: {e}")


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
            text=f"✅ Düzeltme kaydedildi: **{sp}** için\n`{wrong.strip()}` → `{right.strip()}`")


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
    app.router.add_get("/ws", ws_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()
    logger.info(f"🌐 HTTP+WS: port {HTTP_PORT}")

    asyncio.create_task(poll_loop())
    logger.info("🚀 Hazır! v2.0 — PTT + Voice + Text + Speaker ID + Commands")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
