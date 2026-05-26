# Dockerfile for Whisper Video to Text

FROM python:3.11-slim

ARG APP_REVISION=local

LABEL org.opencontainers.image.title="Whisper Video to Text" \
      org.opencontainers.image.description="Local-first media transcription with Whisper, ffmpeg normalization, and web uploads." \
      org.opencontainers.image.revision="${APP_REVISION}"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies with error handling
RUN set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        curl && \
    rm -rf /var/lib/apt/lists/* && \
    # Verify ffmpeg installation
    ffmpeg -version && \
    echo "✓ System dependencies installed successfully"

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set workdir
WORKDIR /app

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install runtime dependencies directly.
# `uv export --frozen` currently fails on Linux x86_64 due a resolver conflict
# between locked `triton==3.3.1` and `openai-whisper==20231117`.
RUN set -e && \
    uv pip install --system --no-cache \
        "openai-whisper==20231117" \
        "yt-dlp>=2025.01.01" \
        "tqdm==4.66.4" \
        "fastapi" \
        "uvicorn[standard]" \
        "python-multipart" \
        "jinja2" && \
    echo "✓ Python dependencies installed successfully"

# Copy entrypoint script first and make it executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Copy application code
COPY . /app

# Install the application package itself (no dependencies as they are already installed)
RUN set -e && \
    uv pip install --system --no-deps . && \
    echo "✓ Application installed successfully"

# Verify installation and create non-root user for security
RUN set -e && \
    python -c "import whisper_video_to_text; print('Package imported successfully')" && \
    useradd --create-home --shell /bin/bash appuser && \
    # Create necessary directories for volumes with correct permissions
    mkdir -p \
        /app/uploads \
        /app/transcripts \
        /home/appuser/.cache/whisper \
        /home/appuser/.cache/yt-dlp && \
    chown -R appuser:appuser /app /home/appuser/.cache && \
    echo "✓ Application setup completed"

# Switch to non-root user
USER appuser

# Expose web server port
EXPOSE 8000

# Add health check that verifies the package and media registry are importable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import whisper_video_to_text; from whisper_video_to_text.convert import SUPPORTED_MEDIA_EXTENSIONS; assert '.m4a' in SUPPORTED_MEDIA_EXTENSIONS" || exit 1

# Set entrypoint script
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command shows help
CMD ["--help"]
