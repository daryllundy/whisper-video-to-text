# Dockerfile for Whisper Video to Text

FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set workdir
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN uv pip install .[dev]

# Default command
ENTRYPOINT ["python", "-m", "whisper_video_to_text.cli"]
