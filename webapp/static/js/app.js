/* =============================================
   APP.JS - Ініціалізація додатку та глобальний стан
   ============================================= */

// Global State
const AppState = {
    userId: 0,
    isAdmin: false,
    ADMIN_IDS: [],
    currentTab: 'search',
    currentDepartment: null,
    cachedProducts: [],
    cachedProductsInfo: null,
    
    // Modal state
    selectedProduct: null,
    editingItem: null,
    currentQuantity: 1,
    editQuantity: 1,
    
    // UI state
    searchTimeout: null,
    pullStartY: 0,
    pulling: false,
    selectedFile: null
};

// Initialize application
function initApp(adminIds) {
    console.log('🚀 Initializing EpicService...');
    
    AppState.ADMIN_IDS = adminIds;
    AppState.userId = window.tg?.initDataUnsafe?.user?.id || 0;
    AppState.isAdmin = AppState.ADMIN_IDS.includes(AppState.userId);
    
    // Show admin tab if user is admin
    if (AppState.isAdmin) {
        const adminBtn = document.getElementById('adminTabBtn');
        if (adminBtn) adminBtn.classList.remove('hidden');
    }
    
    // Update user info in header
    const userInfo = document.getElementById('userInfo');
    if (userInfo) {
        const firstName = window.tg?.initDataUnsafe?.user?.first_name || 'User';
        const adminBadge = AppState.isAdmin ? ' 👑' : '';
        userInfo.textContent = AppState.userId 
            ? `Користувач: ${firstName}${adminBadge}` 
            : 'Тестовий режим';
    }
    
    // Load initial data
    if (AppState.userId) {
        loadList();
    }
    
    updateSearchBoxVisibility();
    
    console.log('✅ App initialized:', {
        userId: AppState.userId,
        isAdmin: AppState.isAdmin,
        adminIds: AppState.ADMIN_IDS
    });
    
    console.log('📱 Display mode:', 
        window.matchMedia('(display-mode: standalone)').matches ? 'Standalone (PWA)' : 'Browser'
    );
}

// Export for global access
window.AppState = AppState;
window.initApp = initApp;