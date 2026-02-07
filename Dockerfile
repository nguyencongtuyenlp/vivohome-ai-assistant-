# VIVOHOME AI - Docker Image
# Multi-stage build for optimized image size

FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./
COPY *.csv ./
COPY *.md ./

# Create database on build (optional - can also do at runtime)
# RUN python3 database.py

# Expose ports
# 8000: vLLM server
# 7860: Gradio app
EXPOSE 8000 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:7860')"

# Default command: run Gradio app
# (vLLM should be run separately or via docker-compose)
CMD ["python3", "app.py"]
