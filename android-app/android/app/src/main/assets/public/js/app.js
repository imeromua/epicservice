/**
 * www/js/app.js
 * Головний модуль додатку EpicService Android.
 * Управляє вкладками, пошуком, списком та архівами.
 */
const App = (function () {
    'use strict';

    // --- Стан ---
    let _user = null;
    let _token = null;
    let _activeTab = 'search';
    let _searchTimeout = null;
    let _listItems = {};    // { productId: { product, qty } }
    let _isOffline = !navigator.onLine;
    let _pullStartY = 0;
    let _isPulling = false;

    // --- Ініціалізація ---
    function init(user, token) {
        _user = user;
        _token = token;
        _setupNetworkMonitor();
        _setupPullToRefresh();
        _loadCachedList();
        _updateListBadge();
        loadArchives();
        if (_isOffline) showOfflineBanner();
    }

    function reset() {
        _user = null;
        _token = null;
        _listItems = {};
        _updateListBadge();
    }

    // --- Вкладки ---
    function switchTab(name) {
        _activeTab = name;
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        document.getElementById(`tab-${name}`)?.classList.add('active');
        document.getElementById(`content-${name}`)?.classList.add('active');

        if (name === 'archives') loadArchives();
        if (name === 'admin') loadAdmin();
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
            const { data, fromCache } = await EpicAPI.getWithCache(
                `/api/products/search?q=${encodeURIComponent(query)}&limit=50`,
                _token,
                `search_${query}`
            );

            if (fromCache) _showOfflineBadge(resultsEl);
            _renderSearchResults(data.items || data.results || []);
        } catch (e) {
            resultsEl.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">❌</div>
                    <p>${e.message || 'Помилка пошуку'}</p>
                </div>`;
        }
    }

    function _renderSearchResults(items) {
        const el = document.getElementById('search-results');
        if (!el) return;

        if (!items.length) {
            _renderSearchEmpty('Нічого не знайдено');
            return;
        }

        el.innerHTML = items.map(p => _productCardHtml(p)).join('');
    }

    function _renderSearchEmpty(msg) {
        const el = document.getElementById('search-results');
        if (el) el.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔍</div>
                <p>${msg}</p>
            </div>`;
    }

    function _productCardHtml(p) {
        const article = p.артикул || p.article || '';
        const name = p.назва || p.name || '';
        const qty = parseFloat(p.кількість ?? p.quantity ?? 0);
        const dept = p.відділ || p.department || '';
        const group = p.група || p.group || '';
        const reserved = p.відкладено || p.reserved || 0;
        const months = p.місяці_без_руху || p.months_no_move || 0;
        const price = p.ціна || p.price || 0;

        const qtyClass = qty <= 0 ? 'zero' : qty < 5 ? 'low' : '';
        const inList = _listItems[article] ? 'action-btn-primary' : '';

        return `
        <div class="product-card" onclick="App.openProduct(${JSON.stringify(article).replace(/"/g, '&quot;')})">
            <div class="product-card-header">
                <div style="flex:1">
                    <div class="product-article">${article}</div>
                    <div class="product-name">${name}</div>
                </div>
                <div class="product-qty ${qtyClass}">${qty}</div>
            </div>
            <div class="product-meta">
                ${dept ? `<span class="product-tag">🏢 Відділ ${dept}</span>` : ''}
                ${group ? `<span class="product-tag">📂 ${group}</span>` : ''}
                ${price ? `<span class="product-tag">💰 ${price} грн</span>` : ''}
                ${months > 3 ? `<span class="product-tag" style="color:var(--warning)">⏳ ${months} міс. без руху</span>` : ''}
                ${reserved > 0 ? `<span class="product-tag" style="color:var(--danger)">🔒 ${reserved} відкладено</span>` : ''}
            </div>
            <div class="product-actions">
                <button class="action-btn action-btn-primary ${inList}" 
                        onclick="event.stopPropagation(); App.addToList(${JSON.stringify(JSON.stringify(p)).replace(/"/g, '&quot;')})">
                    ➕ До списку
                </button>
            </div>
        </div>`;
    }

    // --- Товар: деталі ---
    function openProduct(article) {
        const modal = document.getElementById('product-modal');
        const content = document.getElementById('modal-content');
        if (!modal || !content) return;
        content.innerHTML = '<div class="loader-center"><div class="loader"></div></div>';
        modal.style.display = 'flex';

        EpicAPI.get(`/api/products/${encodeURIComponent(article)}`, _token)
            .then(data => {
                const p = data.product || data;
                content.innerHTML = _productDetailHtml(p);
            })
            .catch(() => {
                content.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><p>Помилка завантаження</p></div>';
            });
    }

    function _productDetailHtml(p) {
        const article = p.артикул || p.article || '';
        const name = p.назва || p.name || '';
        const qty = parseFloat(p.кількість ?? p.quantity ?? 0);
        const dept = p.відділ || p.department || '';
        const group = p.група || p.group || '';
        const reserved = p.відкладено || p.reserved || 0;
        const months = p.місяці_без_руху || p.months_no_move || 0;
        const price = p.ціна || p.price || 0;
        const total = p.сума_залишку || p.total_value || 0;

        return `
        <div>
            <h2 style="font-size:18px;font-weight:700;color:var(--text-primary);margin-bottom:6px">${name}</h2>
            <div style="font-family:'Courier New',monospace;color:var(--accent-light);font-size:14px;margin-bottom:16px">${article}</div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" style="color:${qty <= 0 ? 'var(--danger)' : qty < 5 ? 'var(--warning)' : 'var(--success)'}">${qty}</div>
                    <div class="stat-label">Залишок</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color:var(--warning)">${reserved}</div>
                    <div class="stat-label">Відкладено</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="font-size:18px">${price.toLocaleString('uk-UA')} ₴</div>
                    <div class="stat-label">Ціна</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="font-size:18px">${total.toLocaleString('uk-UA')} ₴</div>
                    <div class="stat-label">Сума</div>
                </div>
            </div>
            <div class="product-meta" style="margin-bottom:16px">
                ${dept ? `<span class="product-tag">🏢 Відділ ${dept}</span>` : ''}
                ${group ? `<span class="product-tag">📂 ${group}</span>` : ''}
                ${months > 0 ? `<span class="product-tag" style="color:${months>6?'var(--danger)':months>3?'var(--warning)':'var(--text-muted)'}">⏳ ${months} міс. без руху</span>` : ''}
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
                <button class="action-btn action-btn-primary" style="flex:1" 
                        onclick="App.addToList(${JSON.stringify(JSON.stringify(p)).replace(/"/g, '&quot;')}); App.closeProductModal()">
                    ➕ До списку
                </button>
            </div>
        </div>`;
    }

    function closeProductModal(event) {
        if (!event || event.target === document.getElementById('product-modal')) {
            document.getElementById('product-modal').style.display = 'none';
        }
    }

    // --- Список ---
    function addToList(productJson) {
        let product;
        try { product = typeof productJson === 'string' ? JSON.parse(productJson) : productJson; }
        catch { return; }

        const article = product.артикул || product.article || '';
        if (!article) return;

        if (_listItems[article]) {
            _listItems[article].qty++;
        } else {
            _listItems[article] = { product, qty: 1 };
        }

        _saveListToCache();
        _updateListBadge();
        _renderList();
        toast(`${article} — додано до списку`, 'success');
    }

    function _renderList() {
        const el = document.getElementById('list-content');
        const actions = document.getElementById('list-actions');
        if (!el) return;

        const items = Object.values(_listItems);
        if (!items.length) {
            el.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><p>Список порожній</p></div>';
            if (actions) actions.style.display = 'none';
            return;
        }

        if (actions) actions.style.display = 'flex';

        el.innerHTML = items.map(({ product, qty }) => {
            const article = product.артикул || product.article || '';
            const name = product.назва || product.name || '';
            return `
            <div class="product-card" style="display:flex;align-items:center;gap:12px">
                <div style="flex:1">
                    <div class="product-article">${article}</div>
                    <div class="product-name">${name}</div>
                </div>
                <div class="qty-control">
                    <button class="qty-btn" onclick="App.changeQty('${article}',-1)">−</button>
                    <span class="qty-val">${qty}</span>
                    <button class="qty-btn" onclick="App.changeQty('${article}',1)">+</button>
                </div>
                <button class="action-btn" style="padding:8px;margin:0" 
                        onclick="App.removeFromList('${article}')">✕</button>
            </div>`;
        }).join('');
    }

    function changeQty(article, delta) {
        if (!_listItems[article]) return;
        _listItems[article].qty = Math.max(1, _listItems[article].qty + delta);
        _saveListToCache();
        _renderList();
    }

    function removeFromList(article) {
        delete _listItems[article];
        _saveListToCache();
        _updateListBadge();
        _renderList();
    }

    function clearList() {
        if (!Object.keys(_listItems).length) return;
        if (confirm('Очистити весь список?')) {
            _listItems = {};
            _saveListToCache();
            _updateListBadge();
            _renderList();
        }
    }

    async function saveList() {
        const items = Object.entries(_listItems).map(([article, { product, qty }]) => ({
            article_name: product.назва || product.name || article,
            quantity: qty,
        }));
        if (!items.length) { toast('Список порожній', 'info'); return; }

        try {
            await EpicAPI.post('/api/saved-lists', { items }, _token);
            toast('Список збережено ✅', 'success');
            loadArchives();
        } catch (e) {
            toast(e.message || 'Помилка збереження', 'error');
        }
    }

    function _updateListBadge() {
        const badge = document.getElementById('list-badge');
        const count = Object.keys(_listItems).length;
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    function _saveListToCache() {
        try { localStorage.setItem('epic_list', JSON.stringify(_listItems)); }
        catch { /* ігнорувати */ }
    }

    function _loadCachedList() {
        try {
            const raw = localStorage.getItem('epic_list');
            if (raw) _listItems = JSON.parse(raw);
        } catch { _listItems = {}; }
        _renderList();
    }

    // --- Архіви ---
    async function loadArchives() {
        if (_activeTab !== 'archives' && !document.getElementById('content-archives').classList.contains('active')) return;

        const el = document.getElementById('archives-content');
        if (!el) return;

        try {
            const { data, fromCache } = await EpicAPI.getWithCache(
                '/api/saved-lists',
                _token,
                `archives_${_user?.id}`
            );

            const lists = data.lists || data || [];
            if (!lists.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-icon">📁</div><p>Архів порожній</p></div>';
                return;
            }

            el.innerHTML = lists.map(l => `
                <div class="archive-card">
                    <div>
                        <div class="archive-name">📄 ${l.file_name || l.name || 'Список'}</div>
                        <div class="archive-date">${_formatDate(l.created_at || l.date)}</div>
                    </div>
                    <button class="action-btn" onclick="App.downloadArchive(${l.id})">⬇️</button>
                </div>
            `).join('');
        } catch (e) {
            el.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><p>${e.message}</p></div>`;
        }
    }

    async function downloadArchive(id) {
        try {
            window.open(`${EpicAPI._server || 'https://anubis-ua.pp.ua'}/api/saved-lists/${id}/download?token=${_token}`, '_blank');
        } catch (e) {
            toast('Помилка завантаження', 'error');
        }
    }

    // --- Адмін ---
    async function loadAdmin() {
        if (!['admin', 'superadmin'].includes(_user?.role)) return;
        const el = document.getElementById('admin-content');
        if (!el) return;

        try {
            const data = await EpicAPI.get('/api/admin/stats', _token);
            el.innerHTML = `
                <div class="admin-section">
                    <div class="admin-section-title">📊 Статистика</div>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">${data.total_users || 0}</div>
                            <div class="stat-label">Користувачів</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.active_users || 0}</div>
                            <div class="stat-label">Активних</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.total_products || 0}</div>
                            <div class="stat-label">Товарів</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.pending_users || 0}</div>
                            <div class="stat-label">Очікують</div>
                        </div>
                    </div>
                </div>`;
        } catch (e) {
            el.innerHTML = `<div class="empty-state"><div class="empty-icon">🛠️</div><p>${e.message}</p></div>`;
        }
    }

    // --- Мережа ---
    function _setupNetworkMonitor() {
        window.addEventListener('online', () => {
            _isOffline = false;
            document.getElementById('offline-banner').style.display = 'none';
            document.getElementById('conn-icon').textContent = '🟢';
            document.getElementById('conn-status').textContent = 'Онлайн';
        });
        window.addEventListener('offline', () => {
            _isOffline = true;
            showOfflineBanner();
            document.getElementById('conn-icon').textContent = '🔴';
            document.getElementById('conn-status').textContent = 'Офлайн';
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

        content.addEventListener('touchstart', e => {
            if (content.scrollTop === 0) {
                _pullStartY = e.touches[0].clientY;
                _isPulling = true;
            }
        }, { passive: true });

        content.addEventListener('touchmove', e => {
            if (!_isPulling) return;
            const dy = e.touches[0].clientY - _pullStartY;
            if (dy > 50) {
                const indicator = document.getElementById('pull-indicator');
                if (indicator) indicator.style.display = 'block';
            }
        }, { passive: true });

        content.addEventListener('touchend', e => {
            if (!_isPulling) return;
            _isPulling = false;
            const dy = e.changedTouches[0].clientY - _pullStartY;
            const indicator = document.getElementById('pull-indicator');
            if (indicator) indicator.style.display = 'none';
            if (dy > 80) {
                const query = document.getElementById('search-input')?.value?.trim();
                if (query) _doSearch(query);
            }
        }, { passive: true });
    }

    // --- Toast ---
    function toast(msg, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.textContent = msg;
        container.appendChild(el);
        setTimeout(() => el.remove(), 3200);
    }

    // --- Утиліти ---
    function _formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            return new Date(dateStr).toLocaleDateString('uk-UA', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
        } catch { return dateStr; }
    }

    return {
        init, reset, switchTab, onSearch,
        openProduct, closeProductModal,
        addToList, changeQty, removeFromList, clearList, saveList,
        loadArchives, downloadArchive, loadAdmin,
        showOfflineBanner, toast,
    };
})();

// Закриття меню при кліку поза ним
document.addEventListener('click', function (e) {
    const menu = document.getElementById('user-menu');
    const trigger = document.getElementById('header-user');
    if (menu && !menu.contains(e.target) && !trigger?.contains(e.target)) {
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
