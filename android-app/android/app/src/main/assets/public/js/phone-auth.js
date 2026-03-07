/**
 * www/js/phone-auth.js
 * Модуль автентифікації за номером телефону (OTP) та логіном/паролем.
 * Підтримує онлайн та офлайн режими.
 */
const PhoneAuth = (function () {
    'use strict';

    // --- Конфігурація ---
    const SERVER = window.APP_CONFIG?.serverUrl || 'https://anubis-ua.pp.ua';
    const TOKEN_KEY = 'epic_access_token';
    const REFRESH_KEY = 'epic_refresh_token';
    const USER_KEY = 'epic_user';
    const PHONE_KEY = 'epic_phone';

    // --- Стан ---
    let _currentPhone = '';
    let _isNewUser = false;
    let _isRegisterMode = false;
    let _otpTimer = null;
    let _otpSecondsLeft = 0;

    // --- Сховище ---
    function saveSession(data) {
        if (data.access_token) localStorage.setItem(TOKEN_KEY, data.access_token);
        if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token);
        if (data.user) {
            localStorage.setItem(USER_KEY, JSON.stringify(data.user));
            if (data.user.phone) localStorage.setItem(PHONE_KEY, data.user.phone);
        }
    }

    function clearSession() {
        [TOKEN_KEY, REFRESH_KEY, USER_KEY, PHONE_KEY].forEach(k => localStorage.removeItem(k));
    }

    function getToken() { return localStorage.getItem(TOKEN_KEY); }
    function getRefreshToken() { return localStorage.getItem(REFRESH_KEY); }
    function getUser() {
        try { return JSON.parse(localStorage.getItem(USER_KEY)); }
        catch { return null; }
    }

    // --- Ініціалізація ---
    async function init() {
        _setupOtpInputs();
        const user = await checkSession();
        if (user) {
            _showApp(user.user || user);
        } else {
            _showScreen('auth-screen');
        }
    }

    async function checkSession() {
        const token = getToken();
        if (!token) return null;
        try {
            const resp = await EpicAPI.get('/api/auth/me', token);
            if (resp.success) {
                saveSession({ user: resp.user });
                return resp;
            }
            // Спробуємо оновити токен
            const refreshToken = getRefreshToken();
            if (refreshToken) {
                const refreshResp = await EpicAPI.post('/api/auth/refresh', { refresh_token: refreshToken });
                if (refreshResp.success) {
                    localStorage.setItem(TOKEN_KEY, refreshResp.access_token);
                    // Persist rotated refresh token if server returned one
                    if (refreshResp.refresh_token) localStorage.setItem(REFRESH_KEY, refreshResp.refresh_token);
                    const meResp = await EpicAPI.get('/api/auth/me', refreshResp.access_token);
                    if (meResp.success) {
                        saveSession({ user: meResp.user });
                        return meResp;
                    }
                }
            }
            clearSession();
            return null;
        } catch {
            // Офлайн-режим — використовуємо кешованого користувача
            const user = getUser();
            if (user) return { user, offline: true };
            return null;
        }
    }

    // --- Показ екранів ---
    function _showScreen(id) {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        const el = document.getElementById(id);
        if (el) el.classList.add('active');
    }

    function _showStep(id) {
        ['phone-step', 'otp-step', 'login-step'].forEach(s => {
            const el = document.getElementById(s);
            if (el) el.style.display = s === id ? 'block' : 'none';
        });
    }

    function _showApp(user) {
        _showScreen('app-screen');
        // Оновлюємо UI заголовку
        const avatar = document.getElementById('user-avatar');
        const nameEl = document.getElementById('user-name');
        const menuName = document.getElementById('menu-user-name');
        const menuRole = document.getElementById('menu-user-role');
        const menuPhone = document.getElementById('menu-user-phone');

        if (avatar) avatar.textContent = (user.first_name || user.login || '?')[0].toUpperCase();
        if (nameEl) nameEl.textContent = user.first_name || user.login || 'Користувач';
        if (menuName) menuName.textContent = user.first_name || user.login || '';
        if (menuRole) menuRole.textContent = _roleLabel(user.role);
        if (menuPhone && user.phone) {
            menuPhone.textContent = user.phone;
            menuPhone.style.display = 'block';
        }

        // Показуємо вкладку адміна якщо потрібно
        if (['admin', 'superadmin'].includes(user.role)) {
            document.getElementById('tab-admin')?.classList.remove('hidden');
        }

        // Ініціалізуємо головний модуль
        if (typeof App !== 'undefined') {
            App.init(user, getToken());
        }
    }

    function _roleLabel(role) {
        const labels = {
            user: '👤 Користувач',
            moderator: '🎭 Модератор',
            admin: '🛡️ Адміністратор',
            superadmin: '⚡ Супер-адмін',
        };
        return labels[role] || role || '—';
    }

    // --- Помилки ---
    function _showError(elId, msg) {
        const el = document.getElementById(elId);
        if (el) { el.textContent = msg; el.style.display = 'block'; }
    }
    function _hideError(elId) {
        const el = document.getElementById(elId);
        if (el) el.style.display = 'none';
    }

    // --- Нормалізація номера ---
    function normalizePhone(raw) {
        const digits = raw.replace(/\D/g, '');
        if (digits.startsWith('380') && digits.length === 12) return `+${digits}`;
        if (digits.startsWith('80') && digits.length === 11) return `+3${digits}`;
        if (digits.length === 10 && digits.startsWith('0')) return `+38${digits}`;
        return raw.startsWith('+') ? raw : `+${digits}`;
    }

    function validateUAPhone(phone) {
        return /^\+380\d{9}$/.test(phone);
    }

    // --- Форматування введення номера ---
    (function _initPhoneFormat() {
        const input = document.getElementById('phone-input');
        if (!input) return;
        input.addEventListener('input', function () {
            let val = this.value.replace(/[^\d+]/g, '');
            if (!val.startsWith('+')) val = '+' + val;
            this.value = val;
        });
        input.addEventListener('focus', function () {
            if (!this.value) this.value = '+380';
        });
    })();

    // --- Крок 1: Запит OTP ---
    async function requestOtp() {
        _hideError('auth-error');
        const rawPhone = document.getElementById('phone-input')?.value?.trim() || '';
        const phone = normalizePhone(rawPhone);
        const firstName = document.getElementById('name-input')?.value?.trim() || '';

        if (!validateUAPhone(phone)) {
            _showError('auth-error', '⚠️ Введіть коректний номер: +380XXXXXXXXX');
            return;
        }

        const btn = document.getElementById('send-otp-btn');
        _setLoading(btn, true, '📲 Відправка...');

        try {
            const data = await EpicAPI.post('/api/auth/phone/request', { phone });
            _currentPhone = phone;
            _isNewUser = !data.registered;

            // Якщо новий користувач — показуємо поле для імені
            if (_isNewUser && !firstName) {
                const nameGroup = document.getElementById('name-group');
                if (nameGroup) nameGroup.style.display = 'flex';
                _hideError('auth-error');
                _setLoading(btn, false, '📲 Отримати код');
                App.toast('Новий обліковий запис — введіть ім\'я', 'info');
                return;
            }

            const hint = document.getElementById('otp-hint');
            if (hint) {
                hint.textContent = data.sent_via_bot
                    ? `✅ Код надіслано у Telegram-бот (${phone})`
                    : `🔐 Код згенеровано для ${phone}`;
            }

            _showStep('otp-step');
            _startOtpTimer();
            _focusFirstOtpDigit();
            App.toast('Код підтвердження надіслано', 'success');
        } catch (e) {
            _showError('auth-error', e.message || 'Помилка з\'єднання. Перевірте інтернет.');
        } finally {
            _setLoading(btn, false, '📲 Отримати код');
        }
    }

    // --- Крок 2: Підтвердження OTP ---
    async function verifyOtp() {
        _hideError('auth-error-otp');
        const digits = Array.from(document.querySelectorAll('.otp-digit'));
        const otp = digits.map(d => d.value).join('');

        if (otp.length < 6) {
            _showError('auth-error-otp', '⚠️ Введіть усі 6 цифр коду');
            return;
        }

        const firstName = document.getElementById('name-input')?.value?.trim() || 'Користувач';
        const btn = document.getElementById('verify-otp-btn');
        _setLoading(btn, true, '⏳ Перевірка...');

        try {
            const payload = { phone: _currentPhone, otp };
            if (_isNewUser) payload.first_name = firstName;

            const data = await EpicAPI.post('/api/auth/phone/verify', payload);
            saveSession(data);
            _stopOtpTimer();
            _showApp(data.user);
            App.toast(`Ласкаво просимо, ${data.user.first_name || ''}! 🎉`, 'success');
        } catch (e) {
            _showError('auth-error-otp', e.message || 'Невірний код. Спробуйте ще раз.');
            _shakeOtpInputs();
        } finally {
            _setLoading(btn, false, '✅ Підтвердити');
        }
    }

    // --- Таймер OTP ---
    function _startOtpTimer() {
        _otpSecondsLeft = 5 * 60;
        const timerEl = document.getElementById('otp-timer');
        const resendBtn = document.getElementById('resend-btn');
        const countdownEl = document.getElementById('otp-countdown');

        if (timerEl) timerEl.style.display = 'block';
        if (resendBtn) resendBtn.style.display = 'none';

        _otpTimer = setInterval(() => {
            _otpSecondsLeft--;
            if (countdownEl) {
                const m = Math.floor(_otpSecondsLeft / 60);
                const s = _otpSecondsLeft % 60;
                countdownEl.textContent = `${m}:${s.toString().padStart(2, '0')}`;
            }
            if (_otpSecondsLeft <= 0) {
                clearInterval(_otpTimer);
                if (timerEl) timerEl.style.display = 'none';
                if (resendBtn) resendBtn.style.display = 'block';
            }
        }, 1000);
    }

    function _stopOtpTimer() {
        if (_otpTimer) { clearInterval(_otpTimer); _otpTimer = null; }
    }

    async function resendOtp() {
        _stopOtpTimer();
        document.querySelectorAll('.otp-digit').forEach(d => { d.value = ''; d.classList.remove('filled'); });
        await requestOtp();
    }

    function backToPhone() {
        _stopOtpTimer();
        _showStep('phone-step');
    }

    // --- OTP inputs setup ---
    function _setupOtpInputs() {
        const digits = document.querySelectorAll('.otp-digit');
        digits.forEach((input, i) => {
            input.addEventListener('input', function () {
                const val = this.value.replace(/\D/g, '');
                this.value = val ? val[0] : '';
                this.classList.toggle('filled', !!this.value);
                if (this.value && i < digits.length - 1) digits[i + 1].focus();
                // Автоматична перевірка при повному введенні
                const allFilled = Array.from(digits).every(d => d.value);
                if (allFilled) setTimeout(verifyOtp, 200);
            });
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Backspace' && !this.value && i > 0) {
                    digits[i - 1].focus();
                    digits[i - 1].value = '';
                    digits[i - 1].classList.remove('filled');
                }
            });
            input.addEventListener('paste', function (e) {
                e.preventDefault();
                const text = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
                digits.forEach((d, j) => {
                    d.value = text[j] || '';
                    d.classList.toggle('filled', !!d.value);
                });
                if (text.length >= 6) setTimeout(verifyOtp, 200);
                else if (text.length > 0) digits[Math.min(text.length, digits.length - 1)].focus();
            });
        });
    }

    function _focusFirstOtpDigit() {
        setTimeout(() => document.querySelector('.otp-digit')?.focus(), 300);
    }

    function _shakeOtpInputs() {
        const container = document.getElementById('otp-inputs');
        if (!container) return;
        container.style.animation = 'none';
        container.offsetHeight; // reflow
        container.style.animation = 'shake 0.4s ease';
    }

    // Додаємо анімацію shake
    if (!document.querySelector('#shake-style')) {
        const style = document.createElement('style');
        style.id = 'shake-style';
        style.textContent = `
            @keyframes shake {
                0%, 100% { transform: none; }
                20%, 60% { transform: translateX(-6px); }
                40%, 80% { transform: translateX(6px); }
            }
        `;
        document.head.appendChild(style);
    }

    // --- Логін/Пароль ---
    function switchToLogin() { _showStep('login-step'); }
    function switchToPhone() { _showStep('phone-step'); }

    function toggleRegister() {
        _isRegisterMode = !_isRegisterMode;
        const nameInput = document.getElementById('reg-name-input');
        const regBtn = document.getElementById('reg-toggle-btn');
        const loginBtn = document.getElementById('login-btn');
        if (nameInput) nameInput.style.display = _isRegisterMode ? 'block' : 'none';
        if (regBtn) regBtn.textContent = _isRegisterMode ? '↩️ Назад до входу' : '📝 Реєстрація';
        if (loginBtn) loginBtn.textContent = _isRegisterMode ? '📝 Зареєструватися' : '🔐 Увійти';
        _hideError('auth-error-login');
    }

    async function loginWithPassword() {
        _hideError('auth-error-login');
        const login = document.getElementById('login-input')?.value?.trim();
        const pass = document.getElementById('password-input')?.value;
        const btn = document.getElementById('login-btn');

        if (!login || !pass) {
            _showError('auth-error-login', '⚠️ Введіть логін та пароль');
            return;
        }

        _setLoading(btn, true, '⏳ Вхід...');

        try {
            let data;
            if (_isRegisterMode) {
                const name = document.getElementById('reg-name-input')?.value?.trim();
                if (!name) { _showError('auth-error-login', '⚠️ Введіть ваше ім\'я'); return; }
                data = await EpicAPI.post('/api/auth/register', { login, password: pass, first_name: name });
            } else {
                data = await EpicAPI.post('/api/auth/login', { login, password: pass });
            }
            saveSession(data);
            _showApp(data.user);
        } catch (e) {
            _showError('auth-error-login', e.message || 'Невірний логін або пароль');
        } finally {
            _setLoading(btn, false, _isRegisterMode ? '📝 Зареєструватися' : '🔐 Увійти');
        }
    }

    // --- Вихід ---
    function logout() {
        const token = getToken();
        const refreshToken = getRefreshToken();
        clearSession();
        _currentPhone = '';
        _stopOtpTimer();
        _showStep('phone-step');
        _showScreen('auth-screen');
        // Скидаємо форму
        const phoneInput = document.getElementById('phone-input');
        if (phoneInput) phoneInput.value = '';
        document.querySelectorAll('.otp-digit').forEach(d => { d.value = ''; d.classList.remove('filled'); });
        if (typeof App !== 'undefined') App.reset();
        App.toast('Ви вийшли з системи', 'info');
        // Notify server to revoke both tokens (fire-and-forget; ignore errors)
        if (token) {
            const body = refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : undefined;
            fetch(SERVER + '/api/auth/logout', {
                method: 'POST',
                headers: Object.assign({ 'Authorization': 'Bearer ' + token }, body ? { 'Content-Type': 'application/json' } : {}),
                body,
            }).catch(() => {});
        }
    }

    // --- Хелпер: стан кнопки ---
    function _setLoading(btn, loading, text) {
        if (!btn) return;
        btn.disabled = loading;
        btn.textContent = text;
    }

    return {
        init,
        checkSession,
        getToken,
        getUser,
        requestOtp,
        verifyOtp,
        resendOtp,
        backToPhone,
        switchToLogin,
        switchToPhone,
        toggleRegister,
        loginWithPassword,
        logout,
        saveSession,
        clearSession,
    };
})();

// Автоматичний старт
document.addEventListener('DOMContentLoaded', () => PhoneAuth.init());
