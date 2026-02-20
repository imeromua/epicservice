/* =============================================
   MAIN.JS - Головний ініціалізатор
   Initialize all modules and event listeners
   ============================================= */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 EpicService starting...');
    
    // Get ADMIN_IDS from template (passed from backend)
    const adminIds = window.ADMIN_IDS_FROM_TEMPLATE || [];
    
    // Initialize app
    initApp(adminIds);
    
    // Initialize modules
    initSearch();
    initPullToRefresh();
    
    // Initialize file upload for admin
    if (AppState.isAdmin) {
        initFileUpload();
    }
    
    // Initialize offline/online detection
    initNetworkDetection();
    
    console.log('✅ EpicService initialized successfully');
});

// Network detection
function initNetworkDetection() {
    const offlineIndicator = document.getElementById('offline-indicator');
    
    if (offlineIndicator) {
        window.addEventListener('online', () => {
            offlineIndicator.classList.remove('show');
            console.log('[✅] З\'\u0454днання відновлено');
        });
        
        window.addEventListener('offline', () => {
            offlineIndicator.classList.add('show');
            console.log('[⚠️] Втрачено з\'\u0454днання');
        });
        
        if (!navigator.onLine) {
            offlineIndicator.classList.add('show');
        }
    }
}

// Debug info
if (window.AppState) {
    console.log('📊 App State:', {
        userId: AppState.userId,
        isAdmin: AppState.isAdmin,
        currentTab: AppState.currentTab
    });
}