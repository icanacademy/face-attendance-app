# Camera Setup Guide

## 📹 Camera Access Issues

The face-attendance-app uses cameras in **TWO different ways**:

### 1. Web Interface (Browser) ✅ **RECOMMENDED**
- Uses **WebRTC** (browser camera API)
- Browser handles permissions
- **Usually works without issues**
- Best for face registration

**How to use:**
1. Start server: `./start-server-only.sh`
2. Open: http://localhost:5001
3. Click "Register Face" tab
4. Click "Start Camera"
5. Browser will ask for camera permission → Click "Allow"
6. Camera stream appears in browser

### 2. Camera Monitor (Python/OpenCV) ⚠️ **Requires Permission**
- Uses **OpenCV** (system-level camera access)
- Requires Terminal app to have camera permissions
- Used by `monitor.py` for automatic face detection

**How to enable:**
1. Open **System Settings**
2. Go to **Privacy & Security** → **Camera**
3. Look for your Terminal app:
   - "Terminal" (default macOS Terminal)
   - "iTerm" (if using iTerm2)
   - "Visual Studio Code" (if running from VS Code terminal)
4. **Enable the checkbox** next to your terminal app
5. Restart the terminal
6. Run `./start_all.sh` again

## 🔧 Troubleshooting

### "Camera opened: False" error
This means Terminal doesn't have camera permission.

**Solution:**
- Use the web interface (http://localhost:5001) instead
- Or grant Terminal camera permissions (see above)

### "OpenCV: not authorized to capture video"
Same as above - permission issue.

**Quick Fix:** Just use the web interface!

### Camera works in browser but not in monitor.py
This is expected! They use different APIs.
- Browser = WebRTC (has permission by default)
- Python = OpenCV (needs Terminal permission)

## 💡 Recommended Workflow

**For Registration:**
```bash
# Start web server only
./start-server-only.sh

# Open browser: http://localhost:5001
# Register faces using web interface
```

**For Automatic Monitoring:**
```bash
# First: Grant Terminal camera permission (one-time setup)
# System Settings → Privacy → Camera → Enable Terminal

# Then: Start full system
./start_all.sh

# Camera monitor will auto-detect faces
```

## 📱 Which Method to Use?

| Task | Use | Reason |
|------|-----|--------|
| Register new faces | Web Interface | Easy, reliable, browser handles permissions |
| Manual time in/out | Web Interface | Quick, no terminal needed |
| Automatic monitoring | Camera Monitor | Hands-free, auto-detects faces |
| Testing | Web Interface | Faster to set up |

## ✅ Verify Camera Access

**Test Web Interface:**
```bash
./start-server-only.sh
# Open http://localhost:5001
# Click "Register Face" → "Start Camera"
# Should show camera feed
```

**Test Camera Monitor:**
```bash
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera:', cap.isOpened()); cap.release()"
# Should print: Camera: True
```

If first test works but second doesn't → Terminal needs camera permission!

## 🎯 Bottom Line

**You don't need camera monitor to use the system!**

The web interface works great for:
- Registering faces
- Manual face recognition
- Viewing attendance history
- Managing users

Camera monitor is optional for:
- Automatic attendance (hands-free)
- Continuous monitoring
- Entrance/exit tracking
