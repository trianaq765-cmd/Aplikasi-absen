/**
 * Authentication Module
 * Sistem Absensi Karyawan 2025
 */

// ============================================
// LOGIN
// ============================================
async function login(email, password) {
    try {
        const result = await api.post('/auth/login', { email, password });
        
        if (result.success) {
            // Save tokens and user data
            setToken(result.data.access_token);
            setRefreshToken(result.data.refresh_token);
            setUser(result.data.employee);
            
            return { success: true };
        }
        
        return { success: false, message: result.message };
        
    } catch (error) {
        console.error('Login error:', error);
        return { success: false, message: 'Terjadi kesalahan saat login' };
    }
}

// ============================================
// LOGOUT
// ============================================
function logout() {
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
    
    // Public pages that don't require auth
    const publicPages = ['index.html', ''];
    
    if (!token && !publicPages.includes(currentPage)) {
        // Not logged in, redirect to login
        window.location.href = 'index.html';
        return false;
    }
    
    if (token && publicPages.includes(currentPage)) {
        // Already logged in, redirect to dashboard
        window.location.href = 'dashboard.html';
        return false;
    }
    
    // Load user info into header
    if (token) {
        loadUserHeader();
        checkAdminAccess();
    }
    
    return true;
}

// ============================================
// LOAD USER HEADER
// ============================================
function loadUserHeader() {
    const user = getUser();
    if (!user) return;
    
    // Update user name
    const nameElements = document.querySelectorAll('#userName, #welcomeName');
    nameElements.forEach(el => {
        if (el) el.textContent = user.name;
    });
    
    // Update user role
    const roleElement = document.getElementById('userRole');
    if (roleElement) {
        roleElement.textContent = getRoleLabel(user.role);
    }
    
    // Update avatar with initials
    const avatarElement = document.getElementById('userAvatar');
    if (avatarElement) {
        const initials = user.name.split(' ')
            .map(n => n[0])
            .slice(0, 2)
            .join('')
            .toUpperCase();
        avatarElement.innerHTML = initials;
    }
}

function getRoleLabel(role) {
    const roles = {
        admin: 'Administrator',
        hr: 'Human Resources',
        manager: 'Manager',
        employee: 'Karyawan'
    };
    return roles[role] || role;
}

// ============================================
// CHECK ADMIN ACCESS
// ============================================
function checkAdminAccess() {
    const user = getUser();
    if (!user) return;
    
    const adminRoles = ['admin', 'hr', 'manager'];
    const isAdmin = adminRoles.includes(user.role);
    
    // Show/hide admin menu items
    const adminElements = document.querySelectorAll('.admin-only');
    adminElements.forEach(el => {
        el.style.display = isAdmin ? '' : 'none';
    });
}

// ============================================
// GET PROFILE
// ============================================
async function getProfile() {
    const result = await api.get('/auth/profile');
    if (result.success) {
        setUser(result.data);
        return result.data;
    }
    return null;
}

// ============================================
// UPDATE PROFILE
// ============================================
async function updateProfile(data) {
    const result = await api.put('/auth/profile', data);
    if (result.success) {
        setUser(result.data);
        showToast('Profil berhasil diperbarui', 'success');
    } else {
        showToast(result.message || 'Gagal memperbarui profil', 'error');
    }
    return result;
}

// ============================================
// CHANGE PASSWORD
// ============================================
async function changePassword(oldPassword, newPassword) {
    const result = await api.post('/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword
    });
    
    if (result.success) {
        showToast('Password berhasil diubah', 'success');
    } else {
        showToast(result.message || 'Gagal mengubah password', 'error');
    }
    
    return result;
}

// ============================================
// REGISTER (Admin only)
// ============================================
async function registerEmployee(data) {
    const result = await api.post('/auth/register', data);
    
    if (result.success) {
        showToast('Karyawan berhasil didaftarkan', 'success');
    } else {
        showToast(result.message || 'Gagal mendaftarkan karyawan', 'error');
    }
    
    return result;
}

// ============================================
// EXPORT
// ============================================
window.login = login;
window.logout = logout;
window.checkAuth = checkAuth;
window.loadUserHeader = loadUserHeader;
window.getProfile = getProfile;
window.updateProfile = updateProfile;
window.changePassword = changePassword;
window.registerEmployee = registerEmployee;
