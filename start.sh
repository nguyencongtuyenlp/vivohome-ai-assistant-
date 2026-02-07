#!/bin/bash
# VIVOHOME AI - Startup Script
# Initialize database and run Gradio app

set -e  # Exit on error

echo "=================================================="
echo "🚀 VIVOHOME AI - Starting..."
echo "=================================================="

# Wait for vLLM server to be ready
echo "⏳ Waiting for vLLM server..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ vLLM server is ready!"
        break
    fi
    retry_count=$((retry_count + 1))
    echo "   Retry $retry_count/$max_retries..."
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ vLLM server failed to start"
    exit 1
fi

# Initialize database if not exists
if [ ! -f "vivohome.db" ]; then
    echo "🗄️  Creating database..."
    python3 database.py
else
    echo "✅ Database already exists"
fi

# Run Gradio app
echo "🌐 Starting Gradio app..."
python3 app.py
