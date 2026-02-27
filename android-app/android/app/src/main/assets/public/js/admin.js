/**
 * admin.js - Full admin panel for EpicService Android
 */
const EpicAdmin = (function() {
    'use strict';

    function _esc(str) {
        return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    const SERVER = window.APP_CONFIG ? window.APP_CONFIG.serverUrl : 'https://anubis-ua.pp.ua';
    let _selectedFile = null;

    function load() {
        loadStats();
        loadActiveUsers();
        if (typeof EpicPhotos !== 'undefined') EpicPhotos.loadModeration();
        if (typeof EpicUserMgmt !== 'undefined') EpicUserMgmt.load();
    }

    async function loadStats() {
        const grid = document.getElementById('admin-stats-grid');
        if (!grid) return;
        try {
            const user = App.getUser();
            const token = App.getToken();
            const [stats, info] = await Promise.all([
                EpicAPI.get('/api/admin/statistics?user_id=' + user.id, token),
                EpicAPI.get('/api/admin/products/info?user_id=' + user.id, token).catch(function() { return {}; })
            ]);
            grid.innerHTML =
                '<div class="stat-card" style="cursor:pointer" onclick="EpicAdmin.showAllUsers()">' +
                '<div class="stat-value">' + (stats.total_users || 0) + '</div>' +
                '<div class="stat-label">Користувачів</div></div>' +
                '<div class="stat-card" style="cursor:pointer" onclick="EpicAdmin.showActiveUsers()">' +
                '<div class="stat-value" style="color:var(--success)">' + (stats.active_users || 0) + '</div>' +
                '<div class="stat-label">Активних</div></div>' +
                '<div class="stat-card" style="cursor:pointer" onclick="EpicAdmin.showProductsInfo()">' +
                '<div class="stat-value">' + (stats.total_products || 0) + '</div>' +
                '<div class="stat-label">Товарів</div></div>' +
                '<div class="stat-card" style="cursor:pointer" onclick="EpicAdmin.showReservedByDepartment()">' +
                '<div class="stat-value" style="color:var(--warning)">' + (stats.pending_users || 0) + '</div>' +
                '<div class="stat-label">Очікують</div></div>' +
                (stats.total_reserved_sum ? '<div class="stat-card" style="grid-column:1/-1"><div class="stat-value" style="font-size:18px">' +
                    parseFloat(stats.total_reserved_sum).toLocaleString('uk-UA') + ' ₴</div><div class="stat-label">Загальний резерв</div></div>' : '');
        } catch (e) {
            if (grid) grid.innerHTML = '<div class="empty-state"><p>' + e.message + '</p></div>';
        }
    }

    async function loadActiveUsers() {
        const el = document.getElementById('admin-active-users');
        if (!el) return;
        try {
            const user = App.getUser();
            const token = App.getToken();
            const data = await EpicAPI.get('/api/admin/users/active?user_id=' + user.id, token);
            const users = data.users || [];
            if (!users.length) {
                el.innerHTML = '<div class="empty-state"><p>Немає активних списків</p></div>';
                return;
            }
            el.innerHTML = users.map(function(u) {
                return '<div class="product-card" style="display:flex;align-items:center;gap:12px;margin-bottom:8px">' +
                    '<div style="flex:1">' +
                    '<div style="font-weight:600;color:var(--text-primary)">' + (u.username || u.user_id) + '</div>' +
                    '<div style="font-size:12px;color:var(--text-muted)">' + (u.department || '') + ' · ' + (u.items_count || 0) + ' поз. · ' + (u.total_sum || 0).toLocaleString('uk-UA') + ' ₴</div>' +
                    '</div>' +
                    '<button class="action-btn action-btn-primary" onclick="EpicAdmin.forceSave(' + u.user_id + ')">💾</button>' +
                    '</div>';
            }).join('');
        } catch (e) {
            if (el) el.innerHTML = '<div class="empty-state"><p>' + e.message + '</p></div>';
        }
    }

    async function forceSave(targetUserId) {
        if (!confirm('Примусово зберегти список цього користувача?')) return;
        try {
            const user = App.getUser();
            const token = App.getToken();
            const data = await EpicAPI.post('/api/admin/force-save/' + targetUserId, { user_id: user.id }, token);
            App.toast(data.message || 'Збережено', 'success');
            loadActiveUsers();
        } catch (e) {
            App.toast(e.message || 'Помилка', 'error');
        }
    }

    async function showAllUsers() {
        const modal = document.getElementById('stats-modal');
        const content = document.getElementById('stats-modal-content');
        if (!modal || !content) return;
        content.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
        modal.style.display = 'flex';
        try {
            const user = App.getUser();
            const token = App.getToken();
            const data = await EpicAPI.get('/api/admin/users/all?user_id=' + user.id, token);
            const users = data.users || [];
            content.innerHTML = '<h3 style="font-size:16px;font-weight:700;margin-bottom:16px">👥 Всі користувачі (' + users.length + ')</h3>' +
                users.map(function(u) {
                    return '<div style="padding:10px 0;border-bottom:1px solid var(--border)">' +
                        '<div style="font-weight:600">' + (u.username || u.user_id) + '</div>' +
                        '<div style="font-size:12px;color:var(--text-muted)">Архівів: ' + (u.archives_count || 0) + ' · Сума: ' + (u.total_amount || 0).toLocaleString('uk-UA') + ' ₴</div>' +
                        (u.last_activity ? '<div style="font-size:11px;color:var(--text-muted)">Активність: ' + u.last_activity + '</div>' : '') +
                        '</div>';
                }).join('');
        } catch (e) {
            content.innerHTML = '<div class="empty-state"><p>' + e.message + '</p></div>';
        }
    }

    async function showActiveUsers() {
        const modal = document.getElementById('stats-modal');
        const content = document.getElementById('stats-modal-content');
        if (!modal || !content) return;
        content.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
        modal.style.display = 'flex';
        try {
            const user = App.getUser();
            const token = App.getToken();
            const data = await EpicAPI.get('/api/admin/users/active?user_id=' + user.id, token);
            const users = data.users || [];
            content.innerHTML = '<h3 style="font-size:16px;font-weight:700;margin-bottom:16px">🔥 Активні списки (' + users.length + ')</h3>' +
                users.map(function(u) {
                    return '<div style="padding:10px 0;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">' +
                        '<div><div style="font-weight:600">' + (u.username || u.user_id) + '</div>' +
                        '<div style="font-size:12px;color:var(--text-muted)">' + (u.department || '') + ' · ' + (u.items_count || 0) + ' поз. · ' + (u.total_sum || 0).toLocaleString('uk-UA') + ' ₴</div></div>' +
                        '<button class="action-btn action-btn-primary" onclick="EpicAdmin.forceSave(' + u.user_id + ')">💾 Зберегти</button>' +
                        '</div>';
                }).join('');
        } catch (e) {
            content.innerHTML = '<div class="empty-state"><p>' + e.message + '</p></div>';
        }
    }

    async function showProductsInfo() {
        const modal = document.getElementById('stats-modal');
        const content = document.getElementById('stats-modal-content');
        if (!modal || !content) return;
        content.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
        modal.style.display = 'flex';
        try {
            const user = App.getUser();
            const token = App.getToken();
            const data = await EpicAPI.get('/api/admin/products/info?user_id=' + user.id, token);
            content.innerHTML = '<h3 style="font-size:16px;font-weight:700;margin-bottom:16px">📦 Інформація про товари</h3>' +
                '<div class="stats-grid">' +
                '<div class="stat-card"><div class="stat-value">' + (data.original_articles || 0) + '</div><div class="stat-label">Оригінальних арт.</div></div>' +
                '<div class="stat-card"><div class="stat-value">' + (data.current_articles || 0) + '</div><div class="stat-label">Поточних арт.</div></div>' +
                '<div class="stat-card"><div class="stat-value">' + (data.original_sum || 0).toLocaleString('uk-UA') + ' ₴</div><div class="stat-label">Початкова сума</div></div>' +
                '<div class="stat-card"><div class="stat-value">' + (data.current_sum || 0).toLocaleString('uk-UA') + ' ₴</div><div class="stat-label">Поточна сума</div></div>' +
                '<div class="stat-card"><div class="stat-value">' + (data.collected_sum || 0).toLocaleString('uk-UA') + ' ₴</div><div class="stat-label">Зібрано сума</div></div>' +
                '<div class="stat-card"><div class="stat-value">' + (data.collected_articles || 0) + '</div><div class="stat-label">Зібрано арт.</div></div>' +
                '</div>' +
                (data.last_import ? '<div style="font-size:12px;color:var(--text-muted);margin-top:12px">Останній імпорт: ' + data.last_import + '</div>' : '') +
                (data.departments ? '<div style="margin-top:12px;font-size:13px;color:var(--text-secondary)">Відділи: ' + data.departments + '</div>' : '');
        } catch (e) {
            content.innerHTML = '<div class="empty-state"><p>' + e.message + '</p></div>';
        }
    }

    async function showReservedByDepartment() {
        const modal = document.getElementById('stats-modal');
        const content = document.getElementById('stats-modal-content');
        if (!modal || !content) return;
        content.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
        modal.style.display = 'flex';
        try {
            const user = App.getUser();
            const token = App.getToken();
            const data = await EpicAPI.get('/api/admin/reserved/by-department?user_id=' + user.id, token);
            const depts = data.departments || [];
            content.innerHTML = '<h3 style="font-size:16px;font-weight:700;margin-bottom:16px">🏢 Резерв по відділах</h3>' +
                depts.map(function(d) {
                    return '<div style="padding:10px 0;border-bottom:1px solid var(--border)">' +
                        '<div style="font-weight:600">Відділ ' + d.department + '</div>' +
                        '<div style="font-size:12px;color:var(--text-muted)">Сума: ' + (d.reserved_sum || 0).toLocaleString('uk-UA') + ' ₴ · Товарів: ' + (d.products_count || 0) + ' · Кор.: ' + (d.users_count || 0) + '</div>' +
                        '</div>';
                }).join('');
        } catch (e) {
            content.innerHTML = '<div class="empty-state"><p>' + e.message + '</p></div>';
        }
    }

    function closeStatsModal(event) {
        if (!event || event.target === document.getElementById('stats-modal')) {
            document.getElementById('stats-modal').style.display = 'none';
        }
    }

    async function showAdminArchives() {
        const modal = document.getElementById('admin-archives-modal');
        const content = document.getElementById('admin-archives-modal-content');
        if (!modal || !content) return;
        content.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
        modal.style.display = 'flex';
        try {
            const user = App.getUser();
            const token = App.getToken();
            const data = await EpicAPI.get('/api/admin/archives?user_id=' + user.id, token);
            const files = data.files || [];
            content.innerHTML =
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">' +
                '<h3 style="font-size:16px;font-weight:700">🗄 Архіви (' + files.length + ')</h3>' +
                '<button class="btn btn-secondary" onclick="EpicAdmin.downloadAllAdminArchives()" style="font-size:12px">⬇️ Всі</button>' +
                '</div>' +
                files.map(function(f) {
                    var fnEsc = _esc(f.filename);
                    var fnUrlEsc = encodeURIComponent(f.filename || '');
                    return '<div class="archive-card">' +
                        '<div><div class="archive-name">📄 ' + fnEsc + '</div>' +
                        '<div class="archive-date">' + _esc(f.modified) + (f.size ? ' · ' + Math.round(f.size / 1024) + ' KB' : '') + '</div></div>' +
                        '<button class="action-btn" onclick="EpicAdmin.downloadAdminArchive(&#39;' + fnEsc + '&#39;)">⬇️</button>' +
                        '</div>';
                }).join('');
        } catch (e) {
            content.innerHTML = '<div class="empty-state"><p>' + e.message + '</p></div>';
        }
    }

    function downloadAdminArchive(filename) {
        const user = App.getUser();
        window.open(SERVER + '/api/admin/archives/download/' + encodeURIComponent(filename) + '?user_id=' + user.id, '_blank');
    }

    function downloadAllAdminArchives() {
        const user = App.getUser();
        window.open(SERVER + '/api/admin/archives/download-all?user_id=' + user.id, '_blank');
    }

    function closeAdminArchivesModal(event) {
        if (!event || event.target === document.getElementById('admin-archives-modal')) {
            document.getElementById('admin-archives-modal').style.display = 'none';
        }
    }

    async function sendBroadcast() {
        const msgEl = document.getElementById('broadcast-message');
        const alertEl = document.getElementById('broadcast-alert');
        const msg = msgEl ? msgEl.value.trim() : '';
        if (!msg) { App.toast('Введіть текст повідомлення', 'error'); return; }
        try {
            const user = App.getUser();
            const token = App.getToken();
            const data = await EpicAPI.post('/api/admin/broadcast?user_id=' + user.id, { user_id: user.id, message: msg }, token);
            if (alertEl) alertEl.innerHTML = '<div style="color:var(--success);font-size:13px">✅ ' + (data.message || 'Відправлено') + ' (' + (data.sent || 0) + ' отримувачів)</div>';
            if (msgEl) msgEl.value = '';
        } catch (e) {
            if (alertEl) alertEl.innerHTML = '<div style="color:var(--danger);font-size:13px">❌ ' + e.message + '</div>';
        }
    }

    function handleFileSelect(event) {
        var file = event.target.files[0];
        if (!file) return;
        _selectedFile = file;
        var info = document.getElementById('import-file-info');
        var btn = document.getElementById('import-upload-btn');
        var zone = document.getElementById('import-drop-zone');
        if (info) { info.textContent = '📄 ' + file.name + ' (' + Math.round(file.size / 1024) + ' KB)'; info.style.display = 'block'; }
        if (zone) zone.textContent = '📄 ' + file.name;
        if (btn) btn.disabled = false;
    }

    async function uploadFile() {
        if (!_selectedFile) { App.toast('Оберіть файл', 'error'); return; }
        var alertEl = document.getElementById('import-alert');
        var notify = document.getElementById('import-notify-users') ? document.getElementById('import-notify-users').checked : false;
        var user = App.getUser();
        var token = App.getToken();
        var formData = new FormData();
        formData.append('file', _selectedFile);
        try {
            var resp = await fetch(SERVER + '/api/admin/import?user_id=' + user.id + '&notify_users=' + notify, {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
                body: formData
            });
            var data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || data.message || 'HTTP ' + resp.status);
            if (alertEl) alertEl.innerHTML = '<div style="color:var(--success);font-size:13px">✅ Додано: ' + (data.added || 0) + ', Оновлено: ' + (data.updated || 0) + ', Деактивовано: ' + (data.deactivated || 0) + '</div>';
            App.toast('Імпорт завершено', 'success');
            _selectedFile = null;
            var btn = document.getElementById('import-upload-btn');
            if (btn) btn.disabled = true;
        } catch (e) {
            if (alertEl) alertEl.innerHTML = '<div style="color:var(--danger);font-size:13px">❌ ' + e.message + '</div>';
            App.toast(e.message || 'Помилка імпорту', 'error');
        }
    }

    function exportStock() {
        var user = App.getUser();
        window.open(SERVER + '/api/admin/export/stock?user_id=' + user.id, '_blank');
    }

    async function clearDatabase() {
        if (!confirm('⚠️ Очистити базу даних? Ця дія незворотна!')) return;
        if (!confirm('Ви впевнені? Всі товари будуть видалені!')) return;
        try {
            var user = App.getUser(); var token = App.getToken();
            var data = await EpicAPI.post('/api/admin/danger/clear-database?user_id=' + user.id, {}, token);
            App.toast('Видалено ' + (data.deleted_count || 0) + ' записів', 'success');
        } catch (e) { App.toast(e.message || 'Помилка', 'error'); }
    }

    async function deleteAllPhotos() {
        if (!confirm('⚠️ Видалити всі фото?')) return;
        try {
            var user = App.getUser(); var token = App.getToken();
            var data = await EpicAPI.post('/api/admin/danger/delete-all-photos?user_id=' + user.id, {}, token);
            App.toast('Видалено ' + (data.deleted_count || 0) + ' фото', 'success');
        } catch (e) { App.toast(e.message || 'Помилка', 'error'); }
    }

    async function resetModeration() {
        if (!confirm('⚠️ Скинути всю модерацію?')) return;
        try {
            var user = App.getUser(); var token = App.getToken();
            var data = await EpicAPI.post('/api/admin/danger/reset-moderation?user_id=' + user.id, {}, token);
            App.toast('Скинуто ' + (data.reset_count || 0) + ' записів', 'success');
        } catch (e) { App.toast(e.message || 'Помилка', 'error'); }
    }

    async function deleteAllArchives() {
        if (!confirm('⚠️ Видалити всі архіви?')) return;
        try {
            var user = App.getUser(); var token = App.getToken();
            var data = await EpicAPI.post('/api/admin/danger/delete-all-archives?user_id=' + user.id, {}, token);
            App.toast('Видалено ' + (data.deleted_count || 0) + ' архівів', 'success');
        } catch (e) { App.toast(e.message || 'Помилка', 'error'); }
    }

    async function fullWipe() {
        if (!confirm('💥 ПОВНЕ ОЧИЩЕННЯ? Всі дані будуть знищені!')) return;
        if (!confirm('ОСТАТОЧНЕ ПІДТВЕРДЖЕННЯ: Дані відновити неможливо!')) return;
        try {
            var user = App.getUser(); var token = App.getToken();
            var data = await EpicAPI.post('/api/admin/danger/full-wipe?user_id=' + user.id, {}, token);
            App.toast('Видалено: ' + (data.deleted_products || 0) + ' тов., ' + (data.deleted_photos || 0) + ' фото, ' + (data.deleted_archives || 0) + ' арх.', 'success');
        } catch (e) { App.toast(e.message || 'Помилка', 'error'); }
    }

    return {
        load, loadStats, loadActiveUsers, forceSave,
        showAllUsers, showActiveUsers, showProductsInfo, showReservedByDepartment,
        closeStatsModal,
        showAdminArchives, downloadAdminArchive, downloadAllAdminArchives, closeAdminArchivesModal,
        sendBroadcast, handleFileSelect, uploadFile, exportStock,
        clearDatabase, deleteAllPhotos, resetModeration, deleteAllArchives, fullWipe,
    };
})();
