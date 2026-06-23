# LINE Bot Deploy Durumu (2026-06-23)

## ✅ Tamamlanan
- [x] LINE Channel oluşturuldu (ID: 2010490532)
- [x] Channel Secret + Access Token alındı
- [x] Webhook server (aiohttp, port 8089) deploy edildi
- [x] Caddy HTTPS reverse proxy: `line.178-104-122-91.nip.io`
- [x] Webhook URL LINE API'ye kaydedildi
- [x] Signature doğrulama test edildi ✓
- [x] Docker container (lato-line-bot) çalışıyor

## ⬜ Leb'in Yapması Gereken
1. **LINE Developers Console** → Messaging API settings
2. **"Use webhook" → ON** (şu an `active: false`)
3. Bot'u LINE arkadaşlarına ekle (QR kod ile)

## 🔧 Teknik Detaylar
- **Webhook URL**: `https://line.178-104-122-91.nip.io/webhook`
- **Health**: `https://line.178-104-122-91.nip.io/health`
- **Container**: `lato-line-bot` (Docker, efloud-bot_default network)
- **Token yenileme**: 30 günde bir (`POST /v2/oauth/accessToken`)
- **Push mesaj**: Free planda kapalı → reply mesajları çalışır

## 📱 Kullanım
Personel LINE'da bota yazınca:
- AI mesajı sınıflandırır (departman, öncelik, tip)
- 3 dilli özet üretir (TR/TH/EN)
- Doğru Telegram topic'e yönlendirir
- Fotoğraf → OCR (fatura/dekont okuma)
- Ses → STT (gelecek)

Kayıt: `/register [İsim] [Departman]`
