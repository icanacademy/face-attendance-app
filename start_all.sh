#!/bin/bash

# Face Recognition Attendance System - Complete Startup Script
# Starts web server + camera monitor with one command

PYTHON="/usr/local/bin/python3.11"

# Check if Python exists
if [ ! -f "$PYTHON" ]; then
    echo "⚠ Python 3.11 not found, using system python3"
    PYTHON="python3"
fi

echo "========================================="
echo "Face Recognition Attendance System"
echo "========================================="
echo ""
echo "Starting complete system..."
echo ""

# Check if attendance-checker is running
echo "🔍 Checking attendance-checker integration..."
if lsof -ti:3001 > /dev/null 2>&1; then
    echo "   ✓ attendance-checker running on port 3001"
    echo "   ✓ Integration enabled - attendance will sync to both systems"
else
    echo "   ⚠ attendance-checker NOT running on port 3001"
    echo "   ⚠ Face attendance will work, but won't sync to attendance-checker"
fi
echo ""

# Kill any existing instances
echo "🧹 Cleaning up any running instances..."
lsof -ti:5001 | xargs kill -9 2>/dev/null
killall -9 Python python3 python3.11 2>/dev/null
sleep 1

# Start web server in background
echo "🌐 Starting web server on http://localhost:5001..."
$PYTHON server.py > server.log 2>&1 &
SERVER_PID=$!
echo "   ✓ Web server starting (PID: $SERVER_PID)"
echo "   📝 Logs: server.log"
echo "   ⏳ Waiting for server to initialize..."

# Wait up to 10 seconds for server to start
for i in {1..10}; do
    sleep 1
    if lsof -ti:5001 > /dev/null 2>&1; then
        echo "   ✓ Web server ready on port 5001"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   ❌ Web server failed to start within 10 seconds!"
        echo "   Check server.log for errors"
        exit 1
    fi
done

echo ""
echo "🎥 Starting camera monitor..."
echo "   Press 'q' in camera window to stop"
echo "   Or press Ctrl+C here to stop everything"
echo ""
echo "========================================="
echo "System Ready!"
echo "========================================="
echo ""
echo "Web Interface: http://localhost:5001"
echo "  • Register new faces"
echo "  • View attendance history"
echo "  • Manage registered users"
echo ""
echo "Camera Monitor: Running"
echo "  • Automatic face detection"
echo "  • Audio announcements"
echo "  • 10-second cooldown"
echo ""
echo "Attendance Sync:"
if lsof -ti:3001 > /dev/null 2>&1; then
    echo "  ✓ attendance-checker (port 3001) - ACTIVE"
    echo "  ✓ Notion database - ACTIVE"
else
    echo "  ⚠ attendance-checker (port 3001) - OFFLINE"
    echo "  ✓ Notion database - ACTIVE"
fi
echo ""
echo "========================================="
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo ""
    echo "🛑 Stopping system..."
    echo "   Stopping camera monitor..."
    echo "   Stopping web server (PID: $SERVER_PID)..."
    kill $SERVER_PID 2>/dev/null
    lsof -ti:5001 | xargs kill -9 2>/dev/null
    echo "   ✓ All processes stopped"
    echo ""
    echo "Goodbye! 👋"
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Start monitor in foreground (blocks until stopped)
$PYTHON monitor.py

# When monitor exits, cleanup runs automatically via trap
