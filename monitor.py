#!/usr/bin/env python3
"""
Face Recognition Attendance Monitor - AUTO TIME IN MODE
Continuous camera monitoring for automatic attendance logging
Automatically logs TIME IN when face is detected
"""

import cv2
import face_recognition
import numpy as np
import json
import time
from datetime import datetime
import os
import subprocess
from notion_client import Client
from dotenv import load_dotenv
import threading
import requests

# Load environment variables
load_dotenv()

# Configuration
DB_FILE = 'attendance.json'
USERS_FILE = 'users.json'
RECOGNITION_COOLDOWN = 10  # 10 seconds cooldown for same person/action
SCAN_INTERVAL = 2  # Scan every 2 seconds
CAMERA_INDEX = 0  # Default camera
FRAME_WIDTH = 320  # Small resolution for monitoring only
FRAME_HEIGHT = 240  # Small resolution for monitoring only
FRAME_SKIP = 5  # Process every 5th frame for smooth display

# Initialize Notion client
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

notion = None
notion_enabled = False

if NOTION_API_KEY and NOTION_DATABASE_ID:
    try:
        notion = Client(auth=NOTION_API_KEY)
        notion_enabled = True
        print("✓ Notion integration enabled")
    except Exception as e:
        print(f"⚠ Notion integration failed: {e}")
        notion_enabled = False
else:
    print("ℹ Notion integration disabled")

# Attendance Checker Integration
ATTENDANCE_CHECKER_URL = 'http://localhost:3001/api/attendance'

def send_to_attendance_checker(teacher_id, teacher_name, date, status, start_time, end_time, minutes_late=None):
    """Send attendance data to attendance-checker app"""
    try:
        # Format status to lowercase for attendance-checker
        formatted_status = status.lower() if status else 'present'

        payload = {
            'attendance': [{
                'teacherId': teacher_id,
                'teacherName': teacher_name,
                'status': formatted_status,
                'startTime': start_time or '',
                'endTime': end_time or '',
                'minutesLate': minutes_late
            }],
            'date': date
        }

        response = requests.post(ATTENDANCE_CHECKER_URL, json=payload, timeout=5)

        if response.status_code == 200:
            print(f"✓ Sent to attendance-checker: {teacher_name} - {formatted_status}")
            return True
        else:
            print(f"⚠ Failed to send to attendance-checker: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"⚠ Could not reach attendance-checker: {e}")
        return False

# Track last time-in to prevent duplicates
last_timein_time = {}


def load_users():
    """Load registered users from file"""
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠ {USERS_FILE} not found. Please register users via web interface first.")
        return []


def save_attendance(record):
    """Save attendance record"""
    try:
        with open(DB_FILE, 'r') as f:
            records = json.load(f)
    except FileNotFoundError:
        records = []

    records.append(record)

    with open(DB_FILE, 'w') as f:
        json.dump(records, f, indent=2)


def get_teacher_schedule(notion_page_id):
    """Fetch teacher's schedule (start time, end time) from Notion"""
    if not notion_enabled or not notion_page_id:
        return None, None

    try:
        page = notion.pages.retrieve(page_id=notion_page_id)
        properties = page['properties']

        start_time = None
        end_time = None

        # Get Start Time
        if 'Start Time' in properties:
            start_prop = properties['Start Time']
            if start_prop['type'] == 'select' and start_prop['select']:
                start_time = start_prop['select']['name']

        # Get End Time
        if 'End Time' in properties:
            end_prop = properties['End Time']
            if end_prop['type'] == 'select' and end_prop['select']:
                end_time = end_prop['select']['name']

        return start_time, end_time

    except Exception as e:
        print(f"⚠ Error fetching schedule: {e}")
        return None, None


def parse_time(time_str):
    """Convert time string like '10am' to datetime.time object"""
    if not time_str:
        return None

    try:
        # Handle formats like "8am", "10am", "1pm", "3pm"
        time_str = time_str.lower().strip()

        if 'am' in time_str:
            hour = int(time_str.replace('am', ''))
            if hour == 12:
                hour = 0
        elif 'pm' in time_str:
            hour = int(time_str.replace('pm', ''))
            if hour != 12:
                hour += 12
        else:
            return None

        return datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)

    except:
        return None


