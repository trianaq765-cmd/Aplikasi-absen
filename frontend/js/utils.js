/**
 * Utility Functions - FIXED VERSION
 */

const CONFIG = {
    API_URL: '/api',
    TOKEN_KEY: 'absensi_token',
    REFRESH_TOKEN_KEY: 'absensi_refresh_token',
    USER_KEY: 'absensi_user'
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
    try {
        const user = localStorage.getItem(CONFIG.USER_KEY);
        return user ? JSON.parse(user) : null;
    } catch (e) {
        console.error('Error parsing user:', e);
        return null;
    }
}

function setUser(user) {
    localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
}

// ============================================
// API REQUEST - FIXED
// ============================================
async function apiRequest(endpoint, options = {}) {
    const url = `${CONFIG.API_URL}${endpoint}`;
    
    // Default headers
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    };
    
    // Add token if exists
    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Merge options
    const config = {
        method: options.method || 'GET',
        headers: { ...headers, ...options.headers }
    };
    
    // Add body for POST/PUT
    if (options.body) {
        config.body = options.body;
    }
    
    console.log(`[API] ${config.method} ${url}`);
    
    try {
        const response = await fetch(url, config);
        
        console.log(`[API] Response status: ${response.status}`);
        
        // Handle 401 Unauthorized
        if (response.status === 401) {
            console.log('[API] Token expired or invalid');
            
            // Try refresh token
            const refreshToken = getRefreshToken();
            if (refreshToken && !endpoint.includes('/auth/')) {
                console.log('[API] Trying to refresh token...');
                const refreshed = await refreshAccessToken();
                
                if (refreshed) {
                    // Retry with new token
                    headers['Authorization'] = `Bearer ${getToken()}`;
                    config.headers = headers;
                    
                    const retryResponse = await fetch(url, config);
                    const retryData = await retryResponse.json();
                    return retryData;
                }
            }
            
            // Refresh failed or no refresh token
            removeTokens();
            if (!window.location.pathname.includes('index.html')) {
                window.location.href = 'index.html';
            }
            return { success: false, message: 'Sesi habis, silakan login kembali' };
        }
        
        // Parse response
        const data = await response.json();
        console.log('[API] Response data:', data);
        
        return data;
        
    } catch (error) {
        console.error('[API] Error:', error);
        return {
            success: false,
            message: 'Gagal terhubung ke server: ' + error.message
        };
    }
}

async function refreshAccessToken() {
    try {
        const refreshToken = getRefreshToken();
        if (!refreshToken) return false;
        
        const response = await fetch(`${CONFIG.API_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${refreshToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.access_token) {
                setToken(data.access_token);
                console.log('[API] Token refreshed successfully');
                return true;
            }
        }
        
        return false;
    } catch (error) {
        console.error('[API] Refresh token error:', error);
        return false;
    }
}

// API helper methods
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
    if (!toast) {
        console.log(`[Toast] ${type}: ${message}`);
        return;
    }
    
    // Icon berdasarkan type
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    
    toast.innerHTML = `${icons[type] || ''} ${message}`;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// ============================================
// DATE/TIME UTILITIES
// ============================================
function formatDate(dateStr, format = 'short') {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        if (format === 'short') {
            return date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
        }
        return date.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    } catch (e) {
        return dateStr;
    }
}

function formatTime(dateStr) {
    if (!dateStr) return '--:--';
    try {
        const date = new Date(dateStr);
        return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return '--:--';
    }
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
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}

function startLiveClock() {
    function update() {
        const now = new Date();
        const time = now.toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        
        const elements = document.querySelectorAll('#liveClock, #bigClock');
        elements.forEach(el => {
            if (el) el.textContent = time;
        });
    }
    
    update();
    setInterval(update, 1000);
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

// ============================================
// GEOLOCATION
// ============================================
async function getCurrentLocation() {
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
                        message = 'Izin lokasi ditolak. Aktifkan GPS.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        message = 'Lokasi tidak tersedia';
                        break;
                    case error.TIMEOUT:
                        message = 'Timeout mendapatkan lokasi';
                        break;
                }
                reject(new Error(message));
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 60000
            }
        );
    });
}

// ============================================
// EXPORT GLOBAL
// ============================================
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
window.getGreeting = getGreeting;
window.getCurrentDateFormatted = getCurrentDateFormatted;
window.startLiveClock = startLiveClock;
window.toggleSidebar = toggleSidebar;
window.getCurrentLocation = getCurrentLocation;

console.log('[Utils] Loaded successfully');
