// EpicService - Archives Module
// Archive management and statistics

async function loadStatistics() {
    try {
        const r = await fetch(`/api/statistics/${userId}`);
        const d = await r.json();
        
        if (d.total_lists === 0) return '';
        
        return `<div class="stats-card">
            <div class="stats-title">📊 Ваша статистика</div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">${d.total_lists}</div>
                    <div class="stat-label">📝 Всього списків</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${d.total_amount.toLocaleString('uk-UA')} ₴</div>
                    <div class="stat-label">💰 Загальна сума</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${d.this_month_lists}</div>
                    <div class="stat-label">📅 За місяць</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${d.popular_department || '-'}</div>
                    <div class="stat-label">🏢 Популярний відділ</div>
                </div>
            </div>
        </div>`;
    } catch (e) {
        console.error('Stats error:', e);
        return '';
    }
}

async function loadArchiveStats(filename) { try { const r = await fetch(`/api/archive/stats/${filename}`); const d = await r.json(); if (d.success) { return `<div class="stat-row"><span class="stat-label">📦 Товарів:</span><span class="stat-value">${d.items_count}</span></div><div class="stat-row"><span class="stat-label">🏢 Відділ:</span><span class="stat-value">${d.department}</span></div>`; } return ''; } catch (e) { return ''; } }

async function loadArchives() { 
    const el = document.getElementById('archivesContent'); 
    const statsCard = document.getElementById('statisticsCard');
    
    el.innerHTML = '<div class="loader">📁 Завантаження...</div>'; 
    statsCard.innerHTML = '';
    
    try { 
        const stats = await loadStatistics();
        if (stats) statsCard.innerHTML = stats;
        
        const r = await fetch(`/api/archives/${userId}`); 
        const d = await r.json(); 
        
        if (!d.archives || d.archives.length === 0) { 
            el.innerHTML = '<div class="empty-state"><div class="empty-icon">📁</div>Архів порожній</div>'; 
            return; 
        }
        
        let html = `<button class="download-all-btn" onclick="downloadAllArchives()">📦 Завантажити всі архіви (${d.archives.length})</button>`;
        
        for (const a of d.archives) { 
            const stats = await loadArchiveStats(a.filename); 
            html += `<div class="archive-item"><div class="archive-header"><strong>📄 ${a.date}</strong><span class="archive-badge ${a.is_surplus ? 'surplus' : 'main'}">${a.type}</span></div>${stats ? `<div class="archive-stats">${stats}</div>` : ''}<div class="archive-actions"><button class="download-btn" onclick="downloadArchive('${a.filename}')">📥 Завантажити</button><button class="delete-archive-btn" onclick="deleteArchive('${a.filename}')">🗑️ Видалити</button></div></div>`; 
        } 
        el.innerHTML = html; 
    } catch (e) { 
        el.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка</div>'; 
    } 
}

function downloadAllArchives() {
    // Use fetch+blob download to include TMA auth header
    API.downloadFile(`/api/archives/download-all/${userId}`, `epicservice_archives_${userId}.zip`);
    tg.HapticFeedback.notificationOccurred('success');
}

function downloadArchive(f) {
    // Use fetch+blob download to include TMA auth header
    API.downloadFile(`/api/archive/download/${f}`, f);
    tg.HapticFeedback.notificationOccurred('success');
}

async function deleteArchive(filename) { if (!confirm(`Видалити файл "${filename}"?`)) return; try { const r = await fetch(`/api/archive/delete/${filename}`, { method: 'DELETE' }); const d = await r.json(); if (d.success) { tg.showAlert(`✅ ${d.message}`); tg.HapticFeedback.notificationOccurred('success'); loadArchives(); } else { tg.showAlert('❌ Помилка видалення'); } } catch (e) { tg.showAlert('❌ Помилка: ' + e.message); } }


