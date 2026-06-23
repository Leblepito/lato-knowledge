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

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("lato-translate")

# ── Config ─────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TRANSLATE_BOT_TOKEN", "")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
GROUP_CHAT_ID = config.GROUP_CHAT_ID
TOPIC_ID = config.TRANSLATION_TOPIC_ID
HTTP_PORT = 8088

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
async def do_translate(original, source_lang, sender_name="Konuşmacı"):
    targets = [l for l in config.ACTIVE_LANGUAGES if l != source_lang]
    translations = translate_text(original, source_lang, targets)
    return {"original": original, "source_lang": source_lang,
            "translations": translations, "sender_name": sender_name}

def build_text(result, elapsed=0):
    sl = result["source_lang"]
    lines = [f"🗣 **{result['sender_name']}**  {FLAG.get(sl,'🗣')} {LNAME.get(sl,sl)}:",
             result["original"], ""]
    for l, t in result["translations"].items():
        if t:
            lines += [f"{FLAG[l]} **{LNAME[l]}**:", t, ""]
    if elapsed:
        lines.append(f"⏱ {elapsed:.1f}s")
    return "\n".join(lines).strip()

async def send_tts(result, thread_id):
    for l, t in result["translations"].items():
        if not t:
            continue
        try:
            ogg = synthesize(t, language=l)
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


# ── Telegram voice handler ────────────────────────────────────────
async def handle_voice(msg):
    chat_id = msg["chat"]["id"]
    thread_id = msg.get("message_thread_id", TOPIC_ID)
    sender_name = msg.get("from", {}).get("first_name", "?")
    file_id = msg.get("voice", {}).get("file_id")

    t0 = time.time()
    proc_msg = await tg("sendMessage", chat_id=chat_id, message_thread_id=thread_id,
                        text=f"🎧 **{sender_name}** dinleniyor...")
    msg_id = proc_msg.get("result", {}).get("message_id")

    try:
        ogg = await download_file(file_id)
        stt = await run_whisper(ogg)
        os.unlink(ogg)
        original = stt["text"].strip()
        if not original:
            await tg("editMessageText", chat_id=chat_id, message_id=msg_id, text="🔇 Anlaşılamadı")
            return
        result = await do_translate(original, stt["language"], sender_name)
        elapsed = time.time() - t0
        await tg("editMessageText", chat_id=chat_id, message_id=msg_id, text=build_text(result, elapsed))
        await send_tts(result, thread_id)
        logger.info(f"✅ Voice ({elapsed:.1f}s)")
    except Exception as e:
        logger.error(f"Voice: {e}")
        await tg("editMessageText", chat_id=chat_id, message_id=msg_id, text=f"❌ {str(e)[:200]}")


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
                    if "voice" in m:
                        await handle_voice(m)
                    elif "text" in m and not m["text"].startswith("/"):
                        text = m["text"].strip()
                        name = m.get("from", {}).get("first_name", "?")
                        src = detect_language_simple(text)
                        result = await do_translate(text, src, name)
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

    app = web.Application()
    app.router.add_get("/", http_index)
    app.router.add_get("/ws", ws_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()
    logger.info(f"🌐 HTTP+WS: port {HTTP_PORT}")

    asyncio.create_task(poll_loop())
    logger.info("🚀 Hazır! PTT + Voice + Text destekli.")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
