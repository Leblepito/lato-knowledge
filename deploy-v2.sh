#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Lato v2 — Sunucu Kurulumu (tek komut)
# Kullanım (VPS'te root):  bash deploy-v2.sh
# Yaptıkları: repo güncelle → claude CLI kontrol → bağımlılık →
#             systemd servisi kur → başlat → durum göster
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

REPO=/opt/lato-knowledge
ENVF=/root/.hermes/profiles/lato/.env

echo "══ 1/6 Repo ══"
if [ -d "$REPO/.git" ]; then
    git -C "$REPO" pull --ff-only
else
    git clone https://github.com/Leblepito/lato-knowledge.git "$REPO"
fi

echo "══ 2/6 .env kontrol ══"
if [ ! -f "$ENVF" ]; then
    echo "❌ $ENVF yok. Önce oluştur (bkz. KURULUM.md §2) — en az TELEGRAM_BOT_TOKEN gerekli."
    exit 1
fi
grep -q "TELEGRAM_BOT_TOKEN\|TRANSLATE_BOT_TOKEN" "$ENVF" || {
    echo "❌ .env içinde TELEGRAM_BOT_TOKEN yok."; exit 1; }

echo "══ 3/6 claude CLI (ücretsiz Sonnet 5) ══"
if ! command -v claude >/dev/null 2>&1; then
    echo "claude CLI kuruluyor..."
    npm install -g @anthropic-ai/claude-code
fi
if ! timeout 90 bash -c 'echo "sadece: ok yaz" | claude -p --model claude-sonnet-5 --output-format text' >/dev/null 2>&1; then
    echo "⚠️  Claude aboneliği girişi yapılmamış."
    echo "    Şimdi çalıştır:  claude setup-token"
    echo "    Sonra bu scripti tekrar çalıştır:  bash deploy-v2.sh"
    exit 1
fi
echo "✅ Sonnet 5 CLI hazır (abonelik — token faturası yok)"

echo "══ 4/6 Python bağımlılığı ══"
pip3 install -q httpx 2>/dev/null || pip3 install -q --break-system-packages httpx

echo "══ 5/6 systemd servisi ══"
cp "$REPO/telegram-bot/lato-telegram-bot.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now lato-telegram-bot
sleep 3

echo "══ 6/6 Durum ══"
systemctl --no-pager -l status lato-telegram-bot | head -10 || true
echo ""
echo "─────────────────────────────────────────────────────────"
echo "✅ Kurulum tamam. Test:"
echo "   • Telegram #131'e arıza fotoğrafı at → olay kaydı taslağı gelmeli"
echo "   • Herhangi bir departman topic'inde /help yaz"
echo "   • Log: journalctl -u lato-telegram-bot -f"
echo ""
echo "⚠️  NOT: @Latotry_bot token'ını BAŞKA bir servis de getUpdates ile"
echo "   dinliyorsa (örn. Hermes) 409 çatışması olur → loglarda '409 Conflict'"
echo "   görürsen ya eski dinleyiciyi kapat ya da BotFather'dan yeni token aç."
echo "─────────────────────────────────────────────────────────"
