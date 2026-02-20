/* =============================================
   ADMIN.JS - Адмін-панель
   Statistics, Users, Import, Broadcast, Archives
   ============================================= */

// Load all admin data
async function loadAdminData() {
    if (!AppState.isAdmin) return;
    console.log('👑 Loading admin data...');
    await loadAdminStats();
    await loadAdminActiveUsers();
}

// Load admin statistics
async function loadAdminStats() {
    const container = document.getElementById('adminStatsGrid');
    try {
        console.log('📊 Fetching admin statistics...');
        const response = await fetch(`/api/admin/statistics?user_id=${AppState.userId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data && data.success === false) throw new Error(data.message || data.error || 'Admin statistics error');
        console.log('📊 Stats data:', data);
        
        // Load products info for tile
        const productsResponse = await fetch(`/api/admin/products/info?user_id=${AppState.userId}`);
        const productsData = await productsResponse.json();
        AppState.cachedProductsInfo = productsData;
        
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

// Load active users
async function loadAdminActiveUsers() {
    try {
        console.log('👥 Fetching active users...');
        const response = await fetch(`/api/admin/users/active?user_id=${AppState.userId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data && data.success === false) throw new Error(data.message || data.error || 'Active users error');
        console.log('👥 Active users data:', data);
        
        const container = document.getElementById('adminActiveUsers');
        
        if (!data.users || data.users.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">👥</div>Немає активних списків</div>';
            return;
        }
        
        container.innerHTML = data.users.map(user => `
            <div class="user-item">
                <div class="user-info">
                    <div class="user-name">👤 ${user.username || 'User ' + user.user_id}</div>
                    <div class="user-details">
                        🏢 ${user.department || '-'} • 📦 ${user.items_count} • 💰 ${(user.total_sum || 0).toLocaleString('uk-UA')} ₴
                    </div>
                </div>
                <button class="btn btn-success" style="flex: 0 0 auto; padding: 8px 16px; font-size: 12px;" onclick="forceSave(${user.user_id})">
                    💾 Зберегти
                </button>
            </div>
        `).join('');
    } catch (error) {
        console.error('❌ Error loading active users:', error);
        document.getElementById('adminActiveUsers').innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка завантаження</div>';
    }
}

// Force save user list
async function forceSave(targetUserId) {
    if (!confirm(`Примусово зберегти список користувача ${targetUserId}?`)) return;
    
    try {
        const response = await fetch(`/api/admin/force-save/${targetUserId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: AppState.userId })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        
        if (data.success) {
            if (window.tg) window.tg.showAlert('✅ ' + data.message);
            loadAdminActiveUsers();
        } else {
            if (window.tg) window.tg.showAlert('❌ ' + (data.message || 'Помилка збереження'));
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ Помилка: ' + error.message);
    }
}

// === FILE UPLOAD ===

function initFileUpload() {
    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return;
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--button-color)';
        dropZone.style.background = 'rgba(0,136,204,0.1)';
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--hint-color)';
        dropZone.style.background = '';
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--hint-color)';
        dropZone.style.background = '';
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            AppState.selectedFile = files[0];
            updateFileInfo();
        }
    });
}

function handleFileSelect(event) {
    AppState.selectedFile = event.target.files[0];
    updateFileInfo();
}

function updateFileInfo() {
    if (AppState.selectedFile) {
        document.getElementById('fileInfo').textContent = `📄 ${AppState.selectedFile.name} (${(AppState.selectedFile.size / 1024).toFixed(2)} KB)`;
        document.getElementById('fileInfo').style.display = 'block';
        document.getElementById('uploadBtn').disabled = false;
    }
}

function cancelUpload(clearAlert = false) {
    AppState.selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('uploadBtn').disabled = true;
    if (clearAlert) {
        document.getElementById('importAlert').innerHTML = '';
    }
}

async function uploadFile() {
    if (!AppState.selectedFile) {
        if (window.tg) window.tg.showAlert('❌ Оберіть файл для завантаження');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', AppState.selectedFile);
    const notifyChecked = document.getElementById('notifyUsers').checked;
    
    document.getElementById('uploadBtn').disabled = true;
    document.getElementById('uploadBtn').textContent = '⌛ Завантаження...';
    
    try {
        const response = await fetch(`/api/admin/import?user_id=${AppState.userId}&notify_users=${notifyChecked}`, {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        
        if (data.success || data.added !== undefined) {
            document.getElementById('importAlert').innerHTML = `
                <div class="alert alert-success">
                    <span style="font-size: 20px;">✅</span>
                    <div>Імпорт успішний<br><small>Додано: ${data.added || 0}, Оновлено: ${data.updated || 0}, Деактивовано: ${data.deactivated || 0}</small></div>
                </div>
            `;
            AppState.selectedFile = null;
            document.getElementById('fileInput').value = '';
            document.getElementById('fileInfo').style.display = 'none';
            document.getElementById('uploadBtn').disabled = true;
            loadAdminStats();
        } else {
            document.getElementById('importAlert').innerHTML = `
                <div class="alert alert-error">
                    <span style="font-size: 20px;">❌</span>
                    <div>${data.error || data.message || 'Помилка імпорту'}</div>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('importAlert').innerHTML = `
            <div class="alert alert-error">
                <span style="font-size: 20px;">❌</span>
                <div>Помилка: ${error.message}</div>
            </div>
        `;
    } finally {
        document.getElementById('uploadBtn').disabled = false;
        document.getElementById('uploadBtn').textContent = '📤 Імпортувати';
    }
}

// Export stock
async function exportStock() {
    try {
        window.open(`/api/admin/export/stock?user_id=${AppState.userId}`, '_blank');
        if (window.tg) window.tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ Помилка експорту: ' + error.message);
    }
}

// === ADMIN ARCHIVES ===

async function showAdminArchives() {
    try {
        const response = await fetch(`/api/admin/archives?user_id=${AppState.userId}`);
        const data = await response.json();
        
        if (data.success && data.files && data.files.length > 0) {
            let html = '<h2 style="margin-bottom: 16px;">🗄 Архіви користувачів</h2>';
            html += '<button class="btn btn-primary" style="width: 100%; margin-bottom: 16px;" onclick="downloadAllAdminArchives(); closeAdminArchivesModal();">📥 Завантажити всі (ZIP)</button>';
            html += '<div style="max-height: 400px; overflow-y: auto;">';
            data.files.forEach(file => {
                html += `<div style="background: var(--secondary-bg-color); padding: 12px; margin-bottom: 8px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">`;
                html += `<div><div style="font-weight: 600;">📄 ${file.filename}</div><div style="font-size: 12px; color: var(--hint-color);">${(file.size / 1024).toFixed(1)} KB | ${file.modified}</div></div>`;
                html += `<button class="btn btn-primary" style="padding: 6px 12px; font-size: 12px; min-width: auto;" onclick="downloadAdminArchive('${file.filename}')">📥</button></div>`;
            });
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeAdminArchivesModal()">Закрити</button>';
            
            document.getElementById('adminArchivesModalContent').innerHTML = html;
            document.getElementById('adminArchivesModal').classList.add('active');
        } else {
            if (window.tg) window.tg.showAlert('📁 Немає архівів');
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ Помилка: ' + error.message);
    }
}

function closeAdminArchivesModal() {
    document.getElementById('adminArchivesModal').classList.remove('active');
}

function downloadAdminArchive(filename) {
    window.open(`/api/admin/archives/download/${filename}?user_id=${AppState.userId}`, '_blank');
    if (window.tg) window.tg.HapticFeedback.notificationOccurred('success');
}

function downloadAllAdminArchives() {
    window.open(`/api/admin/archives/download-all?user_id=${AppState.userId}`, '_blank');
    if (window.tg) window.tg.HapticFeedback.notificationOccurred('success');
}

// === MODAL STATS ===

async function showAllUsers() {
    try {
        const response = await fetch(`/api/admin/users/all?user_id=${AppState.userId}`);
        const data = await response.json();
        
        if (data.success && data.users && data.users.length > 0) {
            let html = '<h2 style="margin-bottom: 16px;">👥 Всі користувачі</h2>';
            html += '<div style="max-height: 450px; overflow-y: auto;">';
            data.users.forEach(user => {
                html += `<div style="background: var(--secondary-bg-color); padding: 12px; margin-bottom: 8px; border-radius: 8px;">`;
                html += `<div style="font-weight: 600;">👤 ID: ${user.user_id}${user.username ? ' (@' + user.username + ')' : ''}</div>`;
                html += `<div style="font-size: 12px; color: var(--hint-color); margin-top: 4px;">`;
                html += `📁 Архівів: ${user.archives_count || 0} | 💰 Сума: ${(user.total_amount || 0).toLocaleString('uk-UA')} ₴`;
                if (user.last_activity) html += ` | 🕐 ${user.last_activity}`;
                html += `</div></div>`;
            });
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeStatsModal()">Закрити</button>';
            
            document.getElementById('statsModalContent').innerHTML = html;
            document.getElementById('statsModal').classList.add('active');
        } else {
            if (window.tg) window.tg.showAlert('📁 Немає користувачів');
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ Помилка: ' + error.message);
    }
}

async function showActiveUsers() {
    try {
        const response = await fetch(`/api/admin/users/active?user_id=${AppState.userId}`);
        const data = await response.json();
        
        if (data.success && data.users && data.users.length > 0) {
            let html = '<h2 style="margin-bottom: 16px;">🔥 Активні користувачі</h2>';
            html += '<div style="max-height: 450px; overflow-y: auto;">';
            data.users.forEach(user => {
                html += `<div style="background: var(--secondary-bg-color); padding: 12px; margin-bottom: 8px; border-radius: 8px;">`;
                html += `<div style="font-weight: 600;">👤 ${user.username || 'User ' + user.user_id}</div>`;
                html += `<div style="font-size: 12px; color: var(--hint-color); margin-top: 4px;">`;
                html += `🏢 ${user.department || '-'} | 📦 ${user.items_count} товарів | 💰 ${(user.total_sum || 0).toLocaleString('uk-UA')} ₴`;
                html += `</div></div>`;
            });
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeStatsModal()">Закрити</button>';
            
            document.getElementById('statsModalContent').innerHTML = html;
            document.getElementById('statsModal').classList.add('active');
        } else {
            if (window.tg) window.tg.showAlert('📁 Немає активних користувачів');
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ Помилка: ' + error.message);
    }
}

async function showProductsInfo() {
    try {
        let data = AppState.cachedProductsInfo;
        if (!data) {
            const response = await fetch(`/api/admin/products/info?user_id=${AppState.userId}`);
            data = await response.json();
            AppState.cachedProductsInfo = data;
        }
        
        if (data.success) {
            let html = '<h2 style="margin-bottom: 8px;">📦 Інформація про товари</h2>';
            if (data.last_import) {
                html += `<div style="padding: 10px; background: rgba(52,199,89,0.1); border-radius: 8px; margin-bottom: 12px; font-size: 13px;">`;
                html += `✅ Базу оновлено ${data.last_import}`;
                html += `</div>`;
            }
            
            // Було/Стало summary
            html += `<div style="padding: 14px; background: linear-gradient(135deg, rgba(255,152,0,0.15) 0%, rgba(255,204,0,0.15) 100%); border-radius: 10px; margin-bottom: 14px;">`;
            html += `<div style="text-align: center; font-size: 15px; font-weight: 600; margin-bottom: 10px;">📊 Було / Стало</div>`;
            html += `<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; text-align: center;">`;
            html += `<div><div style="font-size: 22px; font-weight: 700; color: #ff9500;">${data.original_articles || 0}</div><div style="font-size: 11px; opacity: 0.7;">Було артикулів</div></div>`;
            html += `<div><div style="font-size: 22px; font-weight: 700; color: #34c759;">→</div><div style="font-size: 11px; opacity: 0.7;">Зібрано</div></div>`;
            html += `<div><div style="font-size: 22px; font-weight: 700; color: #0088cc;">${data.current_articles || 0}</div><div style="font-size: 11px; opacity: 0.7;">Залишилось</div></div>`;
            html += `</div></div>`;
            
            // Детальна статистика
            html += `<div style="padding: 12px; background: var(--secondary-bg-color); border-radius: 8px; margin-bottom: 12px;">`;
            html += `<div style="font-weight: 600; margin-bottom: 8px;">💰 Суми:</div>`;
            html += `<div style="font-size: 13px; line-height: 1.6;">`;
            html += `📌 Було: <strong>${(data.original_sum || 0).toLocaleString('uk-UA')} грн</strong><br>`;
            html += `🛒 Зібрано: <strong style="color: #ff9500;">${(data.collected_sum || 0).toLocaleString('uk-UA')} грн</strong> (${data.collected_articles || 0} арт.)<br>`;
            html += `✅ Залишилось: <strong style="color: #34c759;">${(data.current_sum || 0).toLocaleString('uk-UA')} грн</strong>`;
            html += `</div></div>`;
            
            html += '<div style="font-weight: 600; margin-bottom: 8px;">📦 По відділах (було → стало):</div>';
            html += '<div style="max-height: 300px; overflow-y: auto;">';
            if (data.departments && data.departments.length > 0) {
                data.departments.forEach(dept => {
                    const wasCollected = (dept.original_count || 0) - (dept.current_count || 0);
                    const collectedPercent = dept.original_count > 0 ? Math.round((wasCollected / dept.original_count) * 100) : 0;
                    html += `<div style="padding: 10px 12px; background: var(--secondary-bg-color); margin-bottom: 6px; border-radius: 6px;">`;
                    html += `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">`;
                    html += `<span style="font-weight: 600;">🏢 Відділ ${dept.department}</span>`;
                    html += `<span style="font-weight: 600; color: var(--button-color);">${dept.original_count || 0} → ${dept.current_count || 0}</span>`;
                    html += `</div>`;
                    if (wasCollected > 0) {
                        html += `<div style="font-size: 12px; color: var(--hint-color);">`;
                        html += `🛒 Зібрано: ${wasCollected} арт. (${collectedPercent}%)`;
                        html += `</div>`;
                    }
                    html += `</div>`;
                });
            }
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeStatsModal()">Закрити</button>';
            
            document.getElementById('statsModalContent').innerHTML = html;
            document.getElementById('statsModal').classList.add('active');
        } else {
            if (window.tg) window.tg.showAlert('📁 Немає даних');
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ Помилка: ' + error.message);
    }
}

async function showReservedByDepartment() {
    try {
        const response = await fetch(`/api/admin/reserved/by-department?user_id=${AppState.userId}`);
        const data = await response.json();
        
        if (data.success && data.departments && data.departments.length > 0) {
            let html = '<h2 style="margin-bottom: 16px;">💰 Резерви по відділах</h2>';
            html += '<div style="max-height: 450px; overflow-y: auto;">';
            const total = data.departments.reduce((sum, d) => sum + (d.reserved_sum || 0), 0);
            data.departments.forEach(dept => {
                const percent = total > 0 ? ((dept.reserved_sum / total) * 100).toFixed(1) : 0;
                html += `<div style="background: var(--secondary-bg-color); padding: 12px; margin-bottom: 8px; border-radius: 8px;">`;
                html += `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">`;
                html += `<div style="font-weight: 600;">🏢 Відділ ${dept.department}</div>`;
                html += `<div style="font-weight: 600; color: var(--button-color);">${(dept.reserved_sum || 0).toLocaleString('uk-UA')} ₴</div>`;
                html += `</div>`;
                html += `<div style="background: var(--hint-color); height: 6px; border-radius: 3px; overflow: hidden;">`;
                html += `<div style="background: var(--button-color); width: ${percent}%; height: 100%;"></div>`;
                html += `</div>`;
                html += `<div style="font-size: 12px; color: var(--hint-color); margin-top: 4px;">`;
                html += `📦 ${dept.products_count || 0} товарів | 👥 ${dept.users_count || 0} користувачів | ${percent}%`;
                html += `</div></div>`;
            });
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeStatsModal()">Закрити</button>';
            
            document.getElementById('statsModalContent').innerHTML = html;
            document.getElementById('statsModal').classList.add('active');
        } else {
            if (window.tg) window.tg.showAlert('📁 Немає резервів');
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ Помилка: ' + error.message);
    }
}

function closeStatsModal() {
    document.getElementById('statsModal').classList.remove('active');
}

// === BROADCAST ===

async function sendBroadcast() {
    const message = document.getElementById('broadcastMessage').value.trim();
    
    if (!message) {
        if (window.tg) window.tg.showAlert('❌ Введіть текст повідомлення');
        return;
    }
    
    if (!confirm(`Розіслати повідомлення всім користувачам?\n\nТекст: "${message}"`)) return;
    
    try {
        const response = await fetch(`/api/admin/broadcast?user_id=${AppState.userId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: AppState.userId,
                message: message
            })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('broadcastAlert').innerHTML = `
                <div class="alert alert-success">
                    <span style="font-size: 20px;">✅</span>
                    <div>${data.message || 'Розсилка завершена'}<br><small>Розіслано: ${data.sent || 0} користувачам</small></div>
                </div>
            `;
            document.getElementById('broadcastMessage').value = '';
        } else {
            document.getElementById('broadcastAlert').innerHTML = `
                <div class="alert alert-error">
                    <span style="font-size: 20px;">❌</span>
                    <div>${data.message || 'Помилка розсилки'}</div>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('broadcastAlert').innerHTML = `
            <div class="alert alert-error">
                <span style="font-size: 20px;">❌</span>
                <div>Помилка: ${error.message}</div>
            </div>
        `;
    }
}

// Export functions
window.loadAdminData = loadAdminData;
window.loadAdminStats = loadAdminStats;
window.loadAdminActiveUsers = loadAdminActiveUsers;
window.forceSave = forceSave;
window.initFileUpload = initFileUpload;
window.handleFileSelect = handleFileSelect;
window.updateFileInfo = updateFileInfo;
window.cancelUpload = cancelUpload;
window.uploadFile = uploadFile;
window.exportStock = exportStock;
window.showAdminArchives = showAdminArchives;
window.closeAdminArchivesModal = closeAdminArchivesModal;
window.downloadAdminArchive = downloadAdminArchive;
window.downloadAllAdminArchives = downloadAllAdminArchives;
window.showAllUsers = showAllUsers;
window.showActiveUsers = showActiveUsers;
window.showProductsInfo = showProductsInfo;
window.showReservedByDepartment = showReservedByDepartment;
window.closeStatsModal = closeStatsModal;
window.sendBroadcast = sendBroadcast;