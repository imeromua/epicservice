/* =============================================
   ARCHIVES.JS - Архіви та статистика
   ============================================= */

// Load user statistics
async function loadStatistics() {
    try {
        const response = await fetch(`/api/statistics/${AppState.userId}`);
        const data = await response.json();
        
        if (data.total_lists === 0) return '';
        
        return `<div class="stats-card">
            <div class="stats-title">📊 Ваша статистика</div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${data.total_lists}</div>
                    <div class="stat-label">📝 Всього списків</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${data.total_amount.toLocaleString('uk-UA')} ₴</div>
                    <div class="stat-label">💰 Загальна сума</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${data.this_month_lists}</div>
                    <div class="stat-label">📅 За місяць</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${data.popular_department || '-'}</div>
                    <div class="stat-label">🏮 Популярний відділ</div>
                </div>
            </div>
        </div>`;
    } catch (error) {
        console.error('Stats error:', error);
        return '';
    }
}

// Load archive stats
async function loadArchiveStats(filename) {
    try {
        const response = await fetch(`/api/archive/stats/${filename}?user_id=${AppState.userId}`);
        const data = await response.json();
        
        if (data.success) {
            return `
                <div class="stat-row">
                    <span class="stat-label">📦 Товарів:</span>
                    <span class="stat-value">${data.items_count}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">🏮 Відділ:</span>
                    <span class="stat-value">${data.department}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">👤 Автор:</span>
                    <span class="stat-value">ID ${data.author_id}</span>
                </div>
            `;
        }
        return '';
    } catch (error) {
        return '';
    }
}

// Load archives
async function loadArchives() {
    const el = document.getElementById('archivesContent');
    const statsCard = document.getElementById('statisticsCard');
    
    el.innerHTML = '<div class="loader">📁 Завантаження...</div>';
    statsCard.innerHTML = '';
    
    try {
        // Load user statistics
        const stats = await loadStatistics();
        if (stats) statsCard.innerHTML = stats;
        
        // Load archives list
        const response = await fetch(`/api/archives/${AppState.userId}`);
        const data = await response.json();
        
        if (!data.archives || data.archives.length === 0) {
            el.innerHTML = '<div class="empty-state"><div class="empty-icon">📁</div>Архів порожній</div>';
            return;
        }
        
        let html = `<button class="download-all-btn" onclick="downloadAllArchives()">
            📦 Завантажити всі архіви (${data.archives.length})
        </button>`;
        
        for (const archive of data.archives) {
            const stats = await loadArchiveStats(archive.filename);
            html += `
                <div class="archive-item">
                    <div class="archive-header">
                        <strong>📄 ${archive.date}</strong>
                        <span class="archive-badge ${archive.is_surplus ? 'surplus' : 'main'}">
                            ${archive.type}
                        </span>
                    </div>
                    ${stats ? `<div class="archive-stats">${stats}</div>` : ''}
                    <div class="archive-actions">
                        <button class="download-btn" onclick="downloadArchive('${archive.filename}')">
                            📥 Завантажити
                        </button>
                        <button class="delete-archive-btn" onclick="deleteArchive('${archive.filename}')">
                            🗑️ Видалити
                        </button>
                    </div>
                </div>
            `;
        }
        
        el.innerHTML = html;
        
    } catch (error) {
        el.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка</div>';
        console.error('Load archives error:', error);
    }
}

// Download single archive
function downloadArchive(filename) {
    window.open(`/api/archive/download/${filename}`, '_blank');
    if (window.tg) window.tg.HapticFeedback.notificationOccurred('success');
}

// Download all archives
function downloadAllArchives() {
    window.open(`/api/archives/download-all/${AppState.userId}`, '_blank');
    if (window.tg) window.tg.HapticFeedback.notificationOccurred('success');
}

// Delete archive
async function deleteArchive(filename) {
    if (!confirm(`Видалити файл "${filename}"?`)) return;
    
    try {
        const response = await fetch(
            `/api/archive/delete/${filename}?user_id=${AppState.userId}`,
            { method: 'DELETE' }
        );
        
        const data = await response.json();
        
        if (data.success) {
            if (window.tg) {
                window.tg.showAlert(`✅ ${data.message}`);
                window.tg.HapticFeedback.notificationOccurred('success');
            }
            loadArchives();
        } else {
            if (window.tg) window.tg.showAlert('❌ Помилка видалення');
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ Помилка: ' + error.message);
        console.error('Delete archive error:', error);
    }
}

// Export functions
window.loadStatistics = loadStatistics;
window.loadArchiveStats = loadArchiveStats;
window.loadArchives = loadArchives;
window.downloadArchive = downloadArchive;
window.downloadAllArchives = downloadAllArchives;
window.deleteArchive = deleteArchive;