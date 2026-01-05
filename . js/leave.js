/**
 * Leave Management Module
 * Cuti & Izin sesuai UU Ketenagakerjaan Indonesia
 * Sistem Absensi Karyawan 2025
 */

// ============================================
// STATE
// ============================================
let leaveTypes = {};
let currentFilter = 'all';

// ============================================
// INITIALIZE LEAVE PAGE
// ============================================
async function initLeavePage() {
    // Load leave types
    await loadLeaveTypes();
    
    // Load leave balance
    await loadLeaveBalance();
    
    // Load my leave requests
    await loadMyLeaveRequests();
    
    // Setup form
    setupLeaveForm();
    
    // Setup filter tabs
    setupFilterTabs();
}

// ============================================
// LOAD LEAVE TYPES
// ============================================
async function loadLeaveTypes() {
    try {
        const result = await api.get('/leave/types');
        
        if (result.success) {
            leaveTypes = result.data;
            renderLeaveTypes();
        }
        
    } catch (error) {
        console.error('Error loading leave types:', error);
    }
}

function renderLeaveTypes() {
    const container = document.getElementById('leaveTypesGrid');
    if (!container) return;
    
    const types = [
        { key: 'annual', icon: 'calendar-check', color: 'primary' },
        { key: 'sick', icon: 'medkit', color: 'danger' },
        { key: 'marriage', icon: 'heart', color: 'pink' },
        { key: 'maternity', icon: 'baby', color: 'info' },
        { key: 'paternity', icon: 'male', color: 'info' },
        { key: 'bereavement_spouse', icon: 'praying-hands', color: 'gray' },
        { key: 'hajj', icon: 'kaaba', color: 'success' },
        { key: 'unpaid', icon: 'calendar-minus', color: 'warning' }
    ];
    
    let html = '';
    
    types.forEach(type => {
        const info = leaveTypes[type.key];
        if (info) {
            html += `
                <div class="leave-type-card" style="border-left-color: var(--${type.color});">
                    <h5><i class="fas fa-${type.icon}"></i> ${info.name}</h5>
                    <p>Maksimal ${info.max_days} hari</p>
                </div>
            `;
        }
    });
    
    container.innerHTML = html;
}

// ============================================
// LOAD LEAVE BALANCE
// ============================================
async function loadLeaveBalance() {
    try {
        const result = await api.get('/leave/balance');
        
        if (result.success) {
            updateBalanceDisplay(result.data);
        }
        
    } catch (error) {
        console.error('Error loading balance:', error);
    }
}

function updateBalanceDisplay(balance) {
    const remaining = balance.annual_remaining || 0;
    const quota = balance.annual_quota || 12;
    const used = balance.annual_used || 0;
    const percentage = (remaining / quota) * 100;
    
    // Update numbers
    const remainingEl = document.getElementById('balanceRemaining');
    const quotaEl = document.getElementById('balanceQuota');
    const usedEl = document.getElementById('balanceUsed');
    const progressEl = document.getElementById('balanceProgress');
    
    if (remainingEl) remainingEl.textContent = remaining;
    if (quotaEl) quotaEl.textContent = `${quota} hari`;
    if (usedEl) usedEl.textContent = `${used} hari`;
    
    // Update progress circle
    if (progressEl) {
        progressEl.setAttribute('stroke-dasharray', `${percentage}, 100`);
    }
}

