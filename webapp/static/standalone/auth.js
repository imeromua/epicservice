/**
 * standalone/auth.js
 * Автентифікація для автономного додатку (без Telegram).
 * JWT login/password + біометрія (WebAuthn).
 */
const StandaloneAuth = (function() {
    const TOKEN_KEY = 'epicservice_access_token';
    const REFRESH_KEY = 'epicservice_refresh_token';
    const USER_KEY = 'epicservice_user';
    let isRegisterMode = false;

    function getToken() { return localStorage.getItem(TOKEN_KEY); }
    function getRefreshToken() { return localStorage.getItem(REFRESH_KEY); }
    function getUser() { try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; } }

    function saveSession(data) {
        localStorage.setItem(TOKEN_KEY, data.access_token);
        if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token);
        if (data.user) localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    }

    function clearSession() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        localStorage.removeItem(USER_KEY);
    }

    // Safely update global app state variables defined in standalone.html
    function _updateGlobals(id) {
        if (typeof window.userId !== 'undefined') window.userId = id;
        if (typeof window.ADMIN_IDS !== 'undefined') window.isAdmin = window.ADMIN_IDS.includes(id);
    }

    async function checkSession() {
        const token = getToken();
        if (!token) return null;
        try {
            const resp = await fetch('/api/auth/me', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (resp.ok) {
                const data = await resp.json();
                return data;
            }
            // Try refresh
            const refreshToken = getRefreshToken();
            if (refreshToken) {
                const refreshResp = await fetch('/api/auth/refresh', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: refreshToken })
                });
                if (refreshResp.ok) {
                    const refreshData = await refreshResp.json();
                    localStorage.setItem(TOKEN_KEY, refreshData.access_token);
                    // Re-check
                    const meResp = await fetch('/api/auth/me', {
                        headers: { 'Authorization': 'Bearer ' + refreshData.access_token }
                    });
                    if (meResp.ok) return await meResp.json();
                }
            }
            clearSession();
            return null;
        } catch (e) {
            // Offline mode - return cached user
            const user = getUser();
            if (user) return { user };
            return null;
        }
    }

    function showError(msg) {
        const el = document.getElementById('login-error');
        if (el) { el.textContent = msg; el.style.display = 'block'; }
    }

    function hideError() {
        const el = document.getElementById('login-error');
        if (el) el.style.display = 'none';
    }

    function hideLogin() {
        const overlay = document.getElementById('login-overlay');
        if (overlay) overlay.style.display = 'none';
        // Update user info
        const user = getUser();
        if (user) {
            const info = document.getElementById('userInfo');
            if (info) info.textContent = user.first_name || user.login;
        }
    }

    function showLogin() {
        const overlay = document.getElementById('login-overlay');
        if (overlay) overlay.style.display = 'flex';
    }

    async function login() {
        hideError();
        const loginVal = document.getElementById('login-input').value.trim();
        const passVal = document.getElementById('password-input').value;
        const nameInput = document.getElementById('name-input');

        if (!loginVal || !passVal) {
            showError('Введіть логін та пароль');
            return;
        }

        if (isRegisterMode) {
            const name = nameInput.value.trim();
            if (!name) { showError("Введіть ваше ім'я"); return; }
            try {
                const resp = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ login: loginVal, password: passVal, first_name: name })
                });
                const data = await resp.json();
                if (!resp.ok) { showError(data.detail || 'Помилка реєстрації'); return; }
                saveSession(data);
                _updateGlobals(data.user.id);
                hideLogin();
                if (typeof loadList === 'function' && userId) loadList();
            } catch (e) {
                showError("Помилка з'єднання з сервером");
            }
        } else {
            try {
                const resp = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ login: loginVal, password: passVal })
                });
                const data = await resp.json();
                if (!resp.ok) { showError(data.detail || 'Невірний логін або пароль'); return; }
                saveSession(data);
                _updateGlobals(data.user.id);
                hideLogin();
                if (typeof loadList === 'function' && userId) loadList();
            } catch (e) {
                showError("Помилка з'єднання з сервером");
            }
        }
    }

    function toggleRegister() {
        isRegisterMode = !isRegisterMode;
        const nameInput = document.getElementById('name-input');
        const regBtn = document.getElementById('register-btn');
        const loginBtn = document.getElementById('login-btn');
        if (isRegisterMode) {
            nameInput.style.display = 'block';
            regBtn.textContent = '↩️ Назад до входу';
            loginBtn.textContent = '📝 Зареєструватися';
        } else {
            nameInput.style.display = 'none';
            regBtn.textContent = '📝 Реєстрація';
            loginBtn.textContent = '🔐 Увійти';
        }
        hideError();
    }

    async function biometricLogin() {
        // WebAuthn biometric - check if credentials are stored
        if (!window.PublicKeyCredential) {
            showError('Біометрія не підтримується');
            return;
        }
        // For Android WebView, biometric auth is handled natively
        // This is a fallback for web browsers
        showError('Біометрія доступна тільки в Android додатку');
    }

    function logout() {
        clearSession();
        _updateGlobals(0);
        showLogin();
    }

    // Check biometric availability on load
    function checkBiometric() {
        // Show biometric button if there's a saved session
        if (getToken() || getUser()) {
            const btn = document.getElementById('biometric-btn');
            if (btn && window.AndroidBridge) btn.style.display = 'block';
        }
    }

    // Initialize
    setTimeout(checkBiometric, 100);

    return {
        getToken, getUser, checkSession, login, toggleRegister,
        biometricLogin, logout, hideLogin, showLogin, saveSession,
        clearSession, showError, hideError
    };
})();

if (typeof window !== 'undefined') window.StandaloneAuth = StandaloneAuth;
