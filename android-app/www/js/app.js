/**
 * www/js/app.js
 * Головний модуль додатку EpicService Android.
 */
const App = (function () {
    'use strict';

    // --- Стан ---
    let _user = null;
    let _token = null;
    let _activeTab = 'search';
    let _searchTimeout = null;
    let _isOffline = !navigator.onLine;
    let _pullStartY = 0;
    let _isPulling = false;
    let _cachedProducts = [];
    let _currentDepartment = null;
    let _selectedProduct = null;
    let _addQty = 1;

    // --- Ініціалізація ---
    function init(user, token) {
        _user = user;
        _token = token;
        _setupNetworkMonitor();
        _setupPullToRefresh();
        _updateUserUI();
        loadList();
        if (_isOffline) showOfflineBanner();
    }

    function reset() {
        _user = null;
        _token = null;
        _cachedProducts = [];
        _currentDepartment = null;
    }

    function _updateUserUI() {
        if (!_user) return;
        const avatar = document.getElementById('user-avatar');
        const userName = document.getElementById('user-name');
        const menuName = document.getElementById('menu-user-name');
        const menuRole = document.getElementById('menu-user-role');
        const menuPhone = document.getElementById('menu-user-phone');

        const displayName = _user.display_name || _user.username || '?';
        if (avatar) avatar.textContent = displayName[0].toUpperCase();
        if (userName) userName.textContent = displayName;
        if (menuName) menuName.textContent = displayName;
        if (menuRole) menuRole.textContent = _user.role || '';
        if (menuPhone && _user.phone) {
            menuPhone.textContent = _user.phone;
            menuPhone.style.display = 'block';
        }

        // Show/hide tabs based on role
        const role = _user.role || '';
        const tabAdmin = document.getElementById('tab-admin');
        const tabModeration = document.getElementById('tab-moderation');
        if (tabAdmin) tabAdmin.classList.toggle('hidden', !['admin', 'superadmin'].includes(role));
        if (tabModeration) tabModeration.classList.toggle('hidden', role !== 'moderator');
    }

    // --- Вкладки ---
    function switchTab(name) {
        _activeTab = name;
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        document.getElementById('tab-' + name)?.classList.add('active');
        document.getElementById('content-' + name)?.classList.add('active');

        if (name === 'archives') {
            if (typeof EpicArchives !== 'undefined') EpicArchives.load();
            else loadArchives();
        }
        if (name === 'admin') loadAdmin();
        if (name === 'moderation' && typeof EpicPhotos !== 'undefined') EpicPhotos.loadModeration();
        if (typeof EpicFilters !== 'undefined') EpicFilters.updateButtonVisibility();
    }

    // --- Пошук ---
    function onSearch(query) {
        clearTimeout(_searchTimeout);
        query = query.trim();
        if (!query) {
            _renderSearchEmpty('Введіть артикул або назву товару');
            return;
        }
        if (query.length < 2) return;
        _searchTimeout = setTimeout(() => _doSearch(query), 350);
    }

    async function _doSearch(query) {
        const resultsEl = document.getElementById('search-results');
        if (!resultsEl) return;
        resultsEl.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
        try {
            const data = await EpicAPI.post('/api/search', { query, user_id: _user.id }, _token);
            _cachedProducts = data.products || [];
            const available = _cachedProducts.filter(p => (p.available || 0) > 0);
            _renderSearchResults(available);
        } catch (e) {
            resultsEl.innerHTML =
                '<div class="empty-state"><div class="empty-icon">❌</div><p>' +
                (e.message || 'Помилка пошуку') + '</p></div>';
        }
    }

    function _renderSearchResults(items) {
        const el = document.getElementById('search-results');
        if (!el) return;
        if (!items.length) { _renderSearchEmpty('Нічого не знайдено'); return; }
        el.innerHTML = items.map(p => _productCardHtml(p)).join('');
    }

    function renderFilterResults(products, stats) {
        _cachedProducts = products || [];
        _renderSearchResults(_cachedProducts);
        if (stats) {
            const box = document.getElementById('filter-stats-box');
            const cnt = document.getElementById('filter-stats-count');
            const sum = document.getElementById('filter-stats-sum');
            if (box) box.style.display = 'block';
            if (cnt) cnt.textContent = stats.total_count || 0;
            if (sum) sum.textContent = (stats.total_sum || 0).toLocaleString('uk-UA') + ' грн';
        }
    }

    function _renderSearchEmpty(msg) {
        const el = document.getElementById('search-results');
        if (el) el.innerHTML =
            '<div class="empty-state"><div class="empty-icon">🔍</div><p>' + msg + '</p></div>';
    }

    function _productCardHtml(p) {
        const article = p.article || '';
        const name = p.name || '';
        const available = parseFloat(p.available || 0);
        const dept = p.department || '';
        const group = p.group || '';
        const months = p.months_without_movement || 0;
        const price = p.price || 0;
        const userReserved = p.user_reserved || 0;
        const locked = !!p.is_different_department;

        const qtyClass = available <= 0 ? 'zero' : available < 5 ? 'low' : '';
        const lockOverlay = locked
            ? '<div style="position:absolute;inset:0;background:rgba(0,0,0,0.4);border-radius:inherit;display:flex;align-items:center;justify-content:center;font-size:24px;pointer-events:none">🔒</div>'
            : '';
        const btnDisabled = locked ? ' disabled style="opacity:0.5"' : '';
        const pEnc = JSON.stringify(JSON.stringify(p)).replace(/"/g, '&quot;');
        const artEnc = JSON.stringify(article).replace(/"/g, '&quot;');

        return '<div class="product-card" style="position:relative" onclick="App.openProduct(' + artEnc + ')">' +
            lockOverlay +
            '<div class="product-card-header">' +
            '<div style="flex:1">' +
            '<div class="product-article">' + article + '</div>' +
            '<div class="product-name">' + name + '</div>' +
            '</div>' +
            '<div class="product-qty ' + qtyClass + '">' + available + '</div>' +
            '</div>' +
            '<div class="product-meta">' +
            (dept ? '<span class="product-tag">🏢 Відділ ' + dept + '</span>' : '') +
            (group ? '<span class="product-tag">📂 ' + group + '</span>' : '') +
            (price ? '<span class="product-tag">💰 ' + price + ' грн</span>' : '') +
            (months > 3 ? '<span class="product-tag" style="color:var(--warning)">⏳ ' + months + ' міс. без руху</span>' : '') +
            (userReserved > 0 ? '<span class="product-tag" style="color:var(--accent)">🛒 Ваш: ' + userReserved + '</span>' : '') +
            '</div>' +
            '<div class="product-actions">' +
            '<button class="action-btn action-btn-primary"' + btnDisabled +
            ' onclick="event.stopPropagation(); App.openAddModal(' + pEnc + ')">➕ До списку</button>' +
            '</div></div>';
    }

    // --- Товар: деталі ---
    function openProduct(article) {
        const modal = document.getElementById('product-modal');
        const content = document.getElementById('modal-content');
        if (!modal || !content) return;

        const cached = _cachedProducts.find(p => p.article === article);
        if (cached) {
            content.innerHTML = _productDetailHtml(cached);
            modal.style.display = 'flex';
            return;
        }

        content.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
        modal.style.display = 'flex';

        EpicAPI.get('/api/products/' + encodeURIComponent(article), _token)
            .then(data => {
                const p = data.product || data;
                content.innerHTML = _productDetailHtml(p);
            })
            .catch(() => {
                content.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><p>Помилка завантаження</p></div>';
            });
    }

    function _productDetailHtml(p) {
        const article = p.article || '';
        const name = p.name || '';
        const available = parseFloat(p.available || p.quantity || 0);
        const dept = p.department || '';
        const group = p.group || '';
        const reserved = p.reserved || 0;
        const userReserved = p.user_reserved || 0;
        const months = p.months_without_movement || 0;
        const price = parseFloat(p.price || 0);
        const balanceSum = parseFloat(p.balance_sum || 0);
        const pEnc = JSON.stringify(JSON.stringify(p)).replace(/"/g, '&quot;');

        const avColor = available <= 0 ? 'var(--danger)' : available < 5 ? 'var(--warning)' : 'var(--success)';
        const mColor = months > 6 ? 'var(--danger)' : months > 3 ? 'var(--warning)' : 'var(--text-muted)';

        return '<div>' +
            '<h2 style="font-size:18px;font-weight:700;color:var(--text-primary);margin-bottom:6px">' + name + '</h2>' +
            '<div style="font-family:\'Courier New\',monospace;color:var(--accent-light);font-size:14px;margin-bottom:16px">' + article + '</div>' +
            '<div class="stats-grid">' +
            '<div class="stat-card"><div class="stat-value" style="color:' + avColor + '">' + available + '</div><div class="stat-label">Доступно</div></div>' +
            '<div class="stat-card"><div class="stat-value" style="color:var(--warning)">' + reserved + '</div><div class="stat-label">Відкладено</div></div>' +
            '<div class="stat-card"><div class="stat-value" style="font-size:18px">' + price.toLocaleString('uk-UA') + ' ₴</div><div class="stat-label">Ціна</div></div>' +
            '<div class="stat-card"><div class="stat-value" style="font-size:18px">' + balanceSum.toLocaleString('uk-UA') + ' ₴</div><div class="stat-label">Сума</div></div>' +
            '</div>' +
            '<div class="product-meta" style="margin-bottom:16px">' +
            (dept ? '<span class="product-tag">🏢 Відділ ' + dept + '</span>' : '') +
            (group ? '<span class="product-tag">📂 ' + group + '</span>' : '') +
            (months > 0 ? '<span class="product-tag" style="color:' + mColor + '">⏳ ' + months + ' міс. без руху</span>' : '') +
            (userReserved > 0 ? '<span class="product-tag" style="color:var(--accent)">🛒 Ваш: ' + userReserved + '</span>' : '') +
            '</div>' +
            '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
            '<button class="action-btn action-btn-primary" style="flex:1"' +
            ' onclick="App.openAddModal(' + pEnc + '); App.closeProductModal()">➕ До списку</button>' +
            '</div></div>';
    }

    function closeProductModal(event) {
        if (!event || event.target === document.getElementById('product-modal')) {
            document.getElementById('product-modal').style.display = 'none';
        }
    }

    // --- Add Modal ---
    function openAddModal(productJson) {
        let p;
        try { p = typeof productJson === 'string' ? JSON.parse(productJson) : productJson; }
        catch (e) { toast('Помилка даних товару', 'error'); return; }

        _selectedProduct = p;
        _addQty = 1;

        const modal = document.getElementById('add-modal');
        if (!modal) return;

        const titleEl = document.getElementById('add-modal-title');
        const priceEl = document.getElementById('add-modal-price');
        const availableEl = document.getElementById('add-modal-available');
        const qtyDisplay = document.getElementById('add-qty-display');
        const normalSel = document.getElementById('add-normal-selector');
        const customInp = document.getElementById('add-custom-input');

        if (titleEl) titleEl.textContent = p.name || p.article || '';
        if (priceEl) priceEl.textContent = p.price ? '💰 ' + p.price + ' грн' : '';
        if (availableEl) availableEl.textContent = '📦 Доступно: ' + (p.available || 0);
        if (qtyDisplay) qtyDisplay.textContent = '1';
        if (normalSel) normalSel.style.display = 'block';
        if (customInp) customInp.style.display = 'none';

        modal.style.display = 'flex';
    }

    function closeAddModal(event) {
        if (!event || event.target === document.getElementById('add-modal')) {
            const modal = document.getElementById('add-modal');
            if (modal) modal.style.display = 'none';
            _selectedProduct = null;
            _addQty = 1;
        }
    }

    function changeAddQty(delta) {
        if (!_selectedProduct) return;
        const max = _selectedProduct.available || 9999;
        _addQty = Math.max(1, Math.min(max, _addQty + delta));
        const display = document.getElementById('add-qty-display');
        if (display) display.textContent = _addQty;
    }

    function addAllAvailable() {
        if (!_selectedProduct) return;
        _addQty = _selectedProduct.available || 1;
        const display = document.getElementById('add-qty-display');
        if (display) display.textContent = _addQty;
    }

    function showCustomInput() {
        const normalSel = document.getElementById('add-normal-selector');
        const customInp = document.getElementById('add-custom-input');
        if (normalSel) normalSel.style.display = 'none';
        if (customInp) customInp.style.display = 'block';
        const input = document.getElementById('add-custom-qty');
        if (input) { input.value = _addQty; input.focus(); }
    }

    function applyCustomQty() {
        const input = document.getElementById('add-custom-qty');
        if (!input) return;
        const val = parseInt(input.value, 10);
        if (!val || val < 1) { toast('Введіть коректну кількість', 'error'); return; }
        const max = _selectedProduct ? (_selectedProduct.available || 9999) : 9999;
        _addQty = Math.min(val, max);
        const normalSel = document.getElementById('add-normal-selector');
        const customInp = document.getElementById('add-custom-input');
        const display = document.getElementById('add-qty-display');
        if (normalSel) normalSel.style.display = 'block';
        if (customInp) customInp.style.display = 'none';
        if (display) display.textContent = _addQty;
    }

    async function confirmAdd() {
        if (!_selectedProduct) return;
        try {
            const data = await EpicAPI.post('/api/add', {
                user_id: _user.id,
                product_id: _selectedProduct.id,
                quantity: _addQty
            }, _token);
            if (data.success) {
                const idx = _cachedProducts.findIndex(p => p.id === _selectedProduct.id);
                if (idx >= 0) {
                    _cachedProducts[idx].available = Math.max(0, (_cachedProducts[idx].available || 0) - _addQty);
                    _cachedProducts[idx].user_reserved = (_cachedProducts[idx].user_reserved || 0) + _addQty;
                }
                toast(data.message || 'Додано до списку ✅', 'success');
                closeAddModal();
                loadList();
            } else {
                toast(data.message || 'Помилка додавання', 'error');
            }
        } catch (e) {
            toast(e.message || 'Помилка додавання', 'error');
        }
    }

    // --- Список ---
    async function loadList() {
        if (!_user) return;
        const el = document.getElementById('list-content');
        const actions = document.getElementById('list-actions');

        try {
            const [listData, deptData] = await Promise.all([
                EpicAPI.get('/api/list/' + _user.id, _token),
                EpicAPI.get('/api/list/department/' + _user.id, _token).catch(() => null)
            ]);

            const items = listData.items || [];
            const count = listData.count !== undefined ? listData.count : items.length;
            updateListBadge(count);

            if (deptData && deptData.department) {
                updateDepartmentInfo(deptData.department, count);
            }

            if (!el) return;
            if (!items.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><p>Список порожній</p></div>';
                if (actions) actions.style.display = 'none';
                return;
            }

            if (actions) actions.style.display = 'flex';
            el.innerHTML = items.map(function(item) {
                return '<div class="product-card" style="display:flex;align-items:center;gap:12px">' +
                    '<div style="flex:1">' +
                    '<div class="product-article">' + (item.article || '') + '</div>' +
                    '<div class="product-name">' + (item.name || '') + '</div>' +
                    (item.price ? '<div style="font-size:12px;color:var(--text-muted)">💰 ' + item.price + ' грн</div>' : '') +
                    '</div>' +
                    '<div class="qty-control">' +
                    '<button class="qty-btn" onclick="App.changeQty(' + item.product_id + ', -1)">−</button>' +
                    '<span class="qty-val" data-pid="' + item.product_id + '">' + item.quantity + '</span>' +
                    '<button class="qty-btn" onclick="App.changeQty(' + item.product_id + ', 1)">+</button>' +
                    '</div>' +
                    '<button class="action-btn" style="padding:8px;margin:0" onclick="App.removeListItem(' + item.product_id + ')">✕</button>' +
                    '</div>';
            }).join('');
        } catch (e) {
            if (el) el.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><p>' + e.message + '</p></div>';
        }
    }

    async function changeQty(productId, delta) {
        const valEl = document.querySelector('.qty-val[data-pid="' + productId + '"]');
        const currentQty = valEl ? (parseInt(valEl.textContent, 10) || 1) : 1;
        const newQty = Math.max(1, currentQty + delta);
        await updateListItem(productId, newQty);
    }

    async function updateListItem(productId, newQty) {
        try {
            const data = await EpicAPI.post('/api/update', {
                user_id: _user.id,
                product_id: productId,
                quantity: newQty
            }, _token);
            if (data.success) await loadList();
            else toast(data.message || 'Помилка оновлення', 'error');
        } catch (e) {
            toast(e.message || 'Помилка оновлення', 'error');
        }
    }

    async function removeListItem(productId) {
        try {
            const data = await EpicAPI.post('/api/delete', {
                user_id: _user.id,
                product_id: productId
            }, _token);
            if (data.success) await loadList();
            else toast(data.message || 'Помилка видалення', 'error');
        } catch (e) {
            toast(e.message || 'Помилка видалення', 'error');
        }
    }

    async function clearList() {
        if (!confirm('Очистити весь список?')) return;
        try {
            const data = await EpicAPI.post('/api/clear/' + _user.id, {}, _token);
            if (data.success) {
                toast('Список очищено', 'success');
                await loadList();
            } else {
                toast(data.message || 'Помилка очищення', 'error');
            }
        } catch (e) {
            toast(e.message || 'Помилка очищення', 'error');
        }
    }

    async function saveList() {
        try {
            const data = await EpicAPI.post('/api/save/' + _user.id, {}, _token);
            if (data.success) {
                const filenameEl = document.getElementById('success-filename');
                if (filenameEl) filenameEl.textContent = data.filename || '';
                const modal = document.getElementById('success-modal');
                if (modal) modal.style.display = 'flex';
                await loadList();
            } else {
                toast(data.message || 'Помилка збереження', 'error');
            }
        } catch (e) {
            toast(e.message || 'Помилка збереження', 'error');
        }
    }

    function updateListBadge(count) {
        const badge = document.getElementById('list-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    function updateDepartmentInfo(dept, count) {
        const banner = document.getElementById('dept-banner');
        const deptName = document.getElementById('dept-name');
        const deptCount = document.getElementById('dept-count');
        if (!banner) return;
        if (dept) {
            if (deptName) deptName.textContent = dept;
            if (deptCount) deptCount.textContent = count || 0;
            banner.style.display = 'block';
        } else {
            banner.style.display = 'none';
        }
    }

    // --- Архіви ---
    async function loadArchives() {
        if (!_user) return;
        const el = document.getElementById('archives-content');
        if (!el) return;

        const SERVER = window.APP_CONFIG ? window.APP_CONFIG.serverUrl : 'https://anubis-ua.pp.ua';

        try {
            const data = await EpicAPI.get('/api/archives/' + _user.id, _token);
            const archives = data.archives || [];
            if (!archives.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-icon">📁</div><p>Архів порожній</p></div>';
                return;
            }
            el.innerHTML = archives.map(function(a) {
                const fn = encodeURIComponent(a.filename || '');
                return '<div class="archive-card">' +
                    '<div>' +
                    '<div class="archive-name">📄 ' + (a.filename || '') + '</div>' +
                    '<div class="archive-date">' + _formatDate(a.date) + '</div>' +
                    (a.type ? '<div style="font-size:11px;color:var(--text-muted)">' + a.type + (a.is_surplus ? ' · надлишки' : '') + '</div>' : '') +
                    '</div>' +
                    '<button class="action-btn" onclick="window.open(\'' + SERVER + '/api/archive/download/' + fn + '?token=' + _token + '\', \'_blank\')">⬇️</button>' +
                    '</div>';
            }).join('');
        } catch (e) {
            el.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><p>' + e.message + '</p></div>';
        }
    }

    // --- Адмін ---
    function loadAdmin() {
        if (!['admin', 'superadmin'].includes(_user ? _user.role : '')) return;
        if (typeof EpicAdmin !== 'undefined') EpicAdmin.load();
    }

    // --- Мережа ---
    function _setupNetworkMonitor() {
        window.addEventListener('online', function() {
            _isOffline = false;
            const banner = document.getElementById('offline-banner');
            if (banner) banner.style.display = 'none';
            const icon = document.getElementById('conn-icon');
            const status = document.getElementById('conn-status');
            if (icon) icon.textContent = '🟢';
            if (status) status.textContent = 'Онлайн';
        });
        window.addEventListener('offline', function() {
            _isOffline = true;
            showOfflineBanner();
            const icon = document.getElementById('conn-icon');
            const status = document.getElementById('conn-status');
            if (icon) icon.textContent = '🔴';
            if (status) status.textContent = 'Офлайн';
        });
    }

    function showOfflineBanner() {
        const el = document.getElementById('offline-banner');
        if (el) el.style.display = 'block';
    }

    function _showOfflineBadge(container) {
        const badge = document.createElement('div');
        badge.style.cssText = 'font-size:12px;color:var(--warning);padding:6px 12px;text-align:center';
        badge.textContent = '📵 Дані з кешу (офлайн)';
        container.insertBefore(badge, container.firstChild);
    }

    // --- Pull to Refresh ---
    function _setupPullToRefresh() {
        const content = document.getElementById('content-search');
        if (!content) return;
        content.addEventListener('touchstart', function(e) {
            if (content.scrollTop === 0) {
                _pullStartY = e.touches[0].clientY;
                _isPulling = true;
            }
        }, { passive: true });
        content.addEventListener('touchmove', function(e) {
            if (!_isPulling) return;
            const dy = e.touches[0].clientY - _pullStartY;
            if (dy > 50) {
                const indicator = document.getElementById('pull-indicator');
                if (indicator) indicator.style.display = 'block';
            }
        }, { passive: true });
        content.addEventListener('touchend', function(e) {
            if (!_isPulling) return;
            _isPulling = false;
            const dy = e.changedTouches[0].clientY - _pullStartY;
            const indicator = document.getElementById('pull-indicator');
            if (indicator) indicator.style.display = 'none';
            if (dy > 80) {
                const searchInput = document.getElementById('search-input');
                const query = searchInput ? searchInput.value.trim() : '';
                if (query) _doSearch(query);
            }
        }, { passive: true });
    }

    // --- Toast ---
    function toast(msg, type) {
        type = type || 'info';
        const container = document.getElementById('toast-container');
        if (!container) return;
        const el = document.createElement('div');
        el.className = 'toast ' + type;
        el.textContent = msg;
        container.appendChild(el);
        setTimeout(function() { el.remove(); }, 3200);
    }

    // --- Утиліти ---
    function _formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            return new Date(dateStr).toLocaleDateString('uk-UA', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
        } catch (e) { return dateStr; }
    }

    function getUser() { return _user; }
    function getToken() { return _token; }

    return {
        init, reset, switchTab, onSearch, renderFilterResults,
        getUser, getToken,
        openProduct, closeProductModal,
        openAddModal, closeAddModal, changeAddQty, addAllAvailable,
        showCustomInput, applyCustomQty, confirmAdd,
        changeQty, updateListItem, removeListItem, clearList, saveList,
        loadList, updateListBadge, updateDepartmentInfo,
        loadArchives, loadAdmin,
        showOfflineBanner, toast,
    };
})();

// Закриття меню при кліку поза ним
document.addEventListener('click', function(e) {
    const menu = document.getElementById('user-menu');
    const trigger = document.getElementById('header-user');
    if (menu && !menu.contains(e.target) && !(trigger && trigger.contains(e.target))) {
        menu.style.display = 'none';
    }
});

function toggleUserMenu() {
    const menu = document.getElementById('user-menu');
    if (menu) menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

function showOfflineStatus() {
    const online = navigator.onLine;
    App.toast(online ? '🟢 Онлайн' : '🔴 Офлайн', online ? 'success' : 'error');
}

function goToArchives() {
    const modal = document.getElementById('success-modal');
    if (modal) modal.style.display = 'none';
    App.switchTab('archives');
}

function startNewSearch() {
    const modal = document.getElementById('success-modal');
    if (modal) modal.style.display = 'none';
    App.switchTab('search');
    const input = document.getElementById('search-input');
    if (input) { input.value = ''; input.focus(); }
}
