// EpicService - Admin Module
// Admin panel and management functions

// === ADMIN FUNCTIONS ===

async function loadAdminData() {
    if (!isAdmin) return;
    console.log('👑 Loading admin data...');
    await loadAdminStats();
    await loadAdminActiveUsers();
    // ✅ Завантажуємо модерацію фото
    if (typeof loadPhotoModeration === 'function') loadPhotoModeration();
    // ✅ Завантажуємо керування користувачами
    if (typeof loadUserManagement === 'function') loadUserManagement();
}

async function loadAdminStats() {
    const container = document.getElementById('adminStatsGrid');
    try {
        console.log('📊 Fetching admin statistics...');
        const response = await fetch(`/api/admin/statistics?user_id=${userId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data && data.success === false) throw new Error(data.message || data.error || 'Admin statistics error');
        console.log('📊 Stats data:', data);
        
        // Load products info for tile
        const productsResponse = await fetch(`/api/admin/products/info?user_id=${userId}`);
        const productsData = await productsResponse.json();
        cachedProductsInfo = productsData;
        
        const productsDisplay = productsData.success 
            ? `${productsData.current_articles} / ${productsData.original_articles}`
            : (data.total_products || 0);
        
        container.innerHTML = `
            <div class="admin-stat-card" style="cursor: pointer;" onclick="showAllUsers()">
                <div class="admin-stat-icon">👥</div>
                <div class="admin-stat-value">${data.total_users || 0}</div>
                <div class="admin-stat-label">Користувачів</div>
            </div>
            <div class="admin-stat-card success" style="cursor: pointer;" onclick="showActiveUsers()">
                <div class="admin-stat-icon">🔥</div>
                <div class="admin-stat-value">${data.active_users || 0}</div>
                <div class="admin-stat-label">Активних</div>
            </div>
            <div class="admin-stat-card warning" style="cursor: pointer;" onclick="showProductsInfo()">
                <div class="admin-stat-icon">📦</div>
                <div class="admin-stat-value">${productsDisplay}</div>
                <div class="admin-stat-label">Товарів</div>
            </div>
            <div class="admin-stat-card danger" style="cursor: pointer;" onclick="showReservedByDepartment()">
                <div class="admin-stat-icon">💰</div>
                <div class="admin-stat-value">${(data.total_reserved_sum || 0).toLocaleString('uk-UA')} ₴</div>
                <div class="admin-stat-label">Зарезервовано</div>
            </div>
        `;
    } catch (error) {
        console.error('❌ Error loading admin stats:', error);
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка завантаження</div>';
    }
}

// ... (rest of admin.js from 3.0.1 stays the same)
