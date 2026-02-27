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

// === MODERATOR IMPORT/EXPORT FUNCTIONS ===

let moderatorSelectedFile = null;

function handleModeratorFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    moderatorSelectedFile = file;
    const fileInfo = document.getElementById('moderatorFileInfo');
    fileInfo.textContent = `📄 ${file.name} (${(file.size / 1024).toFixed(0)} KB)`;
    fileInfo.style.display = 'block';
    document.getElementById('moderatorUploadBtn').disabled = false;
}

function cancelModeratorUpload() {
    moderatorSelectedFile = null;
    document.getElementById('moderatorFileInput').value = '';
    document.getElementById('moderatorFileInfo').style.display = 'none';
    document.getElementById('moderatorUploadBtn').disabled = true;
    document.getElementById('moderatorImportAlert').innerHTML = '';
}

function _resetModeratorFileSelection() {
    moderatorSelectedFile = null;
    document.getElementById('moderatorFileInput').value = '';
    document.getElementById('moderatorFileInfo').style.display = 'none';
    document.getElementById('moderatorUploadBtn').disabled = true;
}

async function uploadModeratorFile() {
    if (!moderatorSelectedFile) return;
    const notifyUsers = document.getElementById('moderatorNotifyUsers').checked;
    const alertEl = document.getElementById('moderatorImportAlert');
    alertEl.innerHTML = '<div class="loader">Завантаження...</div>';

    const formData = new FormData();
    formData.append('file', moderatorSelectedFile);

    try {
        const response = await fetch(`/api/admin/import?user_id=${userId}&notify_users=${notifyUsers}`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.success || data.added !== undefined) {
            alertEl.innerHTML = `<div style="color:var(--button-color);padding:8px 0">✅ Імпорт завершено! Додано: ${data.added || 0}, Оновлено: ${data.updated || 0}, Деактивовано: ${data.deactivated || 0}</div>`;
            _resetModeratorFileSelection();
        } else {
            alertEl.innerHTML = `<div style="color:#ff3b30;padding:8px 0">❌ ${data.error || 'Помилка імпорту'}</div>`;
        }
    } catch (error) {
        alertEl.innerHTML = `<div style="color:#ff3b30;padding:8px 0">❌ Помилка: ${error.message}</div>`;
        console.error('❌ uploadModeratorFile error:', error);
    }
}

function exportModeratorStock() {
    window.location.href = `/api/admin/export/stock?user_id=${userId}`;
}
