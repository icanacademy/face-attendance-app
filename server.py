from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import face_recognition
import base64
import json
import os
from datetime import datetime
from PIL import Image
import io
import numpy as np
from notion_client import Client
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)

# Files for storing data
DB_FILE = 'attendance.json'
USERS_FILE = 'users.json'

# Initialize files
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w') as f:
        json.dump([], f)

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump([], f)

# Initialize Notion client
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

notion = None
notion_enabled = False

if NOTION_API_KEY and NOTION_DATABASE_ID:
    try:
        notion = Client(auth=NOTION_API_KEY)
        notion_enabled = True
        print(f"✓ Notion integration enabled")
        print(f"  Database ID: {NOTION_DATABASE_ID}")
    except Exception as e:
        print(f"⚠ Notion integration failed: {e}")
        notion_enabled = False
else:
    print("ℹ Notion integration disabled (no credentials found)")


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


def base64_to_image(base64_string):
    """Convert base64 string to numpy array (image)"""
    if 'base64,' in base64_string:
        base64_string = base64_string.split('base64,')[1]

    img_data = base64.b64decode(base64_string)
    img = Image.open(io.BytesIO(img_data))
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    return np.array(img)


def load_users():
    """Load registered users from file"""
    with open(USERS_FILE, 'r') as f:
        return json.load(f)


def save_user(user_data):
    """Save new user to file"""
    users = load_users()

    # Check if user already exists and update
    existing_index = None
    for i, user in enumerate(users):
        if user['name'].lower() == user_data['name'].lower():
            existing_index = i
            break

    if existing_index is not None:
        users[existing_index] = user_data
    else:
        users.append(user_data)

    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)


def load_attendance():
    """Load attendance records"""
    with open(DB_FILE, 'r') as f:
        return json.load(f)


def save_attendance(record):
    """Save attendance record"""
    records = load_attendance()
    records.append(record)
    with open(DB_FILE, 'w') as f:
        json.dump(records, f, indent=2)


# Notion Integration Functions
def get_notion_teachers():
    """Fetch list of ACTIVE teachers from Notion database with pagination support"""
    if not notion_enabled:
        return []

    try:
        teachers = []
        has_more = True
        start_cursor = None

        # Handle pagination to get ALL teachers
        while has_more:
            query_params = {
                'database_id': NOTION_DATABASE_ID,
                'page_size': 100,  # Maximum allowed per request
                'filter': {
                    'property': 'Status',
                    'select': {
                        'equals': 'Active'
                    }
                }
            }

            if start_cursor:
                query_params['start_cursor'] = start_cursor

            response = notion.databases.query(**query_params)

            for page in response['results']:
                # Get the title property (usually "Name")
                title_prop = None
                for prop_name, prop_value in page['properties'].items():
                    if prop_value['type'] == 'title' and prop_value['title']:
                        title_prop = prop_value['title'][0]['plain_text']
                        break

                if title_prop:
                    teachers.append({
                        'id': page['id'],
                        'name': title_prop
                    })
                else:
                    # Log pages without a title for debugging
                    print(f"⚠ Skipping page {page['id']}: No title property found")

            # Check if there are more pages
            has_more = response.get('has_more', False)
            start_cursor = response.get('next_cursor')

        print(f"✓ Fetched {len(teachers)} ACTIVE teachers from Notion")
        return teachers
    except Exception as e:
        print(f"Error fetching teachers from Notion: {e}")
        return []


def update_notion_attendance(notion_page_id, teacher_name):
    """Update teacher's Notion page with attendance"""
    if not notion_enabled or not notion_page_id:
        return False

    try:
        current_time = datetime.now().isoformat()

        # Prepare properties to update
        properties = {}

        # Update Last Attendance (Date property)
        properties['Last Attendance'] = {
            'date': {
                'start': current_time
            }
        }

        # Try to increment Total Check-ins if it exists
        try:
            page = notion.pages.retrieve(page_id=notion_page_id)
            if 'Total Check-ins' in page['properties']:
                current_count = page['properties']['Total Check-ins'].get('number', 0) or 0
                properties['Total Check-ins'] = {
                    'number': current_count + 1
                }
        except:
            pass

        # Update Status to Present
        properties['Status'] = {
            'select': {
                'name': 'Present'
            }
        }

        # Update the page
        notion.pages.update(
            page_id=notion_page_id,
            properties=properties
        )

        print(f"✓ Updated Notion for {teacher_name}")
        return True

    except Exception as e:
        print(f"Error updating Notion: {e}")
        return False