def determine_status(arrival_time, start_time_str):
    """Determine if Present or Late based on arrival vs start time"""
    if not start_time_str:
        return "Present"  # Default if no schedule

    start_time = parse_time(start_time_str)
    if not start_time:
        return "Present"

    # No grace period - strict checking
    if arrival_time <= start_time:
        return "Present"
    else:
        return "Late"


def calculate_time_difference(arrival_time, start_time_str):
    """Calculate minutes early (negative) or late (positive)"""
    if not start_time_str:
        return 0

    start_time = parse_time(start_time_str)
    if not start_time:
        return 0

    diff_seconds = (arrival_time - start_time).total_seconds()
    return int(diff_seconds / 60)  # Convert to minutes


def update_notion_attendance(notion_page_id, teacher_name, status, arrival_time):
    """Update teacher's Notion page with Time In and Status"""
    if not notion_enabled or not notion_page_id:
        return False

    try:
        current_time_iso = arrival_time.isoformat()
        properties = {}

        # Update Time In
        properties['Time In'] = {
            'date': {
                'start': current_time_iso
            }
        }

        # Update Status (Present or Late)
        properties['Status'] = {
            'select': {
                'name': status
            }
        }

        # Update Last Attendance
        properties['Last Attendance'] = {
            'date': {
                'start': current_time_iso
            }
        }

        # Update the page
        notion.pages.update(
            page_id=notion_page_id,
            properties=properties
        )

        print(f"✓ Updated Notion for {teacher_name} (TIME IN - {status})")
        return True

    except Exception as e:
        print(f"⚠ Error updating Notion: {e}")
        return False


def speak(text):
    """Speak text using macOS 'say' command"""
    try:
        subprocess.run(['say', text], check=False)
        print(f"🔊 Speaking: {text}")
    except Exception as e:
        print(f"⚠ Speech error: {e}")


def recognize_face(frame, known_users):
    """Recognize face in frame and return match"""
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    if not face_encodings:
        return None

    unknown_encoding = face_encodings[0]

    best_match_name = None
    best_match_distance = float('inf')
    best_match_user = None

    for user in known_users:
        known_encoding = np.array(user['encoding'])
        distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]

        if distance < best_match_distance:
            best_match_distance = distance
            best_match_name = user['name']
            best_match_user = user

    # STRICTER threshold for better accuracy (lower = more strict)
    THRESHOLD = 0.4  # Changed from 0.6 to 0.4 for stricter matching

    if best_match_distance > THRESHOLD:
        # Log rejected faces for debugging
        print(f"⚠ Face detected but not recognized (distance: {best_match_distance:.3f}, threshold: {THRESHOLD})")
        print(f"  Closest match would be: {best_match_name} (but rejected)")
        return None

    return best_match_user, best_match_distance


