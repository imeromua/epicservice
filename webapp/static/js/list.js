/* =============================================
   LIST.JS - Робота зі списком користувача
   Load, Save, Clear list
   ============================================= */

// Load user list
async function loadList() {
    const el = document.getElementById('listContent');
    el.innerHTML = '<div class="loader">⌛ Завантаження...</div>';
    
    try {
        const response = await fetch(`/api/list/${AppState.userId}`);
        const data = await response.json();
        
        if (!data.items || data.items.length === 0) {
            el.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div>Список порожній</div>';
            document.getElementById('totalBox').style.display = 'none';
            updateListBadge(0);
            updateDepartmentInfo(null, 0);
            return;
        }
        
        // Get department info
        const deptResponse = await fetch(`/api/list/department/${AppState.userId}`);
        const deptData = await deptResponse.json();
        updateDepartmentInfo(deptData.department, data.count);
        
        // Render list
        let html = '<div class="action-buttons">';
        html += '<button class="save-btn" onclick="saveList()">💾 Зберегти</button>';
        html += '<button class="clear-btn" onclick="clearList()">🗑️ Очистити</button>';
        html += '</div>';
        
        html += data.items.map(item => `
            <div class="list-item" onclick='openEditModal(${JSON.stringify(item)})'>
                <div class="list-header">
                    <strong>${item.article}</strong>
                    <span>${item.total.toFixed(2)} грн</span>
                </div>
                <div>${item.name}</div>
                <div style="margin-top:8px;color:var(--hint-color)">
                    ${item.quantity} шт. × ${item.price.toFixed(2)} грн
                </div>
            </div>
        `).join('');
        
        el.innerHTML = html;
        
        // Update total box
        document.getElementById('totalSum').textContent = data.total.toFixed(2);
        document.getElementById('totalItems').textContent = data.count;
        document.getElementById('totalBox').style.display = 'flex';
        updateListBadge(data.count);
        
    } catch (error) {
        el.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка завантаження</div>';
        updateListBadge(0);
        updateDepartmentInfo(null, 0);
        console.error('Load list error:', error);
    }
}

// Save list to archive
async function saveList() {
    try {
        const response = await fetch(`/api/save/${AppState.userId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (window.tg) window.tg.HapticFeedback.notificationOccurred('success');
            
            if (data.cleared) {
                loadList();
                updateDepartmentInfo(null, 0);
            }
            
            document.getElementById('successModal').classList.add('active');
        } else {
            if (window.tg) window.tg.showAlert('❌ ' + data.message);
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ ' + error.message);
        console.error('Save list error:', error);
    }
}

// Clear list
async function clearList() {
    if (!confirm('Очистити весь список?')) return;
    
    try {
        const response = await fetch(`/api/clear/${AppState.userId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (window.tg) window.tg.showAlert(`✅ ${data.message}`);
            updateDepartmentInfo(null, 0);
            loadList();
        } else {
            if (window.tg) window.tg.showAlert('❌ ' + data.message);
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ ' + error.message);
        console.error('Clear list error:', error);
    }
}

// Export functions
window.loadList = loadList;
window.saveList = saveList;
window.clearList = clearList;