@app.route('/')
def serve_index():
    """Serve the main HTML interface"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, etc.)"""
    return send_from_directory('.', filename)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Server is running',
        'notion_enabled': notion_enabled
    })


@app.route('/api/notion/teachers', methods=['GET'])
def get_teachers():
    """Get list of teachers from Notion with registration status"""
    teachers = get_notion_teachers()

    # Load registered users to check which teachers already have faces
    registered_users = load_users()
    registered_names = {user['name'].lower() for user in registered_users}

    # Add registration status to each teacher
    for teacher in teachers:
        teacher['has_face'] = teacher['name'].lower() in registered_names

    return jsonify({
        'success': True,
        'teachers': teachers,
        'notion_enabled': notion_enabled
    })


@app.route('/api/register', methods=['POST'])
def register_user():
    """Register a new user with their face"""
    try:
        data = request.json
        name = data.get('name')
        notion_page_id = data.get('notion_page_id')  # Optional
        image_data = data.get('image')

        if not name or not image_data:
            return jsonify({'error': 'Name and image are required'}), 400

        # Convert base64 to image
        img = base64_to_image(image_data)

        # Find face encodings
        face_encodings = face_recognition.face_encodings(img)

        if len(face_encodings) == 0:
            return jsonify({'error': 'No face detected in image. Please try again with better lighting.'}), 400

        if len(face_encodings) > 1:
            return jsonify({'error': 'Multiple faces detected. Please ensure only one face is in the frame.'}), 400

        # Get the face encoding (128-dimensional)
        face_encoding = face_encodings[0]

        # Save user data
        user_data = {
            'name': name,
            'encoding': face_encoding.tolist(),
            'notion_page_id': notion_page_id,
            'registered_at': datetime.now().isoformat()
        }
        save_user(user_data)

        return jsonify({
            'success': True,
            'message': f'User {name} registered successfully',
            'user': {
                'name': name,
                'registered_at': user_data['registered_at'],
                'notion_linked': notion_page_id is not None
            }
        })

    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    """Recognize face and log attendance"""
    try:
        data = request.json
        image_data = data.get('image')

        if not image_data:
            return jsonify({'error': 'Image is required'}), 400

        # Get registered users
        users = load_users()
        if not users:
            return jsonify({'error': 'No registered users found'}), 400

        # Convert base64 to image
        img = base64_to_image(image_data)

        # Find face encodings in the image
        face_encodings = face_recognition.face_encodings(img)

        if len(face_encodings) == 0:
            return jsonify({
                'success': False,
                'error': 'No face detected. Please try again.'
            }), 404

        # Use the first face found
        unknown_encoding = face_encodings[0]

        # Compare with all registered faces
        best_match_name = None
        best_match_distance = float('inf')
        best_match_user = None

        for user in users:
            known_encoding = np.array(user['encoding'])

            # Calculate face distance (lower is better)
            distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]

            if distance < best_match_distance:
                best_match_distance = distance
                best_match_name = user['name']
                best_match_user = user

        # Threshold for recognition (0.6 is standard, lower is more strict)
        THRESHOLD = 0.6

        if best_match_distance > THRESHOLD:
            return jsonify({
                'success': False,
                'error': 'Face not recognized. Please register first.'
            }), 404

        # Calculate confidence (1 - distance = similarity)
        confidence = 1 - best_match_distance

        # Get current date and time
        current_time = datetime.now()
        current_date = current_time.strftime('%Y-%m-%d')

        # Get teacher schedule from Notion if available
        start_time = None
        end_time = None
        teacher_status = 'Present'
        minutes_late = None

        if best_match_user.get('notion_page_id'):
            try:
                page = notion.pages.retrieve(page_id=best_match_user['notion_page_id'])
                properties = page['properties']

                # Get Start Time
                if 'Start Time' in properties and properties['Start Time']['select']:
                    start_time = properties['Start Time']['select']['name']

                # Get End Time
                if 'End Time' in properties and properties['End Time']['select']:
                    end_time = properties['End Time']['select']['name']

                # Determine if late based on start time
                if start_time:
                    # Parse time like "8am", "10am", "1pm"
                    time_str = start_time.lower().strip()
                    if 'am' in time_str:
                        hour = int(time_str.replace('am', ''))
                        if hour == 12:
                            hour = 0
                    elif 'pm' in time_str:
                        hour = int(time_str.replace('pm', ''))
                        if hour != 12:
                            hour += 12
                    else:
                        hour = None

                    if hour is not None:
                        schedule_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
                        if current_time > schedule_time:
                            diff_seconds = (current_time - schedule_time).total_seconds()
                            minutes_late = int(diff_seconds / 60)
                            teacher_status = 'Late'
            except Exception as e:
                print(f"⚠ Error fetching schedule: {e}")

        # Log attendance
        attendance_record = {
            'name': best_match_name,
            'timestamp': current_time.isoformat(),
            'confidence': float(confidence)
        }
        save_attendance(attendance_record)

        # Update Notion if linked
        notion_updated = False
        if best_match_user.get('notion_page_id'):
            notion_updated = update_notion_attendance(
                best_match_user['notion_page_id'],
                best_match_name
            )

        # Send to attendance-checker
        checker_updated = False
        if best_match_user.get('notion_page_id'):
            checker_updated = send_to_attendance_checker(
                best_match_user['notion_page_id'],
                best_match_name,
                current_date,
                teacher_status,
                start_time,
                end_time,
                minutes_late
            )

        return jsonify({
            'success': True,
            'user': best_match_name,
            'confidence': float(confidence),
            'timestamp': attendance_record['timestamp'],
            'notion_updated': notion_updated,
            'attendance_checker_updated': checker_updated
        })

    except Exception as e:
        return jsonify({'error': f'Recognition failed: {str(e)}'}), 500


