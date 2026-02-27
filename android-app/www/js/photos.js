/**
 * photos.js - Photo moderation for EpicService Android
 */
const EpicPhotos = (function() {
    'use strict';

    function _esc(str) {
        return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    const SERVER = window.APP_CONFIG ? window.APP_CONFIG.serverUrl : 'https://anubis-ua.pp.ua';
    let _currentPhotoId = null;

    async function loadModeration() {
        var container = document.getElementById('photo-moderation-container');
        var adminContainer = document.getElementById('admin-photo-moderation');
        var target = container || adminContainer;
        if (!target) return;

        try {
            var user = App.getUser();
            var token = App.getToken();
            var data = await EpicAPI.get('/api/photos/moderation/pending?user_id=' + user.id, token);
            var photos = data.photos || [];

            if (!photos.length) {
                var empty = '<div class="empty-state"><div class="empty-icon">✅</div><p>Немає фото для модерації</p></div>';
                if (container) container.innerHTML = empty;
                if (adminContainer) adminContainer.innerHTML = empty;
                return;
            }

            var html = photos.map(function(p) {
                var src = '';
                if (p.file_path) {
                    src = SERVER + (p.file_path.startsWith('/') ? '' : '/') + p.file_path;
                }
                var articleEsc = _esc(p.article);
                var nameEsc = _esc(p.product_name);
                var byEsc = _esc(p.uploaded_by);
                var atEsc = _esc(p.uploaded_at);
                return '<div class="product-card" style="margin-bottom:12px">' +
                    '<img src="' + _esc(src) + '" style="width:100%;max-height:200px;object-fit:cover;border-radius:8px;margin-bottom:8px;cursor:pointer"' +
                    ' onclick="EpicPhotos.openModerationPopup(' + p.id + ', &#39;' + _esc(src) + '&#39;, &#39;' + articleEsc + '&#39;, &#39;' + nameEsc + '&#39;, &#39;' + byEsc + '&#39;, &#39;' + atEsc + '&#39;, ' + (p.file_size || 0) + ')">' +
                    '<div style="font-size:14px;font-weight:600;color:var(--text-primary)">' + articleEsc + '</div>' +
                    '<div style="font-size:13px;color:var(--text-secondary);margin-bottom:4px">' + nameEsc + '</div>' +
                    '<div style="font-size:12px;color:var(--text-muted)">👤 ' + byEsc + ' · ' + atEsc + '</div>' +
                    '<div style="display:flex;gap:8px;margin-top:10px">' +
                    '<button class="btn btn-success" style="flex:1" onclick="EpicPhotos.moderatePhoto(' + p.id + ', \'approved\')">✅ Схвалити</button>' +
                    '<button class="btn btn-danger" style="flex:1" onclick="EpicPhotos.moderatePhoto(' + p.id + ', \'rejected\')">❌ Відхилити</button>' +
                    '</div></div>';
            }).join('');

            if (container) container.innerHTML = html;
            if (adminContainer) adminContainer.innerHTML = html;
        } catch (e) {
            var errHtml = '<div class="empty-state"><div class="empty-icon">❌</div><p>' + e.message + '</p></div>';
            if (container) container.innerHTML = errHtml;
            if (adminContainer) adminContainer.innerHTML = errHtml;
        }
    }

    async function moderatePhoto(photoId, status) {
        var reason = '';
        if (status === 'rejected') {
            reason = prompt('Причина відхилення (необов\'язково):') || '';
        }
        try {
            var user = App.getUser();
            var token = App.getToken();
            var formData = new FormData();
            formData.append('status', status);
            formData.append('user_id', user.id);
            if (reason) formData.append('reason', reason);

            var resp = await fetch(SERVER + '/api/photos/moderation/' + photoId, {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
                body: formData
            });
            var data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || data.message || 'HTTP ' + resp.status);
            App.toast(status === 'approved' ? '✅ Фото схвалено' : '❌ Фото відхилено', status === 'approved' ? 'success' : 'info');
            closeModerationPopup();
            loadModeration();
        } catch (e) {
            App.toast(e.message || 'Помилка', 'error');
        }
    }

    function openModerationPopup(photoId, src, article, name, uploadedBy, uploadedAt, fileSize) {
        _currentPhotoId = photoId;
        var popup = document.getElementById('moderation-popup');
        if (!popup) {
            popup = document.createElement('div');
            popup.id = 'moderation-popup';
            popup.className = 'modal-overlay';
            popup.style.display = 'flex';
            popup.innerHTML =
                '<div class="modal-sheet"><div class="modal-handle"></div>' +
                '<div id="moderation-popup-content"></div></div>';
            popup.addEventListener('click', function(e) { if (e.target === popup) closeModerationPopup(); });
            document.body.appendChild(popup);
        } else {
            popup.style.display = 'flex';
        }
        var content = document.getElementById('moderation-popup-content');
        var fileSizeKb = fileSize ? Math.round(fileSize / 1024) + ' KB' : '';
        content.innerHTML =
            '<img src="' + _esc(src) + '" style="width:100%;max-height:300px;object-fit:contain;border-radius:8px;margin-bottom:12px">' +
            '<div style="font-size:14px;font-weight:700;color:var(--text-primary);margin-bottom:4px">' + _esc(article) + ' — ' + _esc(name) + '</div>' +
            '<div style="font-size:12px;color:var(--text-muted);margin-bottom:16px">👤 ' + _esc(uploadedBy) + ' · ' + _esc(uploadedAt) + (fileSizeKb ? ' · ' + _esc(fileSizeKb) : '') + '</div>' +
            '<div style="display:flex;gap:8px">' +
            '<button class="btn btn-success" style="flex:1" onclick="EpicPhotos.moderateFromPopup(\'approved\')">✅ Схвалити</button>' +
            '<button class="btn btn-danger" style="flex:1" onclick="EpicPhotos.moderateFromPopup(\'rejected\')">❌ Відхилити</button>' +
            '</div>' +
            '<button class="btn btn-ghost" onclick="EpicPhotos.closeModerationPopup()" style="margin-top:8px">Закрити</button>';
    }

    function closeModerationPopup() {
        var popup = document.getElementById('moderation-popup');
        if (popup) popup.style.display = 'none';
        _currentPhotoId = null;
    }

    function moderateFromPopup(status) {
        if (!_currentPhotoId) return;
        moderatePhoto(_currentPhotoId, status);
    }

    return { loadModeration, moderatePhoto, openModerationPopup, closeModerationPopup, moderateFromPopup };
})();
