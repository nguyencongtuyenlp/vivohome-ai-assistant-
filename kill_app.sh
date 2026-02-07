#!/bin/bash
# Kill all Python processes running app.py

echo "🔍 Finding app.py processes..."
pids=$(ps aux | grep "python.*app.py" | grep -v grep | awk '{print $2}')

if [ -z "$pids" ]; then
    echo "✅ No app.py processes found"
else
    echo "🔪 Killing processes: $pids"
    kill -9 $pids
    echo "✅ Processes killed"
fi

echo ""
echo "🔍 Finding Gradio processes on port 7860..."
gradio_pids=$(lsof -ti:7860)

if [ -z "$gradio_pids" ]; then
    echo "✅ Port 7860 is free"
else
    echo "🔪 Killing processes on port 7860: $gradio_pids"
    kill -9 $gradio_pids
    echo "✅ Port freed"
fi

echo ""
echo "✅ All processes cleaned up!"
echo "You can now run: python3 app.py"
