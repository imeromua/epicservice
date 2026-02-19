// PWA Telegram Integration
// Цей скрипт перевіряє чи додаток відкрито як PWA та забезпечує інтеграцію з Telegram

(function() {
    'use strict';
    
    // Перевірка чи запущено як PWA
    const isPWA = window.matchMedia('(display-mode: standalone)').matches || 
                  window.navigator.standalone === true;
    
    console.log('[PWA] Режим запуску:', isPWA ? 'PWA (Standalone)' : 'Браузер');
    
    if (isPWA) {
        console.log('[PWA] Додаток запущено як PWA');
        
        // Перевіряємо чи є Telegram WebApp SDK
        if (!window.Telegram || !window.Telegram.WebApp) {
            console.warn('[PWA] Telegram WebApp SDK не знайдено в PWA режимі');
            
            // Створюємо mock об'єкт для PWA режиму
            window.Telegram = window.Telegram || {};
            window.Telegram.WebApp = {
                initDataUnsafe: {
                    user: {
                        id: 0,
                        first_name: 'PWA User',
                        username: 'pwa_user'
                    }
                },
                ready: function() {
                    console.log('[PWA] WebApp ready (mock)');
                },
                expand: function() {
                    console.log('[PWA] WebApp expand (mock)');
                },
                showAlert: function(message) {
                    alert(message);
                },
                HapticFeedback: {
                    impactOccurred: function() {},
                    notificationOccurred: function() {}
                },
                MainButton: {
                    text: '',
                    show: function() {},
                    hide: function() {},
                    onClick: function() {}
                },
                version: 'PWA-Mock'
            };
            
            // Додаємо повідомлення для користувача
            document.addEventListener('DOMContentLoaded', function() {
                // Змінюємо текст userInfo
                const userInfo = document.getElementById('userInfo');
                if (userInfo) {
                    userInfo.innerHTML = 'Режим PWA 📱 | <a href="https://t.me/your_bot_name/app" style="color: var(--link-color);">Відкрити в Telegram</a>';
                }
                
                // Додаємо інформаційний банер
                showPWAInfo();
            });
        } else {
            console.log('[PWA] Telegram WebApp SDK знайдено');
        }
    }
    
    function showPWAInfo() {
        // Перевіряємо чи вже показували повідомлення
        const shown = localStorage.getItem('pwa_info_shown');
        if (shown) return;
        
        const banner = document.createElement('div');
        banner.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            padding: 16px;
            z-index: 10001;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            animation: slideDown 0.3s ease-out;
        `;
        
        banner.innerHTML = `
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; margin-bottom: 6px; font-size: 16px;">📱 Додаток встановлено!</div>
                        <div style="font-size: 13px; opacity: 0.95; line-height: 1.4;">
                            Для повного функціоналу відкрийте через Telegram Web App.
                            Зараз ви працюєте в демо-режимі.
                        </div>
                    </div>
                    <button onclick="this.parentElement.parentElement.parentElement.remove(); localStorage.setItem('pwa_info_shown', 'true');" 
                            style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 14px; white-space: nowrap;">
                        Зрозуміло
                    </button>
                </div>
            </div>
        `;
        
        document.body.insertBefore(banner, document.body.firstChild);
        
        // Автоматично приховати через 10 секунд
        setTimeout(() => {
            banner.remove();
            localStorage.setItem('pwa_info_shown', 'true');
        }, 10000);
    }
    
    // Додаємо CSS анімацію
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideDown {
            from {
                transform: translateY(-100%);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
    
})();
