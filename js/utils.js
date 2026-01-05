/**
 * Utility Functions & API Helper
 * Sistem Absensi Karyawan 2025
 */

// ============================================
// CONFIGURATION
// ============================================
const CONFIG = {
    // API Base URL - sesuaikan dengan deployment
    API_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:5000/api' 
        : '/api',
    
    // Token keys
    TOKEN_KEY: 'absensi_access_token',
    REFRESH_TOKEN_KEY: 'absensi_refresh_token',
    USER_KEY: 'absensi_user',
    
    // Office settings (default, akan di-override dari server)
    OFFICE_START: '08:00',
    OFFICE_END: '17:00',
    LATE_TOLERANCE: 15,
    
    // Timezone
    TIMEZONE: 'Asia/Jakarta'
};

// ============================================
// TOKEN MANAGEMENT
// ============================================
function getToken() {
    return localStorage.getItem(CONFIG.TOKEN_KEY);
}

function setToken(token) {
    localStorage.setItem(CONFIG.TOKEN_KEY, token);
}

function getRefreshToken() {
    return localStorage.getItem(CONFIG.REFRESH_TOKEN_KEY);
}

function setRefreshToken(token) {
    localStorage.setItem(CONFIG.REFRESH_TOKEN_KEY, token);
}

function removeTokens() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.REFRESH_TOKEN_KEY);
    localStorage.removeItem(CONFIG.USER_KEY);
}

function getUser() {
    const user = localStorage.getItem(CONFIG.USER_KEY);
    return user ? JSON.parse(user) : null;
}

function setUser(user) {
    localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
}

// ============================================
// API HELPER
// ============================================
async function apiRequest(endpoint, options = {}) {
    const url = `${CONFIG.API_URL}${endpoint}`;
    
    const defaultHeaders = {
        'Content-Type': 'application/json'
    };
    
    // Add auth token if available
    const token = getToken();
    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, config);
        
        // Handle 401 - try to refresh token
        if (response.status === 401 && getRefreshToken()) {
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                // Retry original request
                config.headers['Authorization'] = `Bearer ${getToken()}`;
                const retryResponse = await fetch(url, config);
                return await handleResponse(retryResponse);
            } else {
                // Refresh failed, logout
                removeTokens();
                window.location.href = 'index.html';
                return { success: false, message: 'Sesi habis, silakan login kembali' };
            }
        }
        
        return await handleResponse(response);
        
    } catch (error) {
        console.error('API Request Error:', error);
        return {
            success: false,
            message: 'Gagal terhubung ke server. Periksa koneksi internet Anda.'
        };
    }
}

async function handleResponse(response) {
    try {
        const data = await response.json();
        return data;
    } catch {
        return {
            success: false,
            message: `Error: ${response.status} ${response.statusText}`
        };
    }
}

async function refreshAccessToken() {
    try {
        const response = await fetch(`${CONFIG.API_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getRefreshToken()}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            setToken(data.access_token);
            return true;
        }
        return false;
    } catch {
        return false;
    }
}

// API Methods
const api = {
    get: (endpoint) => apiRequest(endpoint, { method: 'GET' }),
    post: (endpoint, data) => apiRequest(endpoint, { 
        method: 'POST', 
        body: JSON.stringify(data) 
    }),
    put: (endpoint, data) => apiRequest(endpoint, { 
        method: 'PUT', 
        body: JSON.stringify(data) 
    }),
    delete: (endpoint) => apiRequest(endpoint, { method: 'DELETE' })
};

// ============================================
// TOAST NOTIFICATIONS
// ============================================
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    // Set icon based on type
    const icons = {
        success: '<i class="fas fa-check-circle"></i>',
        error: '<i class="fas fa-times-circle"></i>',
        warning: '<i class="fas fa-exclamation-triangle"></i>',
        info: '<i class="fas fa-info-circle"></i>'
    };
    
    toast.innerHTML = `${icons[type] || ''} ${message}`;
    toast.className = `toast ${type}`;
    
    // Show toast
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Hide after duration
    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// ============================================
// DATE & TIME UTILITIES
// ============================================
function formatDate(dateStr, format = 'long') {
    const date = new Date(dateStr);
    const options = {
        long: { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' },
        short: { year: 'numeric', month: 'short', day: 'numeric' },
        iso: { year: 'numeric', month: '2-digit', day: '2-digit' }
    };
    
    return date.toLocaleDateString('id-ID', options[format] || options.long);
}

function formatTime(dateStr) {
    if (!dateStr) return '--:--';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('id-ID', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 11) return 'Pagi';
    if (hour < 15) return 'Siang';
    if (hour < 18) return 'Sore';
    return 'Malam';
}

function getCurrentDateFormatted() {
    return new Date().toLocaleDateString('id-ID', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function getToday() {
    return new Date().toISOString().split('T')[0];
}

function calculateWorkingDays(startDate, endDate) {
    let count = 0;
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    while (start <= end) {
        const day = start.getDay();
        if (day !== 0 && day !== 6) { // Exclude weekends
            count++;
        }
        start.setDate(start.getDate() + 1);
    }
    
    return count;
}

// ============================================
// LIVE CLOCK
// ============================================
function startLiveClock(elementId = 'liveClock') {
    function updateClock() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('id-ID', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            hour12: false 
        });
        
        const elements = document.querySelectorAll(`#${elementId}, #bigClock`);
        elements.forEach(el => {
            if (el) el.textContent = timeStr;
        });
    }
    
    updateClock();
    setInterval(updateClock, 1000);
}

// ============================================
// GEOLOCATION
// ============================================
function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation tidak didukung browser ini'));
            return;
        }
        
        navigator.geolocation.getCurrentPosition(
            (position) => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy
                });
            },
            (error) => {
                let message = 'Gagal mendapatkan lokasi';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        message = 'Izin lokasi ditolak. Aktifkan GPS dan izinkan akses lokasi.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        message = 'Informasi lokasi tidak tersedia';
                        break;
                    case error.TIMEOUT:
                        message = 'Waktu permintaan lokasi habis';
                        break;
                }
                reject(new Error(message));
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    });
}

