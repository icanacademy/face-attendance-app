#!/bin/bash

# Face Recognition Attendance Monitor Startup Script

echo "========================================="
echo "Starting Attendance Monitor"
echo "========================================="
echo ""

# Use Python 3.11 for compatibility
PYTHON="/usr/local/bin/python3.11"

# Check if Python exists
if [ ! -f "$PYTHON" ]; then
    echo "❌ Python 3.11 not found at $PYTHON"
    echo "   Using system python3 instead..."
    PYTHON="python3"
fi

# Run the monitor
echo "🚀 Launching camera monitor..."
echo "   Press 'q' in the camera window to stop"
echo "   Or press Ctrl+C here to stop"
echo ""

$PYTHON monitor.py

echo ""
echo "✓ Monitor stopped"
