async function initDashboard() {
    document.getElementById('currentDate').textContent = getCurrentDateFormatted();
    document.getElementById('greeting').textContent = getGreeting();
    startLiveClock();
    await loadDashboardData();
}

async function loadDashboardData() {
    const result = await api.get('/reports/dashboard');
    
    if (result.success) {
        const data = result.data;
        
        // Today's attendance
        const status = document.getElementById('attendanceStatus');
        const actions = document.getElementById('attendanceActions');
        
        if (data.today.clock_in) {
            status.innerHTML = `
                <div class="attendance-info">
                    <div>Masuk: <strong>${data.today.clock_in}</strong></div>
                    ${data.today.clock_out ? `<div>Pulang: <strong>${data.today.clock_out}</strong></div>` : ''}
                </div>
            `;
            
            if (data.today.clock_out) {
                actions.innerHTML = '<p style="color: var(--success);">✓ Absensi lengkap</p>';
            } else {
                actions.innerHTML = '<a href="attendance.html" class="btn btn-danger">Absen Pulang</a>';
            }
        } else {
            status.innerHTML = '<p>Belum absen hari ini</p>';
            actions.innerHTML = '<a href="attendance.html" class="btn btn-success">Absen Masuk</a>';
        }
        
        // Stats
        document.getElementById('statPresent').textContent = data.monthly.present || 0;
        document.getElementById('statLate').textContent = data.monthly.late || 0;
        document.getElementById('statWfh').textContent = data.monthly.wfh || 0;
        document.getElementById('statLeave').textContent = data.leave_balance.remaining || 12;
    }
}

window.initDashboard = initDashboard;