async function getAddressFromCoords(lat, lon) {
    try {
        // Using OpenStreetMap Nominatim (free)
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=id`
        );
        const data = await response.json();
        return data.display_name || 'Alamat tidak ditemukan';
    } catch {
        return `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
    }
}

// ============================================
// UI HELPERS
// ============================================
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
}

function toggleUserMenu() {
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('userDropdown');
    const userInfo = document.querySelector('.user-info');
    
    if (dropdown && userInfo && !userInfo.contains(e.target)) {
        dropdown.classList.remove('show');
    }
});

// ============================================
// STATUS HELPERS
// ============================================
function getStatusBadge(status) {
    const statusMap = {
        present: { label: 'Hadir', class: 'success' },
        late: { label: 'Terlambat', class: 'warning' },
        absent: { label: 'Tidak Hadir', class: 'danger' },
        leave: { label: 'Cuti', class: 'info' },
        sick: { label: 'Sakit', class: 'info' },
        wfh: { label: 'WFH', class: 'primary' },
        early_leave: { label: 'Pulang Awal', class: 'warning' },
        pending: { label: 'Menunggu', class: 'warning' },
        approved: { label: 'Disetujui', class: 'success' },
        rejected: { label: 'Ditolak', class: 'danger' },
        cancelled: { label: 'Dibatalkan', class: 'secondary' }
    };
    
    const info = statusMap[status] || { label: status, class: 'secondary' };
    return `<span class="leave-status ${info.class}">${info.label}</span>`;
}

function getLeaveTypeName(type) {
    const types = {
        annual: 'Cuti Tahunan',
        sick: 'Sakit',
        maternity: 'Cuti Melahirkan',
        paternity: 'Cuti Ayah',
        marriage: 'Cuti Menikah',
        marriage_child: 'Menikahkan Anak',
        circumcision: 'Khitanan Anak',
        baptism: 'Pembaptisan Anak',
        bereavement_spouse: 'Duka (Keluarga Inti)',
        bereavement_family: 'Duka (Keluarga)',
        hajj: 'Ibadah Haji',
        unpaid: 'Cuti Tanpa Gaji',
        other: 'Izin Lainnya'
    };
    return types[type] || type;
}

// ============================================
// FORM HELPERS
// ============================================
function setMinDate(inputId, daysFromNow = 0) {
    const input = document.getElementById(inputId);
    if (input) {
        const date = new Date();
        date.setDate(date.getDate() + daysFromNow);
        input.min = date.toISOString().split('T')[0];
    }
}

function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const inputs = form.querySelectorAll('[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('error');
            isValid = false;
        } else {
            input.classList.remove('error');
        }
    });
    
    return isValid;
}

// ============================================
// EXPORT UTILITIES
// ============================================
// Make functions globally available
window.CONFIG = CONFIG;
window.getToken = getToken;
window.setToken = setToken;
window.getRefreshToken = getRefreshToken;
window.setRefreshToken = setRefreshToken;
window.removeTokens = removeTokens;
window.getUser = getUser;
window.setUser = setUser;
window.api = api;
window.showToast = showToast;
window.formatDate = formatDate;
window.formatTime = formatTime;
window.formatDateTime = formatDateTime;
window.getGreeting = getGreeting;
window.getCurrentDateFormatted = getCurrentDateFormatted;
window.getToday = getToday;
window.calculateWorkingDays = calculateWorkingDays;
window.startLiveClock = startLiveClock;
window.getCurrentLocation = getCurrentLocation;
window.getAddressFromCoords = getAddressFromCoords;
window.toggleSidebar = toggleSidebar;
window.toggleUserMenu = toggleUserMenu;
window.getStatusBadge = getStatusBadge;
window.getLeaveTypeName = getLeaveTypeName;
window.setMinDate = setMinDate;
window.validateForm = validateForm;
