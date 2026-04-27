# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed to compile some Python packages (e.g. librosa, scipy)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
# Copy src for the editable install in builder stage
COPY src/ ./src/

# Install all Python dependencies into an isolated prefix so we can copy them cleanly
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt && \
    pip install --prefix=/install -e . --no-deps

# ── Stage 2: runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Runtime system packages: ffmpeg for video, Firefox + geckodriver for upload
# libgl1-mesa-glx and libglib2.0-0 are required for opencv-python
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        firefox-esr \
        wget \
        ca-certificates \
        libsndfile1 \
        procps \
        libgl1-mesa-glx \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Download geckodriver v0.34.0 for Linux x86_64
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz" \
        -O /tmp/geckodriver.tar.gz && \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/geckodriver && \
    rm /tmp/geckodriver.tar.gz

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy project files (respecting .dockerignore)
COPY . /app

# Re-install the project package itself (editable, no deps — deps already present)
# This ensures the entry points and metadata are correctly set up in the runtime stage
RUN pip install --no-deps -e .

# Runtime directories
RUN mkdir -p /app/output /root/.local/share/piper-tts/voices

ENV PORT=5050
ENV LOW_MEMORY_MODE=true
ENV VIDEO_THREADS=2
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LOG_LEVEL=INFO

EXPOSE 5050

CMD ["python", "dashboard.py"]
