/**
 * Authentication Module - FIXED v2
 * Fix: Race condition saat login redirect
 */

// ============================================
// LOGIN - FIXED
// ============================================
async function login(email, password) {
    console.log('[Auth] Attempting login for:', email);
    
    try {
        const result = await api.post('/auth/login', { email, password });
        
        console.log('[Auth] Login result:', result);
        
        if (result.success && result.data) {
            // Save tokens FIRST
            if (result.data.access_token) {
                localStorage.setItem('absensi_token', result.data.access_token);
                console.log('[Auth] Access token saved');
            }
            
            if (result.data.refresh_token) {
                localStorage.setItem('absensi_refresh_token', result.data.refresh_token);
                console.log('[Auth] Refresh token saved');
            }
            
            // Save user data
            if (result.data.employee) {
                localStorage.setItem('absensi_user', JSON.stringify(result.data.employee));
                console.log('[Auth] User data saved:', result.data.employee.name);
            }
            
            // Verify token was saved
            const savedToken = localStorage.getItem('absensi_token');
            console.log('[Auth] Token verification:', savedToken ? 'OK' : 'FAILED');
            
            if (!savedToken) {
                return { success: false, message: 'Gagal menyimpan token' };
            }
            
            return { success: true };
        }
        
        return { success: false, message: result.message || 'Login gagal' };
        
    } catch (error) {
        console.error('[Auth] Login error:', error);
        return { success: false, message: 'Terjadi kesalahan saat login' };
    }
}

// ============================================
// LOGOUT
// ============================================
function logout() {
    console.log('[Auth] Logging out...');
    
    // Clear all auth data
    localStorage.removeItem('absensi_token');
    localStorage.removeItem('absensi_refresh_token');
    localStorage.removeItem('absensi_user');
    
    showToast('Anda telah keluar', 'info');
    
    // Redirect after toast shows
    setTimeout(() => {
        window.location.replace('index.html');
    }, 500);
}

// ============================================
// CHECK AUTH - FIXED
// ============================================
function checkAuth() {
    const token = localStorage.getItem('absensi_token');
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const isLoginPage = currentPage === 'index.html' || currentPage === '' || currentPage === 'login.html';
    
    console.log('[Auth] checkAuth called');
    console.log('[Auth] - Current page:', currentPage);
    console.log('[Auth] - Is login page:', isLoginPage);
    console.log('[Auth] - Token exists:', !!token);
    
    // Jika di halaman login dan sudah punya token -> ke dashboard
    if (isLoginPage && token) {
        console.log('[Auth] Has token on login page, redirecting to dashboard...');
        window.location.replace('dashboard.html');
        return false;
    }
    
    // Jika di halaman protected dan tidak punya token -> ke login
    if (!isLoginPage && !token) {
        console.log('[Auth] No token on protected page, redirecting to login...');
        window.location.replace('index.html');
        return false;
    }
    
    // Load user header jika ada token
    if (token) {
        loadUserHeader();
    }
    
    console.log('[Auth] checkAuth passed');
    return true;
}

// ============================================
// LOAD USER HEADER
// ============================================
function loadUserHeader() {
    try {
        const userStr = localStorage.getItem('absensi_user');
        if (!userStr) {
            console.log('[Auth] No user data in storage');
            return;
        }
        
        const user = JSON.parse(userStr);
        console.log('[Auth] Loading user header for:', user.name);
        
        // Update nama
        document.querySelectorAll('#userName, #welcomeName').forEach(el => {
            if (el) el.textContent = user.name || 'User';
        });
        
        // Update role
        const roleElement = document.getElementById('userRole');
        if (roleElement && user.role) {
            const roleLabels = {
                admin: 'Administrator',
                hr: 'Human Resources',
                manager: 'Manager',
                employee: 'Karyawan'
            };
            roleElement.textContent = roleLabels[user.role] || user.role;
        }
        
    } catch (e) {
        console.error('[Auth] Error loading user header:', e);
    }
}

// ============================================
// GET PROFILE
// ============================================
async function getProfile() {
    const result = await api.get('/auth/profile');
    
    if (result.success && result.data) {
        localStorage.setItem('absensi_user', JSON.stringify(result.data));
        loadUserHeader();
        return result.data;
    }
    
    return null;
}

// ============================================
// EXPORT GLOBAL
// ============================================
window.login = login;
window.logout = logout;
window.checkAuth = checkAuth;
window.loadUserHeader = loadUserHeader;
window.getProfile = getProfile;

console.log('[Auth] Module loaded');
