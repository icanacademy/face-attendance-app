# Quick Start Guide - Face Attendance System

## 🚀 How to Run

### Option 1: Double-Click (macOS)
Simply double-click one of these files:
- **`Start Face Attendance.command`** - Starts web server + camera monitor
- **`Start Server Only.command`** - Starts web server only (no camera)

### Option 2: Terminal Commands

#### Full System (Web + Camera)
```bash
cd /Users/icanacademy/face-attendance-app
./start_all.sh
```

#### Server Only (No Camera)
```bash
cd /Users/icanacademy/face-attendance-app
./start-server-only.sh
```

#### Manual Start
```bash
cd /Users/icanacademy/face-attendance-app
python3 server.py
```

## 🔗 Integration with Attendance-Checker

The face-attendance-app now **automatically syncs** with attendance-checker!

### How It Works:
1. Face is recognized → Attendance logged locally
2. Teacher info fetched from Notion (schedule, etc.)
3. Status determined (Present/Late)
4. **Automatically sent to attendance-checker** (port 3001)
5. Both systems stay in sync!

### Requirements:
- ✅ **attendance-checker must be running** on port 3001
- ✅ Face must be registered with Notion teacher link
- ✅ Teacher must exist in Notion database

### Check Integration Status:
The startup script will show:
```
✓ attendance-checker running on port 3001
✓ Integration enabled - attendance will sync to both systems
```

Or if offline:
```
⚠ attendance-checker NOT running on port 3001
⚠ Face attendance will work, but won't sync to attendance-checker
```

## 📊 What Gets Synced

When a face is recognized, the following data is sent to attendance-checker:

| Field | Example | Description |
|-------|---------|-------------|
| teacherId | `1abd37d6-6630-80f5-...` | Notion Page ID |
| teacherName | `[Edward] John Edward Padilla` | Full name |
| status | `present` or `late` | Based on schedule |
| startTime | `10am` | From Notion |
| endTime | `7pm` | From Notion |
| minutesLate | `15` or `null` | If late |
| date | `2025-10-31` | Current date |

## 🌐 Access Points

- **Face Attendance Web**: http://localhost:5001
- **Attendance Checker**: http://localhost:3001

## 📝 Typical Workflow

### Step 1: Start Both Systems
```bash
# Terminal 1 - Start attendance-checker
cd /Users/icanacademy/attendance-checker
npm start

# Terminal 2 - Start face-attendance
cd /Users/icanacademy/face-attendance-app
./start_all.sh
```

### Step 2: Register Faces
1. Go to http://localhost:5001
2. Click "Register Face" tab
3. Select teacher from dropdown (from Notion)
4. Start camera and capture face
5. Face is now linked to that teacher's Notion record

### Step 3: Automatic Attendance
- Camera monitor runs continuously
- Detects faces every 2 seconds
- Auto-logs TIME IN when face recognized
- Updates both systems + Notion

### Step 4: View Attendance
- **Face Attendance**: http://localhost:5001 (History tab)
- **Attendance Checker**: http://localhost:3001 (Reports)
- **Notion**: Check teacher's page

## 🛑 How to Stop

- Press **Ctrl+C** in the terminal
- Or press **`q`** in the camera monitor window

## ⚠️ Troubleshooting

### "Could not reach attendance-checker"
- Check if attendance-checker is running: `lsof -i:3001`
- Start it: `cd ~/attendance-checker && npm start`

### "Face not recognized"
- Ensure good lighting
- Look directly at camera
- Try re-registering with better conditions

### "Port 5001 already in use"
- Kill existing process: `lsof -ti:5001 | xargs kill -9`
- Or the script will do this automatically

## 📦 Data Storage

- **Face encodings**: `users.json`
- **Local attendance**: `attendance.json`
- **Synced attendance**: `~/attendance-checker/attendance.db` (SQLite)
- **Notion database**: Cloud (shared between both apps)

## ✅ Integration Status Check

To verify integration is working:
```bash
# Check if attendance-checker is running
curl http://localhost:3001/api/teachers

# Check if face-attendance server is running
curl http://localhost:5001/api/health
```

Both should return JSON responses.
