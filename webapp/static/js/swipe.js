/**
 * swipe.js - Горизонтальний свайп між вкладками
 * Використовує існуючу функцію switchTab() з core.js
 */

(function() {
    'use strict';

    // Порядок вкладок (відповідає порядку в HTML)
    const TAB_ORDER = ['search', 'list', 'archives', 'admin'];
    
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;
    const MIN_SWIPE_DISTANCE = 50; // Мінімальна дистанція свайпу (px)
    const MAX_VERTICAL_RATIO = 0.6; // Макс відношення вертикального руху до горизонтального

    // Отримати поточну активну вкладку
    function getCurrentTab() {
        const activeContent = document.querySelector('.content.active');
        if (!activeContent) return null;
        return activeContent.id.replace('Tab', '').replace('Content', '');
    }

    // Отримати доступні вкладки (враховуючи видимість Адміна)
    function getAvailableTabs() {
        const adminBtn = document.getElementById('adminTabBtn');
        if (adminBtn && adminBtn.classList.contains('hidden')) {
            return TAB_ORDER.filter(tab => tab !== 'admin');
        }
        return TAB_ORDER;
    }

    // Наступна вкладка
    function getNextTab(currentTab) {
        const availableTabs = getAvailableTabs();
        const currentIndex = availableTabs.indexOf(currentTab);
        if (currentIndex === -1 || currentIndex === availableTabs.length - 1) return null;
        return availableTabs[currentIndex + 1];
    }

    // Попередня вкладка
    function getPreviousTab(currentTab) {
        const availableTabs = getAvailableTabs();
        const currentIndex = availableTabs.indexOf(currentTab);
        if (currentIndex <= 0) return null;
        return availableTabs[currentIndex - 1];
    }

    // Обробка touchstart
    function handleTouchStart(e) {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }

    // Обробка touchend
    function handleTouchEnd(e) {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        handleSwipe();
    }

    // Визначення напрямку свайпу та перемикання
    function handleSwipe() {
        const dx = touchEndX - touchStartX;
        const dy = touchEndY - touchStartY;
        const absDx = Math.abs(dx);
        const absDy = Math.abs(dy);

        // Фільтруємо вертикальний скрол
        if (absDx < MIN_SWIPE_DISTANCE) return;
        if (absDy > absDx * MAX_VERTICAL_RATIO) return;

        const currentTab = getCurrentTab();
        if (!currentTab) return;

        let targetTab = null;
        let direction = null;

        if (dx > 0) {
            // Свайп вправо → попередня вкладка
            targetTab = getPreviousTab(currentTab);
            direction = 'right';
        } else {
            // Свайп вліво → наступна вкладка
            targetTab = getNextTab(currentTab);
            direction = 'left';
        }

        if (targetTab && typeof window.switchTab === 'function') {
            // Встановлюємо напрямок для CSS анімації
            document.body.setAttribute('data-swipe', direction);
            window.switchTab(targetTab);
            // Прибираємо атрибут після завершення анімації
            setTimeout(() => {
                document.body.removeAttribute('data-swipe');
            }, 300);
        }
    }

    // Ініціалізація
    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    document.addEventListener('touchend', handleTouchEnd, { passive: true });

    console.log('[✅] Swipe navigation enabled');
})();
