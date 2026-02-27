/**
 * user-management.js - User management for EpicService Android
 */
const EpicUserMgmt = (function() {
    'use strict';

    function _esc(str) {
        return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    var _currentFilter = 'pending';

    async function load() {
        var el = document.getElementById('user-mgmt-list');
        if (!el) return;
        el.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
        try {
            var user = App.getUser();
            var token = App.getToken();
            var searchEl = document.getElementById('user-mgmt-search');
            var search = searchEl ? searchEl.value.trim() : '';
            var url = '/api/admin/user-management/users?user_id=' + user.id + '&status=' + _currentFilter + '&q=' + encodeURIComponent(search) + '&limit=50&offset=0';
            var data = await EpicAPI.get(url, token);
            var users = data.users || [];
            if (!users.length) {
                el.innerHTML = '<div class="empty-state"><p>Немає користувачів</p></div>';
                return;
            }
            el.innerHTML = users.map(function(u) { return _userCardHtml(u); }).join('');
        } catch (e) {
            el.innerHTML = '<div class="empty-state"><p>' + e.message + '</p></div>';
        }
    }

    function _userCardHtml(u) {
        var statusColor = u.status === 'active' ? 'var(--success)' : u.status === 'blocked' ? 'var(--danger)' : 'var(--warning)';
        var statusMap = { active: '✅ Активний', blocked: '⛔ Заблокований', pending: '⏳ Очікує' };
        var statusText = statusMap[u.status] || u.status;
        var role = u.role || 'user';
        var validRoles = ['user', 'moderator', 'admin'];
        var safeRole = validRoles.indexOf(role) >= 0 ? role : 'user';
        return '<div class="product-card" style="margin-bottom:8px">' +
            '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">' +
            '<div><div style="font-weight:600;color:var(--text-primary)">' + _esc(u.display_name || u.id) + '</div>' +
            '<div style="font-size:12px;color:' + statusColor + '">' + _esc(statusText) + '</div>' +
            '<div style="font-size:12px;color:var(--text-muted)">Роль: ' + _esc(safeRole) + '</div></div>' +
            '</div>' +
            '<div style="display:flex;gap:6px;flex-wrap:wrap">' +
            (u.status === 'pending' ? '<button class="action-btn action-btn-primary" onclick="EpicUserMgmt.approve(' + Number(u.id) + ')">✅ Схвалити</button>' : '') +
            (u.status !== 'blocked' ? '<button class="action-btn" style="background:var(--danger);color:white" onclick="EpicUserMgmt.block(' + Number(u.id) + ')">⛔ Блокувати</button>' : '') +
            (u.status === 'blocked' ? '<button class="action-btn action-btn-primary" onclick="EpicUserMgmt.unblock(' + Number(u.id) + ')">🔓 Розблокувати</button>' : '') +
            '<select style="padding:6px 8px;background:var(--bg-primary);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);font-size:12px"' +
            ' onchange="EpicUserMgmt.changeRole(' + Number(u.id) + ', this.value, &#39;' + safeRole + '&#39;, this)">' +
            '<option value="user"' + (safeRole === 'user' ? ' selected' : '') + '>👤 User</option>' +
            '<option value="moderator"' + (safeRole === 'moderator' ? ' selected' : '') + '>🛡️ Moder</option>' +
            '<option value="admin"' + (safeRole === 'admin' ? ' selected' : '') + '>🔧 Admin</option>' +
            '</select>' +
            '</div></div>';
    }

    function setFilter(status) {
        _currentFilter = status;
        load();
    }

    var debouncedLoad = (function() {
        var t;
        return function() {
            clearTimeout(t);
            t = setTimeout(load, 400);
        };
    })();

    async function approve(targetUserId) {
        try {
            var user = App.getUser(); var token = App.getToken();
            var data = await EpicAPI.post('/api/admin/user-management/approve', { user_id: user.id, target_user_id: targetUserId }, token);
            App.toast(data.message || 'Схвалено', 'success');
            load();
        } catch (e) { App.toast(e.message || 'Помилка', 'error'); }
    }

    async function block(targetUserId) {
        var reason = prompt('Причина блокування (необов\'язково):') || '';
        try {
            var user = App.getUser(); var token = App.getToken();
            var data = await EpicAPI.post('/api/admin/user-management/block', { user_id: user.id, target_user_id: targetUserId, reason: reason }, token);
            App.toast(data.message || 'Заблоковано', 'success');
            load();
        } catch (e) { App.toast(e.message || 'Помилка', 'error'); }
    }

    async function unblock(targetUserId) {
        try {
            var user = App.getUser(); var token = App.getToken();
            var data = await EpicAPI.post('/api/admin/user-management/unblock', { user_id: user.id, target_user_id: targetUserId }, token);
            App.toast(data.message || 'Розблоковано', 'success');
            load();
        } catch (e) { App.toast(e.message || 'Помилка', 'error'); }
    }

    async function changeRole(targetUserId, role, originalRole, selectEl) {
        if (role === originalRole) return;
        if (!confirm('Змінити роль на ' + role + '?')) {
            if (selectEl) selectEl.value = originalRole;
            return;
        }
        try {
            var user = App.getUser(); var token = App.getToken();
            var data = await EpicAPI.post('/api/admin/user-management/role', { user_id: user.id, target_user_id: targetUserId, role: role }, token);
            App.toast(data.message || 'Роль змінено', 'success');
            load();
        } catch (e) {
            App.toast(e.message || 'Помилка', 'error');
            if (selectEl) selectEl.value = originalRole;
        }
    }

    return { load, debouncedLoad, setFilter, approve, block, unblock, changeRole };
})();
