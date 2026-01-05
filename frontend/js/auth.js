async function login(email, password) {
    const result = await api.post('/auth/login', { email, password });
    if (result.success) {
        setToken(result.data.access_token);
        setRefreshToken(result.data.refresh_token);
        setUser(result.data.employee);
    }
    return result;
}

function logout() {
    removeTokens();
    showToast('Anda telah keluar', 'info');
    setTimeout(() => window.location.href = 'index.html', 500);
}

function checkAuth() {
    const token = getToken();
    const page = window.location.pathname.split('/').pop() || 'index.html';
    
    if (!token && page !== 'index.html') {
        window.location.href = 'index.html';
        return false;
    }
    
    if (token) loadUserHeader();
    return true;
}

function loadUserHeader() {
    const user = getUser();
    if (!user) return;
    
    document.querySelectorAll('#userName, #welcomeName').forEach(el => {
        if (el) el.textContent = user.name;
    });
}

window.login = login;
window.logout = logout;
window.checkAuth = checkAuth;
window.loadUserHeader = loadUserHeader;
