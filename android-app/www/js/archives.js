/**
 * archives.js - Archives tab for EpicService Android
 */
const EpicArchives = (function() {
    'use strict';

    const SERVER = window.APP_CONFIG ? window.APP_CONFIG.serverUrl : 'https://anubis-ua.pp.ua';

    async function load() {
        var el = document.getElementById('archives-content');
        if (!el) return;
        var user = App.getUser();
        if (!user) return;
        var token = App.getToken();
        el.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';

        try {
            var results = await Promise.all([
                EpicAPI.get('/api/archives/' + user.id, token),
                EpicAPI.get('/api/statistics/' + user.id, token).catch(function() { return null; })
            ]);
            var archivesData = results[0];
            var statsData = results[1];
            var archives = archivesData.archives || [];
            var html = '';

            if (statsData) {
                html += '<div class="stats-grid" style="margin-bottom:16px">' +
                    '<div class="stat-card"><div class="stat-value">' + (statsData.total_lists || 0) + '</div><div class="stat-label">Всього списків</div></div>' +
                    '<div class="stat-card"><div class="stat-value">' + (statsData.total_amount || 0).toLocaleString('uk-UA') + ' ₴</div><div class="stat-label">Загальна сума</div></div>' +
                    '<div class="stat-card"><div class="stat-value">' + (statsData.this_month_lists || 0) + '</div><div class="stat-label">Цього місяця</div></div>' +
                    (statsData.popular_department ? '<div class="stat-card"><div class="stat-value" style="font-size:14px">' + statsData.popular_department + '</div><div class="stat-label">Топ відділ</div></div>' : '') +
                    '</div>';
            }

            if (!archives.length) {
                html += '<div class="empty-state"><div class="empty-icon">📁</div><p>Архів порожній</p></div>';
            } else {
                html += archives.map(function(a) {
                    var fn = encodeURIComponent(a.filename || '');
                    return '<div class="archive-card">' +
                        '<div style="flex:1">' +
                        '<div class="archive-name">📄 ' + (a.filename || '') + '</div>' +
                        '<div class="archive-date">' + _formatDate(a.date) + '</div>' +
                        (a.type ? '<div style="font-size:11px;color:var(--text-muted)">' + a.type + (a.is_surplus ? ' · надлишки' : '') + '</div>' : '') +
                        '</div>' +
                        '<button class="action-btn" onclick="EpicArchives.download(\'' + fn + '\')">⬇️</button>' +
                        '</div>';
                }).join('');
            }

            el.innerHTML = html;

            var role = user.role || '';
            if (['admin', 'superadmin'].includes(role) && typeof EpicAdmin !== 'undefined') {
                var adminSection = document.createElement('div');
                adminSection.className = 'admin-section';
                adminSection.innerHTML = '<div class="admin-section-title">🗄 Адмін архіви</div>' +
                    '<button class="btn btn-secondary" onclick="EpicAdmin.showAdminArchives()">📁 Переглянути</button>';
                el.appendChild(adminSection);
            }
        } catch (e) {
            el.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><p>' + e.message + '</p></div>';
        }
    }

    function download(filename) {
        var token = App.getToken();
        window.open(SERVER + '/api/archive/download/' + filename + '?token=' + token, '_blank');
    }

    async function deleteArchive(filename) {
        if (!confirm('Видалити архів ' + filename + '?')) return;
        try {
            var user = App.getUser();
            var token = App.getToken();
            await EpicAPI.del('/api/archive/delete/' + encodeURIComponent(filename) + '?user_id=' + user.id, token);
            App.toast('Архів видалено', 'success');
            load();
        } catch (e) {
            App.toast(e.message || 'Помилка видалення', 'error');
        }
    }

    function downloadAll() {
        var user = App.getUser();
        var token = App.getToken();
        window.open(SERVER + '/api/archives/download-all/' + user.id + '?token=' + token, '_blank');
    }

    function _formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            return new Date(dateStr).toLocaleDateString('uk-UA', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
        } catch (e) { return dateStr; }
    }

    return { load, download, deleteArchive, downloadAll };
})();
