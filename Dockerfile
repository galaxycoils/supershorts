# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libsndfile1-dev \
        ffmpeg \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        libswscale-dev \
        libavdevice-dev \
        libavfilter-dev \
        libswresample-dev \
        pkg-config \
        espeak \
        libespeak-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY src/ ./src/

# Install all Python dependencies into an isolated prefix
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt && \
    pip install --prefix=/install -e . --no-deps

# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Create a non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

# Runtime system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        firefox-esr \
        wget \
        ca-certificates \
        libsndfile1 \
        procps \
        libgl1-mesa-glx \
        libglib2.0-0 \
        espeak \
    && rm -rf /var/lib/apt/lists/*

# Download geckodriver v0.34.0
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz" \
        -O /tmp/geckodriver.tar.gz && \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/geckodriver && \
    rm /tmp/geckodriver.tar.gz

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Create necessary directories and set permissions
RUN mkdir -p /app/output /app/assets /home/appuser/.local/share/piper-tts/voices /home/appuser/.mozilla/firefox \
    && chown -R appuser:appgroup /app /home/appuser

# Copy project files with correct ownership
COPY --chown=appuser:appgroup . /app

# Switch to non-root user
USER appuser
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Re-install the project package itself (editable, no deps)
RUN pip install --user --no-deps -e .

ENV PORT=5050
ENV LOW_MEMORY_MODE=true
ENV VIDEO_THREADS=2
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LOG_LEVEL=INFO

EXPOSE 5050

CMD ["python", "dashboard.py"]
