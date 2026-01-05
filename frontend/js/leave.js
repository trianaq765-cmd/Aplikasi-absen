async function initLeavePage() {
    await loadLeaveBalance();
    await loadLeaveRequests();
    setupLeaveForm();
}

async function loadLeaveBalance() {
    const result = await api.get('/leave/balance');
    if (result.success) {
        document.getElementById('balanceQuota').textContent = result.data.annual_quota + ' hari';
        document.getElementById('balanceUsed').textContent = result.data.annual_used + ' hari';
        document.getElementById('balanceRemaining').textContent = result.data.annual_remaining + ' hari';
    }
}

async function loadLeaveRequests() {
    const container = document.getElementById('leaveList');
    const result = await api.get('/leave/my-requests');
    
    if (result.success && result.data.length > 0) {
        container.innerHTML = result.data.map(req => `
            <div class="leave-item">
                <div class="leave-info">
                    <strong>${req.leave_type}</strong>
                    <p>${req.reason}</p>
                </div>
                <div class="leave-dates">
                    <span>${formatDate(req.start_date)} - ${formatDate(req.end_date)}</span>
                    <span>${req.total_days} hari</span>
                </div>
                <span class="leave-status ${req.status}">${req.status}</span>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<p class="empty">Belum ada pengajuan cuti</p>';
    }
}

function setupLeaveForm() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('startDate').min = today;
    document.getElementById('endDate').min = today;
    
    document.getElementById('leaveForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const data = {
            leave_type: document.getElementById('leaveType').value,
            start_date: document.getElementById('startDate').value,
            end_date: document.getElementById('endDate').value,
            reason: document.getElementById('reason').value
        };
        
        const result = await api.post('/leave/request', data);
        
        if (result.success) {
            showToast('Pengajuan berhasil', 'success');
            closeLeaveModal();
            loadLeaveRequests();
        } else {
            showToast(result.message, 'error');
        }
    });
}

function openLeaveModal() {
    document.getElementById('leaveModal').classList.add('show');
}

function closeLeaveModal() {
    document.getElementById('leaveModal').classList.remove('show');
    document.getElementById('leaveForm').reset();
}

window.initLeavePage = initLeavePage;
window.openLeaveModal = openLeaveModal;
window.closeLeaveModal = closeLeaveModal;
