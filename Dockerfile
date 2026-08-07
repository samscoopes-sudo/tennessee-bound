FROM python:3.11-slim

# ffmpeg (rendering) + fonts (drawtext lower-thirds/stats)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV WORK_DIR=/tmp/video-agent \
    PORT=8000
EXPOSE 8000

# faster-whisper downloads the model on first use; that's fine at runtime.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
