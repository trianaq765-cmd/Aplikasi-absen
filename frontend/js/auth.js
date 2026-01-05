/**
 * Authentication Module - FIXED VERSION
 */

// ============================================
// LOGIN
// ============================================
async function login(email, password) {
    console.log('[Auth] Attempting login for:', email);
    
    try {
        const result = await api.post('/auth/login', { email, password });
        
        console.log('[Auth] Login result:', result);
        
        if (result.success && result.data) {
            // Save tokens
            if (result.data.access_token) {
                setToken(result.data.access_token);
                console.log('[Auth] Access token saved');
            }
            
            if (result.data.refresh_token) {
                setRefreshToken(result.data.refresh_token);
                console.log('[Auth] Refresh token saved');
            }
            
            // Save user data
            if (result.data.employee) {
                setUser(result.data.employee);
                console.log('[Auth] User data saved:', result.data.employee.name);
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
    removeTokens();
    showToast('Anda telah keluar', 'info');
    setTimeout(() => {
        window.location.href = 'index.html';
    }, 500);
}

// ============================================
// CHECK AUTH
// ============================================
function checkAuth() {
    const token = getToken();
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const publicPages = ['index.html', '', 'login.html'];
    
    console.log('[Auth] Checking auth, token exists:', !!token, ', page:', currentPage);
    
    if (!token && !publicPages.includes(currentPage)) {
        console.log('[Auth] No token, redirecting to login');
        window.location.href = 'index.html';
        return false;
    }
    
    if (token && publicPages.includes(currentPage)) {
        console.log('[Auth] Has token on public page, redirecting to dashboard');
        window.location.href = 'dashboard.html';
        return false;
    }
    
    if (token) {
        loadUserHeader();
    }
    
    return true;
}

// ============================================
// LOAD USER HEADER
// ============================================
function loadUserHeader() {
    const user = getUser();
    console.log('[Auth] Loading user header:', user);
    
    if (!user) {
        console.log('[Auth] No user data found');
        return;
    }
    
    // Update nama user di header
    const nameElements = document.querySelectorAll('#userName, #welcomeName');
    nameElements.forEach(el => {
        if (el) el.textContent = user.name || 'User';
    });
    
    // Update role jika ada
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
}

// ============================================
// GET PROFILE (untuk refresh data user)
// ============================================
async function getProfile() {
    console.log('[Auth] Getting profile...');
    
    const result = await api.get('/auth/profile');
    
    if (result.success && result.data) {
        setUser(result.data);
        loadUserHeader();
        return result.data;
    }
    
    console.log('[Auth] Failed to get profile:', result.message);
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

console.log('[Auth] Loaded successfully');
