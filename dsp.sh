#!/bin/bash
# SuperShorts Production Suite Launcher

echo "🚀 Starting SuperShorts Dashboard..."
python3 dashboard.py > dashboard.log 2>&1 &
SERVER_PID=$!

echo "🎬 Dashboard live: http://localhost:5050"
echo "📂 Logs: tail -f dashboard.log"
echo ""
echo "Press [ENTER] to shutdown the server and all background tasks..."
read

echo "⏹ Stopping dashboard (PID: $SERVER_PID)..."
kill $SERVER_PID 2>/dev/null
pkill -f "python3 -c" # Cleanup any orphan subprocesses
echo "✅ Everything closed."
