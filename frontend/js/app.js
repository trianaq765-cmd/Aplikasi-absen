/**
 * Dashboard App - FIXED VERSION
 */

// ============================================
// INITIALIZE DASHBOARD
// ============================================
async function initDashboard() {
    console.log('[Dashboard] Initializing...');
    
    // Set current date
    const dateElement = document.getElementById('currentDate');
    if (dateElement) {
        dateElement.textContent = getCurrentDateFormatted();
    }
    
    // Set greeting
    const greetingElement = document.getElementById('greeting');
    if (greetingElement) {
        greetingElement.textContent = getGreeting();
    }
    
    // Start live clock
    startLiveClock();
    
    // Load dashboard data
    await loadDashboardData();
}

// ============================================
// LOAD DASHBOARD DATA
// ============================================
async function loadDashboardData() {
    console.log('[Dashboard] Loading data...');
    
    const statusContainer = document.getElementById('attendanceStatus');
    const actionsContainer = document.getElementById('attendanceActions');
    
    try {
        const result = await api.get('/reports/dashboard');
        
        console.log('[Dashboard] API result:', result);
        
        if (result.success && result.data) {
            const data = result.data;
            
            // Update today's attendance
            updateTodayAttendance(data.today, statusContainer, actionsContainer);
            
            // Update monthly stats
            updateMonthlyStats(data.monthly);
            
            // Update leave balance
            if (data.leave_balance) {
                const leaveEl = document.getElementById('statLeave');
                if (leaveEl) {
                    leaveEl.textContent = data.leave_balance.remaining || 12;
                }
            }
            
        } else {
            console.error('[Dashboard] API error:', result.message);
            
            if (statusContainer) {
                statusContainer.innerHTML = `<p style="color: var(--danger);">Gagal memuat data: ${result.message || 'Unknown error'}</p>`;
            }
            if (actionsContainer) {
                actionsContainer.innerHTML = '<a href="attendance.html" class="btn btn-primary">Buka Absensi</a>';
            }
        }
        
    } catch (error) {
        console.error('[Dashboard] Error:', error);
        
        if (statusContainer) {
            statusContainer.innerHTML = '<p style="color: var(--danger);">Terjadi kesalahan</p>';
        }
        if (actionsContainer) {
            actionsContainer.innerHTML = '<button class="btn btn-outline" onclick="loadDashboardData()">Coba Lagi</button>';
        }
    }
}

// ============================================
// UPDATE TODAY ATTENDANCE
// ============================================
function updateTodayAttendance(today, statusContainer, actionsContainer) {
    console.log('[Dashboard] Today data:', today);
    
    if (!statusContainer || !actionsContainer) return;
    
    if (!today) {
        statusContainer.innerHTML = '<p>Belum ada data hari ini</p>';
        actionsContainer.innerHTML = '<a href="attendance.html" class="btn btn-success btn-lg"><i class="fas fa-sign-in-alt"></i> Absen Masuk</a>';
        return;
    }
    
    if (today.clock_in) {
        // Already clocked in
        let html = `
            <div class="attendance-info">
                <div class="attendance-time">
                    <span class="label">Masuk</span>
                    <span class="time" style="color: var(--success); font-size: 1.5rem; font-weight: bold;">${today.clock_in}</span>
                </div>
        `;
        
        if (today.clock_out) {
            html += `
                <div class="attendance-time">
                    <span class="label">Pulang</span>
                    <span class="time" style="color: var(--info); font-size: 1.5rem; font-weight: bold;">${today.clock_out}</span>
                </div>
            `;
            
            statusContainer.innerHTML = html + '</div>';
            actionsContainer.innerHTML = '<p style="color: var(--success);"><i class="fas fa-check-circle"></i> Absensi hari ini sudah lengkap</p>';
            
        } else {
            html += `
                <div class="attendance-time">
                    <span class="label">Pulang</span>
                    <span class="time" style="color: var(--gray-400); font-size: 1.5rem;">--:--</span>
                </div>
            `;
            
            statusContainer.innerHTML = html + '</div>';
            actionsContainer.innerHTML = '<a href="attendance.html" class="btn btn-danger btn-lg"><i class="fas fa-sign-out-alt"></i> Absen Pulang</a>';
        }
        
    } else {
        // Not clocked in yet
        statusContainer.innerHTML = `
            <div style="text-align: center; padding: 20px;">
                <i class="fas fa-clock" style="font-size: 2rem; color: var(--gray-300); margin-bottom: 10px;"></i>
                <p>Anda belum absen masuk hari ini</p>
            </div>
        `;
        
        actionsContainer.innerHTML = '<a href="attendance.html" class="btn btn-success btn-lg"><i class="fas fa-sign-in-alt"></i> Absen Masuk Sekarang</a>';
    }
}

// ============================================
// UPDATE MONTHLY STATS
// ============================================
function updateMonthlyStats(monthly) {
    console.log('[Dashboard] Monthly data:', monthly);
    
    if (!monthly) return;
    
    const elements = {
        'statPresent': monthly.present || 0,
        'statLate': monthly.late || 0,
        'statWfh': monthly.wfh || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    });
}

// ============================================
// EXPORT GLOBAL
// ============================================
window.initDashboard = initDashboard;
window.loadDashboardData = loadDashboardData;

console.log('[App] Loaded successfully');
