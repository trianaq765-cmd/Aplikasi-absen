/**
 * Leave Management - FIXED VERSION
 */

// ============================================
// INITIALIZE
// ============================================
async function initLeavePage() {
    console.log('[Leave] Initializing...');
    
    await loadLeaveBalance();
    await loadLeaveRequests();
    setupLeaveForm();
}

// ============================================
// LOAD BALANCE
// ============================================
async function loadLeaveBalance() {
    console.log('[Leave] Loading balance...');
    
    try {
        const result = await api.get('/leave/balance');
        
        console.log('[Leave] Balance result:', result);
        
        if (result.success && result.data) {
            const data = result.data;
            
            const quotaEl = document.getElementById('balanceQuota');
            const usedEl = document.getElementById('balanceUsed');
            const remainingEl = document.getElementById('balanceRemaining');
            
            if (quotaEl) quotaEl.textContent = (data.annual_quota || 12) + ' hari';
            if (usedEl) usedEl.textContent = (data.annual_used || 0) + ' hari';
            if (remainingEl) remainingEl.textContent = (data.annual_remaining || 12) + ' hari';
        }
        
    } catch (error) {
        console.error('[Leave] Balance error:', error);
    }
}

// ============================================
// LOAD REQUESTS
// ============================================
async function loadLeaveRequests() {
    console.log('[Leave] Loading requests...');
    
    const container = document.getElementById('leaveList');
    if (!container) return;
    
    container.innerHTML = '<p style="text-align: center; color: var(--gray-400);"><i class="fas fa-spinner fa-spin"></i> Memuat...</p>';
    
    try {
        const result = await api.get('/leave/my-requests');
        
        console.log('[Leave] Requests result:', result);
        
        if (result.success && result.data && result.data.length > 0) {
            container.innerHTML = result.data.map(req => {
                const statusClass = {
                    pending: 'warning',
                    approved: 'success',
                    rejected: 'danger',
                    cancelled: 'secondary'
                }[req.status] || 'secondary';
                
                const statusLabel = {
                    pending: 'Menunggu',
                    approved: 'Disetujui',
                    rejected: 'Ditolak',
                    cancelled: 'Dibatalkan'
                }[req.status] || req.status;
                
                return `
                    <div class="leave-item" style="display: flex; justify-content: space-between; align-items: center; padding: 15px; border-bottom: 1px solid var(--gray-100);">
                        <div class="leave-info">
                            <strong style="display: block; margin-bottom: 5px;">${getLeaveTypeName(req.leave_type)}</strong>
                            <p style="font-size: 0.85rem; color: var(--gray-500);">${req.reason}</p>
                        </div>
                        <div class="leave-dates" style="text-align: right; margin: 0 15px;">
                            <span style="display: block; font-weight: 500;">${formatDate(req.start_date)} - ${formatDate(req.end_date)}</span>
                            <span style="font-size: 0.85rem; color: var(--gray-500);">${req.total_days} hari</span>
                        </div>
                        <span class="leave-status ${statusClass}" style="padding: 6px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; background: var(--${statusClass}-light); color: var(--${statusClass});">
                            ${statusLabel}
                        </span>
                    </div>
                `;
            }).join('');
        } else {
            container.innerHTML = '<p style="text-align: center; color: var(--gray-400); padding: 40px;">Belum ada pengajuan cuti</p>';
        }
        
    } catch (error) {
        console.error('[Leave] Requests error:', error);
        container.innerHTML = '<p style="text-align: center; color: var(--danger);">Gagal memuat data</p>';
    }
}

function getLeaveTypeName(type) {
    const types = {
        annual: 'Cuti Tahunan',
        sick: 'Sakit',
        marriage: 'Cuti Menikah',
        maternity: 'Cuti Melahirkan',
        paternity: 'Cuti Ayah',
        bereavement: 'Duka Cita',
        unpaid: 'Tanpa Gaji',
        other: 'Lainnya'
    };
    return types[type] || type;
}

// ============================================
// FORM SETUP
// ============================================
function setupLeaveForm() {
    const today = new Date().toISOString().split('T')[0];
    
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    
    if (startDate) startDate.min = today;
    if (endDate) endDate.min = today;
    
    if (startDate) {
        startDate.addEventListener('change', () => {
            if (endDate) endDate.min = startDate.value;
        });
    }
    
    const form = document.getElementById('leaveForm');
    if (form) {
        form.addEventListener('submit', handleLeaveSubmit);
    }
}

async function handleLeaveSubmit(e) {
    e.preventDefault();
    
    console.log('[Leave] Submitting request...');
    
    const btn = e.target.querySelector('button[type="submit"]');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
    }
    
    try {
        const data = {
            leave_type: document.getElementById('leaveType').value,
            start_date: document.getElementById('startDate').value,
            end_date: document.getElementById('endDate').value,
            reason: document.getElementById('reason').value
        };
        
        console.log('[Leave] Submit data:', data);
        
        const result = await api.post('/leave/request', data);
        
        console.log('[Leave] Submit result:', result);
        
        if (result.success) {
            showToast('Pengajuan cuti berhasil', 'success');
            closeLeaveModal();
            document.getElementById('leaveForm').reset();
            await loadLeaveRequests();
            await loadLeaveBalance();
        } else {
            showToast(result.message || 'Gagal mengajukan cuti', 'error');
        }
        
    } catch (error) {
        console.error('[Leave] Submit error:', error);
        showToast('Terjadi kesalahan', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-paper-plane"></i> Ajukan';
        }
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

// Close on background click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        closeLeaveModal();
    }
});

// ============================================
// EXPORT GLOBAL
// ============================================
window.initLeavePage = initLeavePage;
window.openLeaveModal = openLeaveModal;
window.closeLeaveModal = closeLeaveModal;

console.log('[Leave] Loaded successfully');