// ============================================
// LOAD MY LEAVE REQUESTS
// ============================================
async function loadMyLeaveRequests(status = 'all') {
    const container = document.getElementById('leaveList');
    if (!container) return;
    
    container.innerHTML = `
        <div class="loading-placeholder">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Memuat data...</p>
        </div>
    `;
    
    try {
        let url = '/leave/my-requests?per_page=20';
        if (status !== 'all') {
            url += `&status=${status}`;
        }
        
        const result = await api.get(url);
        
        if (result.success && result.data.length > 0) {
            renderLeaveList(result.data);
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-calendar-times"></i>
                    <h4>Tidak ada pengajuan</h4>
                    <p>Belum ada pengajuan cuti${status !== 'all' ? ` dengan status "${status}"` : ''}</p>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Error loading leave requests:', error);
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-exclamation-circle"></i>
                <p>Gagal memuat data</p>
            </div>
        `;
    }
}

function renderLeaveList(requests) {
    const container = document.getElementById('leaveList');
    if (!container) return;
    
    let html = '';
    
    requests.forEach(req => {
        const typeName = getLeaveTypeName(req.leave_type);
        const startDate = formatDate(req.start_date, 'short');
        const endDate = formatDate(req.end_date, 'short');
        const statusBadge = getStatusBadge(req.status);
        
        html += `
            <div class="leave-item">
                <div class="leave-info">
                    <h5>${typeName}</h5>
                    <p>${req.reason}</p>
                </div>
                <div class="leave-dates">
                    <div class="dates">${startDate} - ${endDate}</div>
                    <div class="duration">${req.total_days} hari</div>
                </div>
                <div class="leave-actions">
                    ${statusBadge}
                    ${req.status === 'pending' ? `
                        <button class="btn btn-sm btn-outline" onclick="cancelLeave(${req.id})" title="Batalkan">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// ============================================
// FILTER TABS
// ============================================
function setupFilterTabs() {
    const tabs = document.querySelectorAll('.filter-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            const status = tab.dataset.status;
            currentFilter = status;
            loadMyLeaveRequests(status);
        });
    });
}

// ============================================
// LEAVE FORM
// ============================================
function setupLeaveForm() {
    const form = document.getElementById('leaveForm');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    
    // Set min date to today
    const today = getToday();
    if (startDate) startDate.min = today;
    if (endDate) endDate.min = today;
    
    // Calculate days when dates change
    if (startDate) {
        startDate.addEventListener('change', () => {
            if (endDate) endDate.min = startDate.value;
            calculateDays();
        });
    }
    
    if (endDate) {
        endDate.addEventListener('change', calculateDays);
    }
    
    // Handle form submit
    if (form) {
        form.addEventListener('submit', handleLeaveSubmit);
    }
}

function calculateDays() {
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;
    const totalDaysEl = document.getElementById('totalDays');
    
    if (startDate && endDate && totalDaysEl) {
        const days = calculateWorkingDays(startDate, endDate);
        totalDaysEl.textContent = days;
    }
}

async function handleLeaveSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Validate
    const leaveType = document.getElementById('leaveType').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const reason = document.getElementById('reason').value;
    
    if (!leaveType || !startDate || !endDate || !reason) {
        showToast('Mohon lengkapi semua field yang wajib diisi', 'error');
        return;
    }
    
    // Disable button
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    
    try {
        const data = {
            leave_type: leaveType,
            start_date: startDate,
            end_date: endDate,
            reason: reason
        };
        
        const result = await api.post('/leave/request', data);
        
        if (result.success) {
            showToast('Pengajuan cuti berhasil dibuat', 'success');
            closeLeaveModal();
            form.reset();
            
            // Reload data
            await loadLeaveBalance();
            await loadMyLeaveRequests(currentFilter);
        } else {
            showToast(result.message || 'Gagal membuat pengajuan', 'error');
        }
        
    } catch (error) {
        console.error('Leave submit error:', error);
        showToast('Terjadi kesalahan', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Ajukan';
    }
}

// ============================================
// CANCEL LEAVE
// ============================================
async function cancelLeave(leaveId) {
    if (!confirm('Apakah Anda yakin ingin membatalkan pengajuan ini?')) {
        return;
    }
    
    try {
        const result = await api.post(`/leave/cancel/${leaveId}`);
        
        if (result.success) {
            showToast('Pengajuan berhasil dibatalkan', 'success');
            await loadMyLeaveRequests(currentFilter);
        } else {
            showToast(result.message || 'Gagal membatalkan pengajuan', 'error');
        }
        
    } catch (error) {
        console.error('Cancel leave error:', error);
        showToast('Terjadi kesalahan', 'error');
    }
}

// ============================================
// MODAL
// ============================================
function openLeaveModal() {
    const modal = document.getElementById('leaveModal');
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

function closeLeaveModal() {
    const modal = document.getElementById('leaveModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// Close modal on background click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        closeLeaveModal();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeLeaveModal();
    }
});

// ============================================
// APPROVAL FUNCTIONS (Admin/Manager)
// ============================================
async function loadPendingApprovals() {
    const container = document.getElementById('pendingApprovals');
    if (!container) return;
    
    try {
        const result = await api.get('/leave/pending');
        
        if (result.success && result.data.length > 0) {
            let html = '';
            
            result.data.forEach(req => {
                html += `
                    <div class="leave-item">
                        <div class="leave-info">
                            <h5>${req.employee_name}</h5>
                            <p><strong>${getLeaveTypeName(req.leave_type)}</strong>: ${req.reason}</p>
                        </div>
                        <div class="leave-dates">
                            <div class="dates">${formatDate(req.start_date, 'short')} - ${formatDate(req.end_date, 'short')}</div>
                            <div class="duration">${req.total_days} hari</div>
                        </div>
                        <div class="leave-actions">
                            <button class="btn btn-sm btn-success" onclick="approveLeave(${req.id})">
                                <i class="fas fa-check"></i> Setujui
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="rejectLeave(${req.id})">
                                <i class="fas fa-times"></i> Tolak
                            </button>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-check-circle"></i>
                    <h4>Tidak ada pengajuan</h4>
                    <p>Semua pengajuan sudah diproses</p>
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Error loading pending:', error);
    }
}

async function approveLeave(leaveId) {
    if (!confirm('Setujui pengajuan cuti ini?')) return;
    
    try {
        const result = await api.post(`/leave/approve/${leaveId}`);
        
        if (result.success) {
            showToast('Pengajuan disetujui', 'success');
            loadPendingApprovals();
        } else {
            showToast(result.message || 'Gagal menyetujui', 'error');
        }
        
    } catch (error) {
        console.error('Approve error:', error);
        showToast('Terjadi kesalahan', 'error');
    }
}

async function rejectLeave(leaveId) {
    const reason = prompt('Alasan penolakan:');
    if (!reason) return;
    
    try {
        const result = await api.post(`/leave/reject/${leaveId}`, { reason });
        
        if (result.success) {
            showToast('Pengajuan ditolak', 'success');
            loadPendingApprovals();
        } else {
            showToast(result.message || 'Gagal menolak', 'error');
        }
        
    } catch (error) {
        console.error('Reject error:', error);
        showToast('Terjadi kesalahan', 'error');
    }
}

// ============================================
// EXPORT
// ============================================
window.initLeavePage = initLeavePage;
window.openLeaveModal = openLeaveModal;
window.closeLeaveModal = closeLeaveModal;
window.cancelLeave = cancelLeave;
window.loadPendingApprovals = loadPendingApprovals;
window.approveLeave = approveLeave;
window.rejectLeave = rejectLeave;
