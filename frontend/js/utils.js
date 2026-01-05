const CONFIG = {
    API_URL: '/api',
    TOKEN_KEY: 'absensi_token',
    REFRESH_TOKEN_KEY: 'absensi_refresh_token',
    USER_KEY: 'absensi_user'
};

function getToken() { return localStorage.getItem(CONFIG.TOKEN_KEY); }
function setToken(token) { localStorage.setItem(CONFIG.TOKEN_KEY, token); }
function getRefreshToken() { return localStorage.getItem(CONFIG.REFRESH_TOKEN_KEY); }
function setRefreshToken(token) { localStorage.setItem(CONFIG.REFRESH_TOKEN_KEY, token); }
function removeTokens() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.REFRESH_TOKEN_KEY);
    localStorage.removeItem(CONFIG.USER_KEY);
}
function getUser() {
    const user = localStorage.getItem(CONFIG.USER_KEY);
    return user ? JSON.parse(user) : null;
}
function setUser(user) { localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user)); }

async function apiRequest(endpoint, options = {}) {
    const url = `${CONFIG.API_URL}${endpoint}`;
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    try {
        const response = await fetch(url, { ...options, headers: { ...headers, ...options.headers } });
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { success: false, message: 'Koneksi gagal' };
    }
}

const api = {
    get: (endpoint) => apiRequest(endpoint, { method: 'GET' }),
    post: (endpoint, data) => apiRequest(endpoint, { method: 'POST', body: JSON.stringify(data) }),
    put: (endpoint, data) => apiRequest(endpoint, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (endpoint) => apiRequest(endpoint, { method: 'DELETE' })
};

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatTime(dateStr) {
    if (!dateStr) return '--:--';
    return new Date(dateStr).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}

function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 11) return 'Pagi';
    if (hour < 15) return 'Siang';
    if (hour < 18) return 'Sore';
    return 'Malam';
}

function getCurrentDateFormatted() {
    return new Date().toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

function startLiveClock() {
    function update() {
        const now = new Date();
        const time = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        document.querySelectorAll('#liveClock, #bigClock').forEach(el => { if (el) el.textContent = time; });
    }
    update();
    setInterval(update, 1000);
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('open');
}

async function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation tidak didukung'));
            return;
        }
        navigator.geolocation.getCurrentPosition(
            pos => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy }),
            err => reject(err),
            { enableHighAccuracy: true, timeout: 10000 }
        );
    });
}

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