def main():
    """Main monitoring loop"""
    print("=" * 60)
    print("Face Recognition Attendance Monitor - AUTO TIME IN")
    print("=" * 60)
    print(f"Camera Index: {CAMERA_INDEX}")
    print(f"Resolution: {FRAME_WIDTH}x{FRAME_HEIGHT}")
    print(f"Mode: Automatic TIME IN on face detection")
    print(f"Cooldown: {RECOGNITION_COOLDOWN} seconds")
    print(f"Notion: {'✓ Enabled' if notion_enabled else '✗ Disabled'}")
    print("=" * 60)
    print()

    # Load registered users
    print("Loading registered users...")
    users = load_users()
    if not users:
        print("❌ No registered users found. Please register users via web interface.")
        return

    print(f"✓ Loaded {len(users)} registered user(s)")
    for user in users:
        print(f"  • {user['name']}")
    print()

    # Initialize camera
    print(f"Starting camera (index {CAMERA_INDEX})...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("❌ Error: Could not open camera")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 15)  # Reduce FPS for better performance
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer lag

    print("✓ Camera started successfully")
    print()
    print("🎥 Monitoring active - Press 'q' to quit")
    print("⚡ Auto TIME IN mode - no gestures needed")
    print("=" * 60)
    print()

    speak("Attendance system activated. Automatic time in mode.")

    last_scan_time = 0
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠ Failed to grab frame")
                break

            frame_count += 1
            current_time = time.time()
            display_frame = frame.copy()

            # Scan for faces every SCAN_INTERVAL seconds
            if current_time - last_scan_time >= SCAN_INTERVAL:
                # Only process every Nth frame to reduce lag
                if frame_count % FRAME_SKIP == 0:
                    last_scan_time = current_time

                    # Upscale frame for better face recognition accuracy
                    # (display is small but recognition needs detail)
                    recognition_frame = cv2.resize(frame, (640, 480))
                    result = recognize_face(recognition_frame, users)

                    if result:
                        matched_user, confidence = result
                        name = matched_user['name']

                        # Check cooldown
                        if name in last_timein_time:
                            time_since = current_time - last_timein_time[name]
                            if time_since < RECOGNITION_COOLDOWN:
                                remaining = int(RECOGNITION_COOLDOWN - time_since)
                                print(f"⏱  {name} - Already logged ({remaining}s cooldown)")
                                continue

                        # Mark as logged immediately to prevent duplicates
                        last_timein_time[name] = current_time

                        print(f"👤 Face detected: {name}")

                        # Process attendance in background thread to avoid video freeze
                        def process_attendance():
                            arrival_time = datetime.now()

                            # Get schedule from Notion (this is slow!)
                            start_time_str, end_time_str = get_teacher_schedule(matched_user.get('notion_page_id'))

                            # Determine status (Present/Late)
                            status = "Present"
                            minutes_diff = 0
                            if start_time_str:
                                status = determine_status(arrival_time, start_time_str)
                                minutes_diff = calculate_time_difference(arrival_time, start_time_str)

                            # Log attendance
                            attendance_record = {
                                'name': name,
                                'timestamp': arrival_time.isoformat(),
                                'confidence': float(1 - confidence),
                                'action': 'time_in',
                                'status': status,
                                'schedule_start': start_time_str,
                                'minutes_difference': minutes_diff
                            }
                            save_attendance(attendance_record)

                            # Update Notion (this is slow!)
                            notion_updated = False
                            if matched_user.get('notion_page_id'):
                                notion_updated = update_notion_attendance(
                                    matched_user['notion_page_id'],
                                    name,
                                    status,
                                    arrival_time
                                )

                            # Send to attendance-checker
                            checker_updated = False
                            if matched_user.get('notion_page_id'):
                                current_date = arrival_time.strftime('%Y-%m-%d')
                                minutes_late = minutes_diff if minutes_diff > 0 else None
                                checker_updated = send_to_attendance_checker(
                                    matched_user['notion_page_id'],
                                    name,
                                    current_date,
                                    status,
                                    start_time_str,
                                    end_time_str,
                                    minutes_late
                                )

                            # Announce
                            if status == "Late":
                                speak(f"{name}, time in recorded. You are {abs(minutes_diff)} minutes late.")
                            else:
                                speak(f"{name}, time in recorded. Welcome!")

                            # Console output
                            print(f"✓ {name} - TIME IN logged")
                            print(f"  Status: {status}")
                            if start_time_str:
                                print(f"  Schedule: {start_time_str}")
                                if minutes_diff < 0:
                                    print(f"  Arrived: {abs(minutes_diff)} minutes early")
                                elif minutes_diff > 0:
                                    print(f"  Arrived: {minutes_diff} minutes late")
                            if notion_updated:
                                print(f"  └─ Notion updated")
                            if checker_updated:
                                print(f"  └─ Attendance-checker updated")
                            print()

                        # Run in background thread - video continues smoothly!
                        threading.Thread(target=process_attendance, daemon=True).start()

            # Display status - smaller text for small window
            cv2.putText(display_frame, "MONITORING", (5, 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(display_frame, f"Users: {len(users)}", (5, 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(display_frame, "Press 'q' to quit", (5, 230),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)

            # Show small window
            cv2.imshow('Attendance Monitor', display_frame)

            # Position window in top-right corner (optional)
            cv2.moveWindow('Attendance Monitor', 1000, 50)

            # Press 'q' to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n⏹  Stopping monitor...")
                speak("Attendance monitoring stopped.")
                break

    except KeyboardInterrupt:
        print("\n⏹  Stopped by user (Ctrl+C)")
        speak("Attendance monitoring stopped.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✓ Camera released")
        print("✓ Monitor stopped")


if __name__ == '__main__':
    main()
