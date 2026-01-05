/**
 * Attendance Module
 * Clock In/Out, GPS, QR Code, Face Recognition
 * Sistem Absensi Karyawan 2025
 */

// ============================================
// STATE
// ============================================
let currentLocation = null;
let cameraStream = null;
let todayAttendance = null;

// ============================================
// INITIALIZE ATTENDANCE PAGE
// ============================================
async function initAttendancePage() {
    // Set current date
    const dateElement = document.getElementById('currentDate');
    const dateDisplay = document.getElementById('dateDisplay');
    const today = getCurrentDateFormatted();
    
    if (dateElement) dateElement.textContent = today;
    if (dateDisplay) dateDisplay.textContent = today;
    
    // Start live clock
    startLiveClock();
    
    // Setup method tabs
    setupMethodTabs();
    
    // Load today's attendance
    await loadTodayAttendance();
    
    // Start getting location
    initLocation();
    
    // Load week history
    loadWeekHistory();
}

// ============================================
// METHOD TABS
// ============================================
function setupMethodTabs() {
    const tabs = document.querySelectorAll('.method-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active from all tabs
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Hide all content
            document.querySelectorAll('.method-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Show selected content
            const method = tab.dataset.method;
            const content = document.getElementById(`method-${method}`);
            if (content) content.classList.add('active');
            
            // Stop camera if switching away from face
            if (method !== 'face' && cameraStream) {
                stopCamera();
            }
        });
    });
}

// ============================================
// LOAD TODAY ATTENDANCE
// ============================================
async function loadTodayAttendance() {
    try {
        const result = await api.get('/attendance/today');
        
        if (result.success) {
            todayAttendance = result.data;
            updateAttendanceDisplay();
        }
        
    } catch (error) {
        console.error('Error loading attendance:', error);
    }
}

