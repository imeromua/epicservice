/**
 * js/utils.js
 * Допоміжні функції, форматування та безпечна обгортка для Telegram WebApp SDK.
 */

const Utils = (function() {
    // Отримуємо об'єкт Telegram WebApp (з урахуванням моку з pwa-redirect.js)
    const tg = window.Telegram?.WebApp || {};

    return {
        // Доступ до оригінального об'єкта
        tg: tg,
        
        // Інформація про користувача
        getUserId: () => tg.initDataUnsafe?.user?.id || 0,
        getUserName: () => tg.initDataUnsafe?.user?.first_name || 'Тестовий користувач',
        
        // Візуальний та тактильний зворотний зв'язок (Haptic Feedback)
        haptic: {
            impact: (style = 'light') => {
                if (tg.HapticFeedback?.impactOccurred) {
                    tg.HapticFeedback.impactOccurred(style);
                }
            },
            success: () => {
                if (tg.HapticFeedback?.notificationOccurred) {
                    tg.HapticFeedback.notificationOccurred('success');
                }
            },
            error: () => {
                if (tg.HapticFeedback?.notificationOccurred) {
                    tg.HapticFeedback.notificationOccurred('error');
                }
            },
            warning: () => {
                if (tg.HapticFeedback?.notificationOccurred) {
                    tg.HapticFeedback.notificationOccurred('warning');
                }
            },
            selection: () => {
                if (tg.HapticFeedback?.selectionChanged) {
                    tg.HapticFeedback.selectionChanged();
                }
            }
        },

        // Безпечні сповіщення (фолбек на стандартні браузерні, якщо tg API недоступне)
        showAlert: (message) => {
            if (tg.showAlert) {
                tg.showAlert(message);
            } else {
                alert(message);
            }
        },

        showConfirm: (message, callback) => {
            if (tg.showConfirm) {
                tg.showConfirm(message, callback);
            } else {
                const result = confirm(message);
                callback(result);
            }
        },

        // Форматування валюти (щоб скрізь по додатку ціни виглядали однаково)
        formatCurrency: (amount) => {
            const num = parseFloat(amount);
            if (isNaN(num)) return '0.00 ₴';
            return new Intl.NumberFormat('uk-UA', {
                style: 'decimal',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(num) + ' ₴';
        },

        // Оптимізація частих викликів (наприклад, для інпуту пошуку)
        debounce: (func, wait) => {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    };
})();

// Експорт у глобальну область видимості
if (typeof window !== 'undefined') {
    window.Utils = Utils;
}