# Dockerfile for Whisper Video to Text

FROM python:3.11-slim

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

# Install dependencies from lockfile
# We export to requirements.txt first to ensure exact versions from lockfile are used
RUN set -e && \
    uv export --frozen --format requirements-txt --output-file requirements.txt --extra web && \
    uv pip install --system --no-cache -r requirements.txt && \
    rm requirements.txt && \
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
    mkdir -p /app/uploads /app/transcripts && \
    chown -R appuser:appuser /app && \
    echo "✓ Application setup completed"

# Switch to non-root user
USER appuser

# Expose web server port
EXPOSE 8000

# Add health check that verifies the package is importable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import whisper_video_to_text" || exit 1

# Set entrypoint script
ENTRYPOINT ["docker-entrypoint.sh"]

# Default command shows help
CMD ["--help"]
