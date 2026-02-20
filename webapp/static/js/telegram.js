/* =============================================
   TELEGRAM.JS - Telegram WebApp інтеграція
   ============================================= */

// Initialize Telegram WebApp
const tg = window.Telegram?.WebApp;

if (tg) {
    tg.expand();
    tg.ready();
    console.log('✅ Telegram WebApp initialized');
} else {
    console.warn('⚠️ Telegram WebApp not available');
}

// Export for global access
window.tg = tg;