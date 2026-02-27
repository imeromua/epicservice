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

/**
 * Photos - модуль для додавання фотографій товарів
 */
const Photos = (function() {
    'use strict';

    const _SERVER = window.APP_CONFIG ? window.APP_CONFIG.serverUrl : 'https://anubis-ua.pp.ua';

    function _esc(str) {
        return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    async function openCamera(article) {
        // FIX: Використати Capacitor Camera або fallback через file input
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Camera) {
            try {
                const Camera = window.Capacitor.Plugins.Camera;
                const image = await Camera.getPhoto({
                    quality: 80,
                    allowEditing: false,
                    resultType: 'dataUrl',
                    source: 'PROMPT'
                });
                const blob = await fetch(image.dataUrl).then(function(r) { return r.blob(); });
                await uploadPhoto(article, blob);
            } catch (error) {
                if (error.message !== 'User cancelled photos app') {
                    App.toast('❌ ' + error.message, 'error');
                }
            }
        } else {
            // Fallback: використати стандартний file input з capture
            var input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.capture = 'environment';
            input.onchange = async function(e) {
                var file = e.target.files[0];
                if (file) await uploadPhoto(article, file);
            };
            input.click();
        }
    }

    async function uploadPhoto(article, blob) {
        try {
            App.toast('⏳ Завантаження фото...', 'info');
            var token = App.getToken();
            var formData = new FormData();
            formData.append('photo', blob, 'photo.jpg');
            formData.append('article', article);
            var response = await fetch(_SERVER + '/api/photos/upload', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
                body: formData
            });
            var data = await response.json();
            if (data.success) {
                App.toast('✅ Фото додано!', 'success');
                loadProductPhotos(article);
            } else {
                App.toast('❌ ' + (data.message || 'Помилка'), 'error');
            }
        } catch (error) {
            App.toast('❌ ' + error.message, 'error');
        }
    }

    async function loadProductPhotos(article) {
        try {
            var token = App.getToken();
            var data = await EpicAPI.get('/api/photos/' + encodeURIComponent(article), token);
            var safeId = article.replace(/[^a-zA-Z0-9]/g, '_');
            var container = document.getElementById('product-photos-' + safeId);
            if (!container) return;
            if (!data.photos || !data.photos.length) {
                container.innerHTML = '';
                return;
            }
            container.innerHTML = '<div style="font-size:14px;font-weight:600;margin-bottom:8px">📷 Фото товару (' + data.photos.length + ')</div>' +
                '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">' +
                data.photos.map(function(photo) {
                    var src = _SERVER + (photo.file_path.startsWith('/') ? '' : '/') + photo.file_path;
                    // FIX: Екранувати URL для безпечної вставки в HTML атрибути
                    return '<img src="' + _esc(src) + '" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px;cursor:pointer" onclick="Photos.viewPhoto(\'' + encodeURIComponent(src) + '\')">';
                }).join('') +
                '</div>';
        } catch (error) {
            console.error('Load photos error:', error);
        }
    }

    function viewPhoto(encodedUrl) {
        var url = decodeURIComponent(encodedUrl);
        var modal = document.createElement('div');
        modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.95);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px';
        var img = document.createElement('img');
        img.src = url;
        img.style.cssText = 'max-width:100%;max-height:100%;border-radius:12px';
        var btn = document.createElement('button');
        btn.style.cssText = 'position:absolute;top:20px;right:20px;background:rgba(255,255,255,0.2);border:none;color:white;font-size:24px;padding:8px 16px;border-radius:8px;cursor:pointer';
        btn.textContent = '✕';
        btn.setAttribute('aria-label', 'Закрити перегляд фото');
        btn.onclick = function() { modal.remove(); };
        modal.appendChild(img);
        modal.appendChild(btn);
        document.body.appendChild(modal);
    }

    return { openCamera, uploadPhoto, loadProductPhotos, viewPhoto };
})();
