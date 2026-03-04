// Configuration
const API_URL = 'http://localhost:5001/api';

// Global variables
let registerStream = null;
let serverConnected = false;

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    await checkServerConnection();
    setupNavigation();
    setupRegisterPage();
    setupHistoryPage();
    setupUsersPage();
    loadNotionTeachers();
});

// Check if backend server is running
async function checkServerConnection() {
    const loadingEl = document.getElementById('loading');
    const statusEl = document.getElementById('server-status');

    try {
        const response = await fetch(`${API_URL}/health`);
        if (response.ok) {
            serverConnected = true;
            loadingEl.classList.add('hidden');
            statusEl.textContent = 'Server Connected';
            console.log('Connected to backend server');
        } else {
            throw new Error('Server not responding');
        }
    } catch (error) {
        console.error('Cannot connect to server:', error);
        loadingEl.querySelector('p').textContent = 'Cannot connect to server. Please start the backend (python server.py)';
        statusEl.textContent = 'Server Offline';
    }
}

// Navigation setup
function setupNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    const pages = document.querySelectorAll('.page');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetPage = btn.dataset.page;

            // Stop camera when switching pages
            stopAllStreams();

            // Update active states
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            pages.forEach(page => {
                page.classList.remove('active');
                if (page.id === `${targetPage}-page`) {
                    page.classList.add('active');
                }
            });

            // Load data based on page
            if (targetPage === 'history') {
                displayAttendanceHistory();
                updateStats();
            } else if (targetPage === 'users') {
                displayRegisteredUsersGrid();
            }
        });
    });
}

