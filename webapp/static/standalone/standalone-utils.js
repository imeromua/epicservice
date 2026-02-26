/**
 * standalone/standalone-utils.js
 * Перевизначення Utils для автономного режиму (без Telegram WebApp SDK).
 */
(function() {
    // Override Utils if it exists, or create it
    const originalUtils = window.Utils || {};

    window.Utils = Object.assign({}, originalUtils, {
        tg: {},
        getUserId: () => {
            const user = StandaloneAuth.getUser();
            return user ? user.id : 0;
        },
        getUserName: () => {
            const user = StandaloneAuth.getUser();
            return user ? (user.first_name || user.login) : 'Користувач';
        },
        haptic: {
            impact: () => { if (window.navigator?.vibrate) navigator.vibrate(10); },
            success: () => { if (window.navigator?.vibrate) navigator.vibrate([10, 50, 10]); },
            error: () => { if (window.navigator?.vibrate) navigator.vibrate([50, 30, 50]); },
            warning: () => { if (window.navigator?.vibrate) navigator.vibrate(30); },
            selection: () => { if (window.navigator?.vibrate) navigator.vibrate(5); }
        },
        showAlert: (message) => alert(message),
        showConfirm: (message, callback) => { callback(confirm(message)); },
        formatCurrency: originalUtils.formatCurrency || ((amount) => {
            const num = parseFloat(amount);
            if (isNaN(num)) return '0.00 ₴';
            return new Intl.NumberFormat('uk-UA', { style: 'decimal', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num) + ' ₴';
        }),
        debounce: originalUtils.debounce || ((func, wait) => {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func(...args), wait);
            };
        })
    });
})();