function updateAttendanceDisplay() {
    const clockInTime = document.getElementById('clockInTime');
    const clockOutTime = document.getElementById('clockOutTime');
    const btnClockIn = document.getElementById('btnClockIn');
    const btnClockOut = document.getElementById('btnClockOut');
    const noteElement = document.getElementById('attendanceNote');
    
    if (todayAttendance && todayAttendance.clock_in) {
        // Already clocked in
        if (clockInTime) {
            clockInTime.textContent = formatTime(todayAttendance.clock_in);
        }
        
        if (btnClockIn) btnClockIn.style.display = 'none';
        if (btnClockOut) btnClockOut.style.display = '';
        
        // Show late note
        if (noteElement && todayAttendance.late_minutes > 0) {
            noteElement.className = 'attendance-note late';
            noteElement.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Terlambat ${todayAttendance.late_minutes} menit`;
        }
        
        if (todayAttendance.clock_out) {
            // Already clocked out
            if (clockOutTime) {
                clockOutTime.textContent = formatTime(todayAttendance.clock_out);
            }
            
            if (btnClockOut) btnClockOut.style.display = 'none';
            
            if (noteElement) {
                noteElement.className = 'attendance-note success';
                noteElement.innerHTML = '<i class="fas fa-check-circle"></i> Absensi hari ini sudah lengkap';
            }
        }
        
    } else {
        // Not clocked in yet
        if (clockInTime) clockInTime.textContent = '--:--';
        if (clockOutTime) clockOutTime.textContent = '--:--';
        if (btnClockIn) btnClockIn.style.display = '';
        if (btnClockOut) btnClockOut.style.display = 'none';
    }
}

// ============================================
// LOCATION / GPS
// ============================================
async function initLocation() {
    const locationInfo = document.getElementById('locationInfo');
    
    if (!locationInfo) return;
    
    try {
        locationInfo.innerHTML = `
            <div class="location-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Mendapatkan lokasi GPS...</p>
            </div>
        `;
        
        currentLocation = await getCurrentLocation();
        const address = await getAddressFromCoords(currentLocation.latitude, currentLocation.longitude);
        
        locationInfo.innerHTML = `
            <div class="location-result">
                <i class="fas fa-map-marker-alt"></i>
                <div class="location-details">
                    <h5>Lokasi Terdeteksi</h5>
                    <p>${address}</p>
                    <span class="location-status valid">
                        <i class="fas fa-check"></i> GPS Aktif (Akurasi: ${Math.round(currentLocation.accuracy)}m)
                    </span>
                </div>
            </div>
        `;
        
    } catch (error) {
        locationInfo.innerHTML = `
            <div class="location-result">
                <i class="fas fa-exclamation-triangle" style="color: var(--danger);"></i>
                <div class="location-details">
                    <h5>GPS Tidak Tersedia</h5>
                    <p>${error.message}</p>
                    <button class="btn btn-sm btn-outline" onclick="initLocation()">
                        <i class="fas fa-redo"></i> Coba Lagi
                    </button>
                </div>
            </div>
        `;
    }
}

// ============================================
// CLOCK IN
// ============================================
async function clockIn(method = 'gps') {
    const btn = document.getElementById('btnClockIn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    }
    
    try {
        const workType = document.querySelector('input[name="workType"]:checked')?.value || 'wfo';
        
        const data = {
            method: method,
            work_type: workType,
            notes: ''
        };
        
        // Add location if available
        if (currentLocation) {
            data.latitude = currentLocation.latitude;
            data.longitude = currentLocation.longitude;
        } else if (workType === 'wfo' && method === 'gps') {
            showToast('Lokasi GPS diperlukan untuk absen WFO', 'error');
            resetClockInButton();
            return;
        }
        
        const result = await api.post('/attendance/clock-in', data);
        
        if (result.success) {
            showToast(result.message, 'success');
            todayAttendance = result.data;
            updateAttendanceDisplay();
        } else {
            showToast(result.message || 'Gagal melakukan absen masuk', 'error');
            resetClockInButton();
        }
        
    } catch (error) {
        console.error('Clock in error:', error);
        showToast('Terjadi kesalahan saat absen', 'error');
        resetClockInButton();
    }
}

function resetClockInButton() {
    const btn = document.getElementById('btnClockIn');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Absen Masuk';
    }
}

// ============================================
// CLOCK OUT
// ============================================
async function clockOut(method = 'gps') {
    const btn = document.getElementById('btnClockOut');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    }
    
    try {
        const data = {
            method: method,
            notes: ''
        };
        
        // Add location if available
        if (currentLocation) {
            data.latitude = currentLocation.latitude;
            data.longitude = currentLocation.longitude;
        }
        
        const result = await api.post('/attendance/clock-out', data);
        
        if (result.success) {
            showToast(result.message, 'success');
            todayAttendance = result.data;
            updateAttendanceDisplay();
        } else {
            showToast(result.message || 'Gagal melakukan absen pulang', 'error');
            resetClockOutButton();
        }
        
    } catch (error) {
        console.error('Clock out error:', error);
        showToast('Terjadi kesalahan saat absen', 'error');
        resetClockOutButton();
    }
}

function resetClockOutButton() {
    const btn = document.getElementById('btnClockOut');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Absen Pulang';
    }
}

// ============================================
// QR CODE
// ============================================
async function showMyQR() {
    const qrDisplay = document.getElementById('qrDisplay');
    const qrImage = document.getElementById('qrImage');
    const qrDate = document.getElementById('qrDate');
    
    if (!qrDisplay || !qrImage) return;
    
    try {
        const result = await api.get('/attendance/qr-code');
        
        if (result.success) {
            qrImage.src = result.data.qr_image;
            if (qrDate) qrDate.textContent = formatDate(result.data.valid_date, 'long');
            qrDisplay.style.display = 'block';
        } else {
            showToast('Gagal membuat QR Code', 'error');
        }
        
    } catch (error) {
        console.error('QR generation error:', error);
        showToast('Terjadi kesalahan', 'error');
    }
}

async function scanQR() {
    showToast('Fitur scan QR akan segera hadir', 'info');
    // QR scanning implementation would require a library like jsQR
    // For now, show a placeholder
}

function stopScanner() {
    const scanner = document.getElementById('qrScanner');
    if (scanner) scanner.style.display = 'none';
}

// ============================================
// CAMERA / FACE RECOGNITION
// ============================================
async function startCamera() {
    const video = document.getElementById('cameraFeed');
    const btnStart = document.getElementById('btnStartCamera');
    const btnCapture = document.getElementById('btnCapture');
    const btnStop = document.getElementById('btnStopCamera');
    
    if (!video) return;
    
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: 640, height: 480 }
        });
        
        video.srcObject = cameraStream;
        
        if (btnStart) btnStart.style.display = 'none';
        if (btnCapture) btnCapture.style.display = '';
        if (btnStop) btnStop.style.display = '';
        
    } catch (error) {
        console.error('Camera error:', error);
        showToast('Gagal mengakses kamera. Pastikan izin kamera diaktifkan.', 'error');
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    const video = document.getElementById('cameraFeed');
    const btnStart = document.getElementById('btnStartCamera');
    const btnCapture = document.getElementById('btnCapture');
    const btnStop = document.getElementById('btnStopCamera');
    
    if (video) video.srcObject = null;
    if (btnStart) btnStart.style.display = '';
    if (btnCapture) btnCapture.style.display = 'none';
    if (btnStop) btnStop.style.display = 'none';
}

async function captureAndAttend() {
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('cameraCanvas');
    
    if (!video || !canvas) return;
    
    // Capture image
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    
    // Determine if clock in or clock out
    if (todayAttendance && todayAttendance.clock_in && !todayAttendance.clock_out) {
        await clockOutWithPhoto(imageData);
    } else if (!todayAttendance || !todayAttendance.clock_in) {
        await clockInWithPhoto(imageData);
    } else {
        showToast('Absensi hari ini sudah lengkap', 'info');
    }
}

async function clockInWithPhoto(photoData) {
    const btnCapture = document.getElementById('btnCapture');
    if (btnCapture) {
        btnCapture.disabled = true;
        btnCapture.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    }
    
    try {
        const workType = document.querySelector('input[name="workType"]:checked')?.value || 'wfo';
        
        const data = {
            method: 'face',
            work_type: workType,
            photo: photoData
        };
        
        if (currentLocation) {
            data.latitude = currentLocation.latitude;
            data.longitude = currentLocation.longitude;
        }
        
        const result = await api.post('/attendance/clock-in', data);
        
        if (result.success) {
            showToast(result.message, 'success');
            todayAttendance = result.data;
            updateAttendanceDisplay();
            stopCamera();
        } else {
            showToast(result.message || 'Gagal melakukan absen', 'error');
        }
        
    } catch (error) {
        console.error('Clock in with photo error:', error);
        showToast('Terjadi kesalahan', 'error');
    } finally {
        if (btnCapture) {
            btnCapture.disabled = false;
            btnCapture.innerHTML = '<i class="fas fa-camera"></i> Ambil Foto & Absen';
        }
    }
}

async function clockOutWithPhoto(photoData) {
    const btnCapture = document.getElementById('btnCapture');
    if (btnCapture) {
        btnCapture.disabled = true;
        btnCapture.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    }
    
    try {
        const data = {
            method: 'face',
            photo: photoData
        };
        
        if (currentLocation) {
            data.latitude = currentLocation.latitude;
            data.longitude = currentLocation.longitude;
        }
        
        const result = await api.post('/attendance/clock-out', data);
        
        if (result.success) {
            showToast(result.message, 'success');
            todayAttendance = result.data;
            updateAttendanceDisplay();
            stopCamera();
        } else {
            showToast(result.message || 'Gagal melakukan absen', 'error');
        }
        
    } catch (error) {
        console.error('Clock out with photo error:', error);
        showToast('Terjadi kesalahan', 'error');
    } finally {
        if (btnCapture) {
            btnCapture.disabled = false;
            btnCapture.innerHTML = '<i class="fas fa-camera"></i> Ambil Foto & Absen';
        }
    }
}

// ============================================
// WEEK HISTORY
// ============================================
async function loadWeekHistory() {
    const container = document.getElementById('weekHistory');
    if (!container) return;
    
    try {
        // Get last 7 days
        const today = new Date();
        const startDate = new Date(today);
        startDate.setDate(startDate.getDate() - 6);
        
        const result = await api.get(`/attendance/history?start_date=${startDate.toISOString().split('T')[0]}&end_date=${today.toISOString().split('T')[0]}&per_page=7`);
        
        // Create attendance map
        const attendanceMap = {};
        if (result.success && result.data) {
            result.data.forEach(att => {
                attendanceMap[att.date] = att;
            });
        }
        
        // Generate week display
        let html = '';
        const dayNames = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];
        
        for (let i = 6; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split('T')[0];
            const dayName = dayNames[date.getDay()];
            const dayNum = date.getDate();
            const isWeekend = date.getDay() === 0 || date.getDay() === 6;
            
            const attendance = attendanceMap[dateStr];
            let status = isWeekend ? 'weekend' : 'absent';
            let icon = isWeekend ? '-' : '✕';
            
            if (attendance) {
                status = attendance.status || 'present';
                if (attendance.clock_in) {
                    icon = status === 'late' ? '⏰' : '✓';
                }
                if (attendance.work_type === 'wfh') {
                    icon = '🏠';
                    status = 'wfh';
                }
            }
            
            html += `
                <div class="day-card">
                    <div class="day-name">${dayName}</div>
                    <div class="day-date">${dayNum}</div>
                    <div class="day-status ${status}">${icon}</div>
                </div>
            `;
        }
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading week history:', error);
    }
}

// ============================================
// EXPORT
// ============================================
window.initAttendancePage = initAttendancePage;
window.clockIn = clockIn;
window.clockOut = clockOut;
window.showMyQR = showMyQR;
window.scanQR = scanQR;
window.stopScanner = stopScanner;
window.startCamera = startCamera;
window.stopCamera = stopCamera;
window.captureAndAttend = captureAndAttend;
window.initLocation = initLocation;