// Register page setup
function setupRegisterPage() {
    const startCameraBtn = document.getElementById('start-register-camera');
    const captureFaceBtn = document.getElementById('capture-face');
    const video = document.getElementById('register-video');
    const canvas = document.getElementById('register-canvas');
    const usernameInput = document.getElementById('username');
    const teacherSelect = document.getElementById('teacher-select');
    const statusEl = document.getElementById('register-status');

    startCameraBtn.addEventListener('click', async () => {
        try {
            registerStream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: 'user' }
            });
            video.srcObject = registerStream;
            captureFaceBtn.disabled = false;
            startCameraBtn.disabled = true;
            showStatus(statusEl, 'Camera started. Position face in frame and click Capture.', 'show');
        } catch (error) {
            console.error('Error accessing camera:', error);
            showStatus(statusEl, 'Error accessing camera. Please grant permissions.', 'error');
        }
    });

    captureFaceBtn.addEventListener('click', async () => {
        const manualName = usernameInput.value.trim();
        const selectedTeacherId = teacherSelect.value;
        const selectedOption = teacherSelect.options[teacherSelect.selectedIndex];
        const selectedTeacherName = selectedOption.dataset.teacherName;

        let username = selectedTeacherName || manualName;
        let notionPageId = selectedTeacherId || null;

        if (!username) {
            showStatus(statusEl, 'Please select a teacher or enter a name.', 'error');
            return;
        }

        if (!serverConnected) {
            showStatus(statusEl, 'Server not connected.', 'error');
            return;
        }

        showStatus(statusEl, 'Capturing and processing face...', 'show');
        captureFaceBtn.disabled = true;

        try {
            const imageData = captureImageFromVideo(video, canvas);

            const registrationData = {
                name: username,
                image: imageData
            };

            if (notionPageId) {
                registrationData.notion_page_id = notionPageId;
            }

            const response = await fetch(`${API_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(registrationData)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                const notionStatus = result.user.notion_linked ? ' (Linked to Notion)' : '';
                showStatus(statusEl, `Success! ${username} registered${notionStatus}`, 'success');

                setTimeout(() => {
                    usernameInput.value = '';
                    teacherSelect.selectedIndex = 0;
                    stopStream(registerStream);
                    registerStream = null;
                    video.srcObject = null;
                    startCameraBtn.disabled = false;
                    captureFaceBtn.disabled = true;
                    statusEl.className = 'status';
                    loadNotionTeachers();
                }, 2000);
            } else {
                showStatus(statusEl, result.error || 'Registration failed.', 'error');
                captureFaceBtn.disabled = false;
            }

        } catch (error) {
            console.error('Error during registration:', error);
            showStatus(statusEl, 'Error during registration.', 'error');
            captureFaceBtn.disabled = false;
        }
    });
}

// History page setup
function setupHistoryPage() {
    const clearBtn = document.getElementById('clear-history');
    const refreshBtn = document.getElementById('refresh-history');
    const filterSelect = document.getElementById('user-filter');
    const dateFilter = document.getElementById('date-filter');

    clearBtn.addEventListener('click', async () => {
        if (confirm('Clear all attendance history?')) {
            try {
                const response = await fetch(`${API_URL}/attendance`, { method: 'DELETE' });
                if (response.ok) {
                    displayAttendanceHistory();
                    updateStats();
                }
            } catch (error) {
                console.error('Error clearing history:', error);
            }
        }
    });

    refreshBtn.addEventListener('click', () => {
        displayAttendanceHistory();
        updateStats();
        updateUserFilterDropdown();
    });

    filterSelect.addEventListener('change', () => displayAttendanceHistory());
    dateFilter.addEventListener('change', () => displayAttendanceHistory());
}

// Users page setup
function setupUsersPage() {
    // Users are loaded when page is activated
}

// Display attendance history with table
async function displayAttendanceHistory() {
    const listEl = document.getElementById('attendance-list');
    const filterSelect = document.getElementById('user-filter');
    const dateFilter = document.getElementById('date-filter');

    try {
        const response = await fetch(`${API_URL}/attendance`);
        const result = await response.json();

        if (!response.ok || !result.success) {
            listEl.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">Error loading records</div></div>';
            return;
        }

        let records = result.records;

        // Filter by user
        const selectedUser = filterSelect.value;
        if (selectedUser !== 'all') {
            records = records.filter(r => r.name === selectedUser);
        }

        // Filter by date
        const selectedDate = dateFilter.value;
        if (selectedDate) {
            records = records.filter(r => {
                const recordDate = new Date(r.timestamp).toISOString().split('T')[0];
                return recordDate === selectedDate;
            });
        }

        if (records.length === 0) {
            listEl.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-text">No attendance records found</div></div>';
            return;
        }

        // Sort by timestamp (newest first)
        records.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        // Build table
        const tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Date & Time</th>
                        <th>Action</th>
                        <th>Status</th>
                        <th>Schedule</th>
                        <th>Early/Late</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
                    ${records.map(record => {
                        const confidence = (record.confidence * 100).toFixed(1);
                        const confidenceClass = confidence >= 90 ? 'high' : 'medium';

                        // Action badge
                        const action = record.action || '-';
                        const actionClass = action === 'time_in' ? 'badge-success' : action === 'time_out' ? 'badge-danger' : '';
                        const actionLabel = action === 'time_in' ? 'TIME IN' : action === 'time_out' ? 'TIME OUT' : '-';

                        // Status badge
                        const status = record.status || '-';
                        const statusClass = status === 'Present' ? 'badge-success' : status === 'Late' ? 'badge-warning' : '';

                        // Schedule
                        const schedule = record.schedule_start || '-';

                        // Minutes difference
                        let timeDiff = '-';
                        if (record.minutes_difference !== undefined && record.action === 'time_in') {
                            const mins = record.minutes_difference;
                            if (mins < 0) {
                                timeDiff = `${Math.abs(mins)} min early`;
                            } else if (mins > 0) {
                                timeDiff = `${mins} min late`;
                            } else {
                                timeDiff = 'On time';
                            }
                        }

                        return `
                            <tr>
                                <td><strong>${record.name}</strong></td>
                                <td>${new Date(record.timestamp).toLocaleString()}</td>
                                <td><span class="badge ${actionClass}">${actionLabel}</span></td>
                                <td><span class="badge ${statusClass}">${status}</span></td>
                                <td>${schedule}</td>
                                <td>${timeDiff}</td>
                                <td><span class="confidence ${confidenceClass}">${confidence}%</span></td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        `;

        listEl.innerHTML = tableHTML;

    } catch (error) {
        console.error('Error loading attendance:', error);
        listEl.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">Error loading records</div></div>';
    }
}

// Update statistics
async function updateStats() {
    try {
        const [attendanceRes, usersRes] = await Promise.all([
            fetch(`${API_URL}/attendance`),
            fetch(`${API_URL}/users`)
        ]);

        const attendance = await attendanceRes.json();
        const users = await usersRes.json();

        if (attendance.success && users.success) {
            const records = attendance.records;

            // Total check-ins
            document.getElementById('total-checkins').textContent = records.length;

            // Unique users
            document.getElementById('unique-users').textContent = users.users.length;

            // Today's check-ins
            const today = new Date().toDateString();
            const todayCount = records.filter(r =>
                new Date(r.timestamp).toDateString() === today
            ).length;
            document.getElementById('today-checkins').textContent = todayCount;

            // Average confidence
            if (records.length > 0) {
                const avgConf = records.reduce((sum, r) => sum + r.confidence, 0) / records.length;
                document.getElementById('avg-confidence').textContent = (avgConf * 100).toFixed(0) + '%';
            } else {
                document.getElementById('avg-confidence').textContent = '0%';
            }

            // Update filter dropdown
            updateUserFilterDropdown();
        }
    } catch (error) {
        console.error('Error updating stats:', error);
    }
}

// Update user filter dropdown
async function updateUserFilterDropdown() {
    const filterSelect = document.getElementById('user-filter');

    try {
        const response = await fetch(`${API_URL}/users`);
        const result = await response.json();

        if (response.ok && result.success) {
            const currentValue = filterSelect.value;
            filterSelect.innerHTML = '<option value="all">All Users</option>';

            result.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.name;
                option.textContent = user.name;
                filterSelect.appendChild(option);
            });

            filterSelect.value = currentValue;
        }
    } catch (error) {
        console.error('Error loading users for filter:', error);
    }
}

// Load Notion teachers into dropdown
async function loadNotionTeachers() {
    const teacherSelect = document.getElementById('teacher-select');

    try {
        const response = await fetch(`${API_URL}/notion/teachers`);
        const result = await response.json();

        if (result.success && result.teachers && result.teachers.length > 0) {
            teacherSelect.innerHTML = '<option value="">-- Select a teacher --</option>';

            const sortedTeachers = result.teachers.sort((a, b) =>
                a.name.localeCompare(b.name)
            );

            sortedTeachers.forEach(teacher => {
                const option = document.createElement('option');
                option.value = teacher.id;

                if (teacher.has_face) {
                    option.textContent = `✓ ${teacher.name}`;
                    option.style.color = '#10b981';
                    option.style.fontWeight = '600';
                } else {
                    option.textContent = teacher.name;
                }

                option.dataset.teacherName = teacher.name;
                teacherSelect.appendChild(option);
            });

            console.log(`✓ Loaded ${result.teachers.length} Active teachers`);
        } else if (result.notion_enabled === false) {
            teacherSelect.innerHTML = '<option value="">Notion integration disabled</option>';
            teacherSelect.disabled = true;
        } else {
            teacherSelect.innerHTML = '<option value="">No teachers found</option>';
        }
    } catch (error) {
        console.error('Error loading Notion teachers:', error);
        teacherSelect.innerHTML = '<option value="">Error loading teachers</option>';
    }
}

// Display registered users in grid
async function displayRegisteredUsersGrid() {
    const gridEl = document.getElementById('registered-users-grid');

    try {
        const response = await fetch(`${API_URL}/users`);
        const result = await response.json();

        if (!response.ok || !result.success) {
            gridEl.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">Error loading users</div></div>';
            return;
        }

        const users = result.users;

        if (users.length === 0) {
            gridEl.innerHTML = '<div class="empty-state"><div class="empty-state-icon">👤</div><div class="empty-state-text">No registered faces yet</div></div>';
            return;
        }

        users.sort((a, b) => a.name.localeCompare(b.name));

        gridEl.innerHTML = users.map(user => {
            const initials = user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
            return `
                <div class="user-card">
                    <div class="user-card-header">
                        <div class="user-avatar">${initials}</div>
                        <div class="user-info">
                            <div class="user-name">${user.name}</div>
                            <div class="user-meta">
                                ${new Date(user.registered_at).toLocaleDateString()}
                                ${user.notion_linked ? ' • <span style="color: #10b981;">Linked</span>' : ''}
                            </div>
                        </div>
                    </div>
                    <div class="user-card-actions">
                        <button class="btn btn-danger" onclick="deleteUser('${user.name.replace(/'/g, "\\'")}')">
                            Delete
                        </button>
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading registered users:', error);
        gridEl.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">Error loading users</div></div>';
    }
}

// Delete a registered user
async function deleteUser(userName) {
    if (!confirm(`Delete face registration for "${userName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/users/${encodeURIComponent(userName)}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (response.ok && result.success) {
            displayRegisteredUsersGrid();
            loadNotionTeachers();
            updateUserFilterDropdown();
        } else {
            alert(`Error: ${result.error || 'Failed to delete user'}`);
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('Error deleting user.');
    }
}

// Utility: Capture image from video
function captureImageFromVideo(video, canvas) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.95);
}

// Utility: Show status message
function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status ${type}`;
}

// Utility: Stop video stream
function stopStream(stream) {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
}

// Utility: Stop all streams
function stopAllStreams() {
    stopStream(registerStream);
    registerStream = null;

    const videos = document.querySelectorAll('video');
    videos.forEach(video => video.srcObject = null);

    const canvases = document.querySelectorAll('canvas');
    canvases.forEach(canvas => {
        const ctx = canvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    });

    const startRegBtn = document.getElementById('start-register-camera');
    const captureBtn = document.getElementById('capture-face');
    if (startRegBtn) startRegBtn.disabled = false;
    if (captureBtn) captureBtn.disabled = true;
}

// Make deleteUser available globally
window.deleteUser = deleteUser;
