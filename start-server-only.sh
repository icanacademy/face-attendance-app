#!/bin/bash

# Face Recognition Attendance System - Server Only
# Starts just the web server (no camera monitor)

PYTHON="/usr/local/bin/python3.11"

# Check if Python exists
if [ ! -f "$PYTHON" ]; then
    echo "⚠ Python 3.11 not found, using system python3"
    PYTHON="python3"
fi

echo "========================================="
echo "Face Recognition Attendance System"
echo "Web Server Only"
echo "========================================="
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
echo "🧹 Cleaning up any running instances on port 5001..."
lsof -ti:5001 | xargs kill -9 2>/dev/null
sleep 1

# Start web server
echo "🌐 Starting web server on http://localhost:5001..."
echo ""
echo "========================================="
echo "Server Starting..."
echo "========================================="
echo ""
echo "Web Interface: http://localhost:5001"
echo "  • Register new faces"
echo "  • View attendance history"
echo "  • Manage registered users"
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
echo "Press Ctrl+C to stop the server"
echo "========================================="
echo ""

# Start server in foreground
$PYTHON server.py
