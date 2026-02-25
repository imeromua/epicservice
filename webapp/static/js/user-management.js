// EpicService - User Management Module
// Handles user approval, blocking, role assignment

let userMgmtFilter = 'pending';
let userMgmtSearchTimeout = null;

function setUserMgmtFilter(status) {
    userMgmtFilter = status;
    loadUserManagement();
}

function debouncedLoadUserManagement() {
    clearTimeout(userMgmtSearchTimeout);
    userMgmtSearchTimeout = setTimeout(() => loadUserManagement(), 400);
}

function _renderRoleSelect(u) {
    const roles = ['user', 'moderator', 'admin'];
    const options = roles.map(r => `<option value="${r}" ${u.role === r ? 'selected' : ''}>${r}</option>`).join('');
    return `<select style="padding:8px; border-radius:8px; border:2px solid var(--hint-color); background:var(--bg-color); color:var(--text-color);" onchange="changeUserRole(${u.id}, this.value)">${options}</select>`;
}

function _renderUserActions(u) {
    let buttons = '';
    if (u.status === 'pending') {
        buttons += `<button class="btn btn-success" style="flex:0 0 auto; padding:8px 12px; font-size:12px; min-width:auto;" onclick="approveUser(${u.id})">✅ Підтвердити</button>`;
        buttons += `<button class="btn btn-danger" style="flex:0 0 auto; padding:8px 12px; font-size:12px; min-width:auto;" onclick="blockUser(${u.id})">⛔️ Блок</button>`;
    } else if (u.status === 'active') {
        buttons += `<button class="btn btn-danger" style="flex:0 0 auto; padding:8px 12px; font-size:12px; min-width:auto;" onclick="blockUser(${u.id})">⛔️ Блок</button>`;
    } else if (u.status === 'blocked') {
        buttons += `<button class="btn btn-success" style="flex:0 0 auto; padding:8px 12px; font-size:12px; min-width:auto;" onclick="unblockUser(${u.id})">✅ Розблок</button>`;
    }

    return `<div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; justify-content:flex-end;">${_renderRoleSelect(u)}${buttons}</div>`;
}

async function loadUserManagement() {
    if (!isAdmin) return;
    const container = document.getElementById('userMgmtList');
    if (!container) return;

    const q = (document.getElementById('userMgmtSearch')?.value || '').trim();
    container.innerHTML = '<div class="loader">⏳ Завантаження...</div>';

    try {
        const url = `/api/admin/user-management/users?user_id=${userId}&status=${encodeURIComponent(userMgmtFilter)}&q=${encodeURIComponent(q)}&limit=50&offset=0`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (!data.users || data.users.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">👥</div>Немає користувачів</div>';
            return;
        }

        container.innerHTML = data.users.map(u => `
            <div class="user-item" style="cursor: default; align-items:flex-start; gap:12px;">
                <div class="user-info">
                    <div class="user-name">👤 ${u.display_name}</div>
                    <div class="user-details">🆔 ${u.id} • статус: ${u.status} • роль: ${u.role}</div>
                </div>
                ${_renderUserActions(u)}
            </div>
        `).join('');

    } catch (error) {
        console.error('❌ Error loading user management:', error);
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка завантаження</div>';
    }
}

async function approveUser(targetUserId) {
    if (!confirm(`Підтвердити доступ користувачу ${targetUserId}?`)) return;
    try {
        const response = await fetch('/api/admin/user-management/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, target_user_id: targetUserId })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
        tg.showAlert('✅ ' + (data.message || 'Готово'));
        loadUserManagement();
    } catch (e) {
        tg.showAlert('❌ ' + e.message);
    }
}

async function blockUser(targetUserId) {
    const reason = prompt('Причина блокування (необов\'язково):', '') || null;
    if (!confirm(`Заблокувати користувача ${targetUserId}?`)) return;
    try {
        const response = await fetch('/api/admin/user-management/block', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, target_user_id: targetUserId, reason: reason })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
        tg.showAlert('✅ ' + (data.message || 'Готово'));
        loadUserManagement();
    } catch (e) {
        tg.showAlert('❌ ' + e.message);
    }
}

async function unblockUser(targetUserId) {
    if (!confirm(`Розблокувати користувача ${targetUserId}?`)) return;
    try {
        const response = await fetch('/api/admin/user-management/unblock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, target_user_id: targetUserId })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
        tg.showAlert('✅ ' + (data.message || 'Готово'));
        loadUserManagement();
    } catch (e) {
        tg.showAlert('❌ ' + e.message);
    }
}

async function changeUserRole(targetUserId, role) {
    if (!confirm(`Змінити роль користувачу ${targetUserId} на ${role}?`)) return;
    try {
        const response = await fetch('/api/admin/user-management/role', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, target_user_id: targetUserId, role: role })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
        tg.showAlert('✅ ' + (data.message || 'Готово'));
        loadUserManagement();
    } catch (e) {
        tg.showAlert('❌ ' + e.message);
    }
}
