/**
 * Attendance Module - FIXED VERSION
 */

let currentLocation = null;
let todayAttendance = null;

// ============================================
// INITIALIZE
// ============================================
async function initAttendancePage() {
    console.log('[Attendance] Initializing...');
    
    // Set date
    const dateElement = document.getElementById('currentDate');
    const dateDisplay = document.getElementById('dateDisplay');
    const today = getCurrentDateFormatted();
    
    if (dateElement) dateElement.textContent = today;
    if (dateDisplay) dateDisplay.textContent = today;
    
    // Start clock
    startLiveClock();
    
    // Load today's attendance
    await loadTodayAttendance();
    
    // Get location
    initLocation();
}

// ============================================
// LOAD TODAY ATTENDANCE
// ============================================
async function loadTodayAttendance() {
    console.log('[Attendance] Loading today attendance...');
    
    try {
        const result = await api.get('/attendance/today');
        
        console.log('[Attendance] Today result:', result);
        
        if (result.success) {
            todayAttendance = result.data;
            updateAttendanceDisplay();
        } else {
            console.error('[Attendance] Error:', result.message);
            showToast(result.message || 'Gagal memuat data', 'error');
        }
        
    } catch (error) {
        console.error('[Attendance] Error:', error);
        showToast('Terjadi kesalahan', 'error');
    }
}

// ============================================
// UPDATE DISPLAY
// ============================================
function updateAttendanceDisplay() {
    console.log('[Attendance] Updating display, data:', todayAttendance);
    
    const clockInTime = document.getElementById('clockInTime');
    const clockOutTime = document.getElementById('clockOutTime');
    const btnClockIn = document.getElementById('btnClockIn');
    const btnClockOut = document.getElementById('btnClockOut');
    const noteElement = document.getElementById('attendanceNote');
    
    // Reset
    if (clockInTime) clockInTime.textContent = '--:--';
    if (clockOutTime) clockOutTime.textContent = '--:--';
    if (btnClockIn) btnClockIn.style.display = '';
    if (btnClockOut) btnClockOut.style.display = 'none';
    if (noteElement) noteElement.innerHTML = '';
    
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
    }
}

// ============================================
// LOCATION
// ============================================
async function initLocation() {
    console.log('[Attendance] Getting location...');
    
    const locationInfo = document.getElementById('locationInfo');
    if (!locationInfo) return;
    
    locationInfo.innerHTML = `
        <div class="location-loading" style="text-align: center;">
            <i class="fas fa-spinner fa-spin" style="font-size: 1.5rem; margin-bottom: 10px;"></i>
            <p>Mendapatkan lokasi GPS...</p>
        </div>
    `;
    
    try {
        currentLocation = await getCurrentLocation();
        
        console.log('[Attendance] Location:', currentLocation);
        
        locationInfo.innerHTML = `
            <div class="location-result" style="display: flex; align-items: flex-start; gap: 15px;">
                <i class="fas fa-map-marker-alt" style="font-size: 1.5rem; color: var(--success);"></i>
                <div>
                    <strong style="display: block; margin-bottom: 5px;">Lokasi Terdeteksi</strong>
                    <p style="font-size: 0.9rem; color: var(--gray-600);">
                        Lat: ${currentLocation.latitude.toFixed(6)}, Long: ${currentLocation.longitude.toFixed(6)}
                    </p>
                    <small style="color: var(--gray-500);">Akurasi: ${currentLocation.accuracy.toFixed(0)} meter</small>
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('[Attendance] Location error:', error);
        
        locationInfo.innerHTML = `
            <div class="location-error" style="text-align: center; color: var(--danger);">
                <i class="fas fa-exclamation-triangle" style="font-size: 1.5rem; margin-bottom: 10px;"></i>
                <p>${error.message}</p>
                <button class="btn btn-sm btn-outline" onclick="initLocation()" style="margin-top: 10px;">
                    <i class="fas fa-redo"></i> Coba Lagi
                </button>
            </div>
        `;
    }
}

// ============================================
// CLOCK IN
// ============================================
async function clockIn(method) {
    console.log('[Attendance] Clock in with method:', method);
    
    const btn = document.getElementById('btnClockIn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    }
    
    try {
        const workType = document.querySelector('input[name="workType"]:checked')?.value || 'wfo';
        
        const data = {
            method: method,
            work_type: workType
        };
        
        // Add location if available
        if (currentLocation) {
            data.latitude = currentLocation.latitude;
            data.longitude = currentLocation.longitude;
        }
        
        console.log('[Attendance] Clock in data:', data);
        
        const result = await api.post('/attendance/clock-in', data);
        
        console.log('[Attendance] Clock in result:', result);
        
        if (result.success) {
            showToast(result.message || 'Absen masuk berhasil', 'success');
            todayAttendance = result.data;
            updateAttendanceDisplay();
        } else {
            showToast(result.message || 'Gagal absen masuk', 'error');
            resetClockInButton();
        }
        
    } catch (error) {
        console.error('[Attendance] Clock in error:', error);
        showToast('Terjadi kesalahan', 'error');
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
async function clockOut(method) {
    console.log('[Attendance] Clock out with method:', method);
    
    const btn = document.getElementById('btnClockOut');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    }
    
    try {
        const data = { method: method };
        
        if (currentLocation) {
            data.latitude = currentLocation.latitude;
            data.longitude = currentLocation.longitude;
        }
        
        console.log('[Attendance] Clock out data:', data);
        
        const result = await api.post('/attendance/clock-out', data);
        
        console.log('[Attendance] Clock out result:', result);
        
        if (result.success) {
            showToast(result.message || 'Absen pulang berhasil', 'success');
            todayAttendance = result.data;
            updateAttendanceDisplay();
        } else {
            showToast(result.message || 'Gagal absen pulang', 'error');
            resetClockOutButton();
        }
        
    } catch (error) {
        console.error('[Attendance] Clock out error:', error);
        showToast('Terjadi kesalahan', 'error');
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
// EXPORT GLOBAL
// ============================================
window.initAttendancePage = initAttendancePage;
window.loadTodayAttendance = loadTodayAttendance;
window.initLocation = initLocation;
window.clockIn = clockIn;
window.clockOut = clockOut;

console.log('[Attendance] Loaded successfully');
