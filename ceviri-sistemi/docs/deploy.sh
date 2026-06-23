#!/bin/bash
# Lato Çeviri Sistemi — Deploy Script
# /opt/lato-translator/ içine kopyalayıp çalıştırın
set -e

echo "🚀 Lato Çeviri Sistemi Deploy"
echo "=============================="

# 1. Token kontrol
if [ -z "${TRANSLATE_BOT_TOKEN}" ]; then
    echo "❌ TRANSLATE_BOT_TOKEN env yok!"
    echo "   .env dosyasına ekleyin: TRANSLATE_BOT_TOKEN=<@BotFather token>"
    exit 1
fi

# 2. Build
echo "📦 Docker image build..."
docker build -t lato-translator-lato-translator:latest .

# 3. Eski container'ı durdur
echo "🛑 Eski container..."
docker stop lato-translator 2>/dev/null || true
docker rm lato-translator 2>/dev/null || true

# 4. Yeni container
echo "🐳 Container başlatılıyor..."
docker run -d \
    --name lato-translator \
    --restart always \
    --network efloud-bot_default \
    --env-file /root/.hermes/profiles/lato/.env \
    -e HERMES_HOME=/root/.hermes/profiles/lato \
    -v /opt/lato-translator/data:/app/data \
    lato-translator-lato-translator:latest

# 5. Sağlık kontrolü
echo "⏳ Başlangıç bekleniyor (15s)..."
sleep 15

if docker logs lato-translator 2>&1 | grep -q "🚀 Hazır"; then
    echo "✅ Sistem aktif!"
    docker logs lato-translator --tail 5
else
    echo "⚠️ Loglar kontrol edin:"
    docker logs lato-translator --tail 20
fi

echo ""
echo "📍 URL: https://translate.178-104-122-91.nip.io/"
echo "🤖 Bot: @Latotranslate_bot (Topic #146)"