@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    """Get all attendance records"""
    try:
        records = load_attendance()
        return jsonify({'success': True, 'records': records})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/attendance', methods=['DELETE'])
def clear_attendance():
    """Clear all attendance records"""
    try:
        with open(DB_FILE, 'w') as f:
            json.dump([], f)
        return jsonify({'success': True, 'message': 'Attendance cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all registered users"""
    try:
        users = load_users()
        # Remove encoding from response for security
        users_safe = [{
            'name': u['name'],
            'registered_at': u['registered_at'],
            'notion_linked': u.get('notion_page_id') is not None
        } for u in users]
        return jsonify({'success': True, 'users': users_safe})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<name>', methods=['DELETE'])
def delete_user(name):
    """Delete a registered user by name"""
    try:
        users = load_users()

        # Find and remove user
        original_count = len(users)
        users = [u for u in users if u['name'].lower() != name.lower()]

        if len(users) == original_count:
            return jsonify({'error': f'User {name} not found'}), 404

        # Save updated users list
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)

        print(f"✓ Deleted user: {name}")
        return jsonify({
            'success': True,
            'message': f'User {name} deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Face Recognition Attendance System - Backend Server")
    print("=" * 60)
    print("Using: face_recognition library (dlib-based)")
    print("Accuracy: 99.38% on LFW benchmark")
    if notion_enabled:
        print("Notion: ✓ Connected")
    else:
        print("Notion: ✗ Not configured")
    print("Server starting on http://localhost:5001")
    print("\nEndpoints:")
    print("  POST /api/register          - Register new user")
    print("  POST /api/recognize         - Recognize face and log time")
    print("  GET  /api/attendance        - Get attendance records")
    print("  GET  /api/users             - Get registered users")
    print("  GET  /api/notion/teachers   - Get Notion teachers list")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5001)
