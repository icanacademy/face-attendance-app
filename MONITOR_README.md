# Face Recognition Attendance Monitor

Standalone Python script for continuous camera monitoring and automatic attendance logging.

## Features

- **Continuous Monitoring**: Runs 24/7 without browser
- **No Permissions Needed**: Direct camera access via OpenCV
- **Audio Announcements**: Uses macOS `say` command
- **1-Hour Cooldown**: Prevents duplicate logging
- **Notion Integration**: Auto-updates teacher status
- **Visual Countdown**: Shows 3-2-1 before logging
- **Shared Database**: Uses same files as web interface

## Quick Start

### 1. Register Users First
Before running the monitor, register teachers via the web interface:

```bash
# Start the web server
/usr/local/bin/python3.11 server.py

# Open in browser: http://localhost:5001
# Go to Register tab and add teacher faces
```

### 2. Run the Monitor

**Option A: Using startup script (recommended)**
```bash
./start_monitor.sh
```

**Option B: Direct Python**
```bash
/usr/local/bin/python3.11 monitor.py
```

### 3. Stop the Monitor
- Press `q` in the camera window, OR
- Press `Ctrl+C` in the terminal

## Configuration

Edit `monitor.py` to customize:

```python
RECOGNITION_COOLDOWN = 3600  # 1 hour (in seconds)
SCAN_INTERVAL = 2           # Scan every 2 seconds
CAMERA_INDEX = 0            # Default camera (0=built-in, 1=external)
```

## How It Works

1. **Loads registered users** from `users.json`
2. **Opens camera** at specified index
3. **Scans every 2 seconds** for faces
4. **Recognizes face** using dlib (99.38% accuracy)
5. **Checks cooldown** (1 hour per person)
6. **Shows countdown** (3-2-1)
7. **Logs attendance** to `attendance.json`
8. **Updates Notion** (if linked)
9. **Announces** via audio: "Welcome [Name]. Attendance logged successfully."

## Audio Announcements

**Successful check-in:**
> "Welcome [Teacher Name]. Attendance logged successfully."

**Already checked in:**
> "[Teacher Name], already checked in. Thank you!"

**System messages:**
> "Attendance system activated. Monitoring started."
> "Attendance monitoring stopped."

## Troubleshooting

### Camera not opening
```bash
# Try different camera index in monitor.py
CAMERA_INDEX = 1  # For external camera
```

### No users found
```bash
# Register users via web interface first
# The monitor reads from users.json
```

### Audio not working
```bash
# Test macOS say command
say "test"

# If not working, check System Preferences → Sound
```

### Permission denied
```bash
# Make startup script executable
chmod +x start_monitor.sh
```

## Running on Startup (Optional)

To run the monitor automatically when your Mac starts:

1. **Create a LaunchAgent**:
```bash
# Create plist file
nano ~/Library/LaunchAgents/com.attendance.monitor.plist
```

2. **Add this content** (replace PATH with your actual path):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.attendance.monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/edward/face-attendance-app/start_monitor.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

3. **Load the agent**:
```bash
launchctl load ~/Library/LaunchAgents/com.attendance.monitor.plist
```

## System Architecture

```
┌─────────────────────────────────────────┐
│         Attendance System               │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │  Web Server  │  │  Camera Monitor │ │
│  │  (server.py) │  │  (monitor.py)   │ │
│  │              │  │                 │ │
│  │ • Register   │  │ • Continuous    │ │
│  │ • View logs  │  │ • Auto-detect   │ │
│  │ • Manage     │  │ • Audio alerts  │ │
│  └──────┬───────┘  └────────┬────────┘ │
│         │                   │          │
│         └────────┬──────────┘          │
│                  │                     │
│         ┌────────▼─────────┐           │
│         │  Shared Database │           │
│         │                  │           │
│         │ • users.json     │           │
│         │ • attendance.json│           │
│         │ • .env           │           │
│         └──────────────────┘           │
│                                        │
└────────────────────────────────────────┘
```

## Files

- `monitor.py` - Main monitoring script
- `start_monitor.sh` - Startup script
- `users.json` - Registered users (shared with web)
- `attendance.json` - Attendance logs (shared with web)
- `.env` - Notion credentials (shared with web)

## Performance

- **CPU Usage**: ~10-15% (optimized with 2-second scan interval)
- **Memory**: ~150-200MB
- **Accuracy**: 99.38% (dlib LFW benchmark)
- **Response Time**: ~2 seconds (scan interval)

## Next Steps

1. **Test the monitor** with registered users
2. **Adjust settings** (cooldown, scan interval, camera)
3. **Set up auto-start** (optional)
4. **Monitor logs** via web interface
5. **Check Notion updates** for linked teachers

## Support

For issues or questions:
- Check console output for error messages
- Verify users are registered via web interface
- Test camera with: `python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"`
- Ensure all dependencies are installed
