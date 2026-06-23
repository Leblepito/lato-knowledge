FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    aiohttp>=3.9 \
    httpx>=0.27 \
    line-bot-sdk>=3.23

COPY src/ .

EXPOSE 8089
CMD ["python3", "line_bot.py"]
