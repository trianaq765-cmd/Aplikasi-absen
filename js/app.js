/**
 * Main Application - Dashboard
 * Sistem Absensi Karyawan 2025
 */

// ============================================
// INITIALIZE DASHBOARD
// ============================================
async function initDashboard() {
    // Set current date
    const dateElement = document.getElementById('currentDate');
    if (dateElement) {
        dateElement.textContent = getCurrentDateFormatted();
    }
    
    // Start live clock
    startLiveClock();
    
    // Set greeting
    const greetingElement = document.getElementById('greeting');
    if (greetingElement) {
        greetingElement.textContent = getGreeting();
    }
    
    // Load dashboard data
    await loadDashboardData();
    
    // Load recent activity
    await loadRecentActivity();
}

// ============================================
// LOAD DASHBOARD DATA
// ============================================
async function loadDashboardData() {
    try {
        const result = await api.get('/reports/dashboard');
        
        if (result.success) {
            const data = result.data;
            
            // Update today's attendance status
            updateTodayStatus(data.today);
            
            // Update monthly stats
            updateMonthlyStats(data.monthly);
            
            // Update leave balance
            updateLeaveBalance(data.leave_balance);
            
            // Update admin stats if available
            if (data.admin_stats) {
                updateAdminStats(data.admin_stats);
            }
        } else {
            console.error('Failed to load dashboard:', result.message);
        }
        
    } catch (error) {
        console.error('Dashboard error:', error);
    }
}

// ============================================
// UPDATE TODAY STATUS
// ============================================
function updateTodayStatus(today) {
    const statusContainer = document.getElementById('attendanceStatus');
    const actionsContainer = document.getElementById('attendanceActions');
    
    if (!statusContainer || !actionsContainer) return;
    
    if (today.clock_in) {
        // Already clocked in
        let statusHtml = `
            <div class="attendance-info">
                <div class="attendance-time clock-in">
                    <div class="label">Masuk</div>
                    <div class="time">${today.clock_in}</div>
                </div>
        `;
        
        if (today.clock_out) {
            // Already clocked out
            statusHtml += `
                <div class="attendance-time clock-out">
                    <div class="label">Pulang</div>
                    <div class="time">${today.clock_out}</div>
                </div>
            `;
            
            actionsContainer.innerHTML = `
                <div class="attendance-complete">
                    <i class="fas fa-check-circle" style="color: var(--success); font-size: 2rem;"></i>
                    <p>Absensi hari ini sudah lengkap</p>
                </div>
            `;
        } else {
            statusHtml += `
                <div class="attendance-time clock-out">
                    <div class="label">Pulang</div>
                    <div class="time">--:--</div>
                </div>
            `;
            
            actionsContainer.innerHTML = `
                <a href="attendance.html" class="btn btn-danger btn-lg">
                    <i class="fas fa-sign-out-alt"></i>
                    Absen Pulang
                </a>
            `;
        }
        
        statusHtml += '</div>';
        statusContainer.innerHTML = statusHtml;
        
    } else {
        // Not clocked in yet
        statusContainer.innerHTML = `
            <div class="not-clocked-in">
                <i class="fas fa-clock" style="font-size: 2.5rem; color: var(--gray-300); margin-bottom: 10px;"></i>
                <p>Anda belum absen masuk hari ini</p>
            </div>
        `;
        
        actionsContainer.innerHTML = `
            <a href="attendance.html" class="btn btn-success btn-lg">
                <i class="fas fa-sign-in-alt"></i>
                Absen Masuk Sekarang
            </a>
        `;
    }
}

// ============================================
// UPDATE MONTHLY STATS
// ============================================
function updateMonthlyStats(monthly) {
    const elements = {
        statPresent: monthly.present || 0,
        statLate: monthly.late || 0,
        statWfh: monthly.wfh || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    });
}

// ============================================
// UPDATE LEAVE BALANCE
// ============================================
function updateLeaveBalance(balance) {
    const el = document.getElementById('statLeave');
    if (el) {
        el.textContent = balance.remaining || 12;
    }
}

// ============================================
// UPDATE ADMIN STATS
// ============================================
function updateAdminStats(stats) {
    const elements = {
        adminTotalEmployees: stats.total_employees || 0,
        adminTodayPresent: stats.today_present || 0,
        adminTodayAbsent: stats.today_absent || 0,
        adminPendingApprovals: stats.pending_approvals || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    });
    
    // Update pending badge in sidebar
    const badge = document.getElementById('pendingBadge');
    if (badge) {
        badge.textContent = stats.pending_approvals || 0;
        badge.style.display = stats.pending_approvals > 0 ? '' : 'none';
    }
}

// ============================================
// LOAD RECENT ACTIVITY
// ============================================
async function loadRecentActivity() {
    const container = document.getElementById('recentActivity');
    if (!container) return;
    
    try {
        const result = await api.get('/attendance/history?per_page=5');
        
        if (result.success && result.data.length > 0) {
            let html = '';
            
            result.data.forEach(item => {
                const icon = item.clock_out ? 'clock-out' : 'clock-in';
                const action = item.clock_out ? 'Absen Pulang' : 'Absen Masuk';
                const time = item.clock_out 
                    ? formatTime(item.clock_out) 
                    : formatTime(item.clock_in);
                
                html += `
                    <div class="activity-item">
                        <div class="activity-icon ${icon}">
                            <i class="fas fa-${item.clock_out ? 'sign-out-alt' : 'sign-in-alt'}"></i>
                        </div>
                        <div class="activity-content">
                            <h5>${action}</h5>
                            <p>${formatDate(item.date, 'short')} - ${getStatusBadge(item.status)}</p>
                        </div>
                        <span class="activity-time">${time}</span>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-history"></i>
                    <p>Belum ada aktivitas</p>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Error loading activity:', error);
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-circle"></i>
                <p>Gagal memuat aktivitas</p>
            </div>
        `;
    }
}

// ============================================
// EXPORT
// ============================================
window.initDashboard = initDashboard;
window.loadDashboardData = loadDashboardData;
window.loadRecentActivity = loadRecentActivity;
