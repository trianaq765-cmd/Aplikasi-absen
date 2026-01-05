let currentLocation = null;
let todayAttendance = null;

async function initAttendancePage() {
    document.getElementById('currentDate').textContent = getCurrentDateFormatted();
    document.getElementById('dateDisplay').textContent = getCurrentDateFormatted();
    startLiveClock();
    await loadTodayAttendance();
    initLocation();
}

async function loadTodayAttendance() {
    const result = await api.get('/attendance/today');
    if (result.success) {
        todayAttendance = result.data;
        updateAttendanceDisplay();
    }
}

function updateAttendanceDisplay() {
    const clockIn = document.getElementById('clockInTime');
    const clockOut = document.getElementById('clockOutTime');
    const btnIn = document.getElementById('btnClockIn');
    const btnOut = document.getElementById('btnClockOut');
    const note = document.getElementById('attendanceNote');
    
    if (todayAttendance && todayAttendance.clock_in) {
        clockIn.textContent = formatTime(todayAttendance.clock_in);
        btnIn.style.display = 'none';
        btnOut.style.display = '';
        
        if (todayAttendance.late_minutes > 0) {
            note.className = 'attendance-note late';
            note.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Terlambat ${todayAttendance.late_minutes} menit`;
        }
        
        if (todayAttendance.clock_out) {
            clockOut.textContent = formatTime(todayAttendance.clock_out);
            btnOut.style.display = 'none';
            note.className = 'attendance-note success';
            note.innerHTML = '<i class="fas fa-check-circle"></i> Absensi lengkap';
        }
    }
}

async function initLocation() {
    const info = document.getElementById('locationInfo');
    try {
        currentLocation = await getCurrentLocation();
        info.innerHTML = `
            <div class="location-result">
                <i class="fas fa-map-marker-alt" style="color: var(--success);"></i>
                <div>
                    <strong>Lokasi Terdeteksi</strong>
                    <p>Lat: ${currentLocation.latitude.toFixed(6)}, Long: ${currentLocation.longitude.toFixed(6)}</p>
                    <small>Akurasi: ${currentLocation.accuracy.toFixed(0)}m</small>
                </div>
            </div>
        `;
    } catch (error) {
        info.innerHTML = `
            <div class="location-error">
                <i class="fas fa-exclamation-triangle" style="color: var(--danger);"></i>
                <p>${error.message}</p>
                <button class="btn btn-sm btn-outline" onclick="initLocation()">Coba Lagi</button>
            </div>
        `;
    }
}

async function clockIn(method) {
    const btn = document.getElementById('btnClockIn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    
    const workType = document.querySelector('input[name="workType"]:checked')?.value || 'wfo';
    const data = { method, work_type: workType };
    
    if (currentLocation) {
        data.latitude = currentLocation.latitude;
        data.longitude = currentLocation.longitude;
    }
    
    const result = await api.post('/attendance/clock-in', data);
    
    if (result.success) {
        showToast(result.message, 'success');
        todayAttendance = result.data;
        updateAttendanceDisplay();
    } else {
        showToast(result.message, 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Absen Masuk';
    }
}

async function clockOut(method) {
    const btn = document.getElementById('btnClockOut');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    
    const data = { method };
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
        showToast(result.message, 'error');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Absen Pulang';
    }
}

window.initAttendancePage = initAttendancePage;
window.clockIn = clockIn;
window.clockOut = clockOut;
window.initLocation = initLocation;
