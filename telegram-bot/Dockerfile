FROM python:3.11-slim

# claude CLI için Node.js (abonelik ile ücretsiz Sonnet 5)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g @anthropic-ai/claude-code && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir httpx>=0.27

WORKDIR /app
COPY claude_client.py lato_telegram_bot.py ./

# Abonelik kimliği host'tan mount edilir: -v ~/.claude:/root/.claude
# (host'ta bir kez `claude setup-token` çalıştırılmış olmalı)
CMD ["python3", "lato_telegram_bot.py"]
