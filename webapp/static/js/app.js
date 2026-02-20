// EpicService - Main Application Logic

// Telegram WebApp initialization
const tg = window.Telegram.WebApp; 
tg.expand();
tg.ready();

// Global variables
const userId = tg.initDataUnsafe?.user?.id || 0;
const ADMIN_IDS = window.ADMIN_IDS || [];
const isAdmin = ADMIN_IDS.includes(userId);

let currentQuantity = 1;
let editQuantity = 1;
let selectedProduct = null;
let editingItem = null;
let searchTimeout = null;
let currentTab = 'search';
let cachedProducts = [];
let currentDepartment = null;
let pullStartY = 0;
let pulling = false;
let selectedFile = null;
let cachedProductsInfo = null;

// Initialize
if (isAdmin) {
    const adminBtn = document.getElementById('adminTabBtn');
    if (adminBtn) adminBtn.classList.remove('hidden');
}

// Display user info
document.getElementById('userInfo').textContent = userId 
    ? `Користувач: ${tg.initDataUnsafe.user.first_name}${isAdmin ? ' 👑' : ''}` 
    : 'Тестовий режим';

// ===== PULL TO REFRESH =====

document.addEventListener('touchstart', e => {
    if (window.scrollY === 0) {
        pullStartY = e.touches[0].clientY;
        pulling = true;
    }
}, {passive: true});

document.addEventListener('touchmove', e => {
    if (!pulling) return;
    const pullDistance = e.touches[0].clientY - pullStartY;
    const indicator = document.getElementById('pullIndicator');
    
    if (pullDistance > 0 && pullDistance < 80) {
        indicator.style.opacity = pullDistance / 80;
        indicator.style.transform = `translateY(${pullDistance - 50}px)`;
    } else if (pullDistance >= 80) {
        indicator.classList.add('active');
        indicator.textContent = '↻ Відпустіть для оновлення';
    }
}, {passive: true});

document.addEventListener('touchend', e => {
    if (!pulling) return;
    const pullDistance = e.changedTouches[0].clientY - pullStartY;
    const indicator = document.getElementById('pullIndicator');
    
    if (pullDistance >= 80) {
        indicator.textContent = '⟳ Оновлення...';
        tg.HapticFeedback.impactOccurred('medium');
        refreshCurrentTab();
    }
    
    setTimeout(() => {
        indicator.classList.remove('active');
        indicator.style.opacity = 0;
        indicator.style.transform = 'translateY(-100%)';
        indicator.textContent = '↓ Потягніть для оновлення';
    }, 500);
    
    pulling = false;
}, {passive: true});

function refreshCurrentTab() {
    switch(currentTab) {
        case 'search':
            const query = document.getElementById('searchInput').value.trim();
            if (query.length >= 2) search(query);
            break;
        case 'list':
            loadList();
            break;
        case 'archives':
            loadArchives();
            break;
        case 'admin':
            if (isAdmin) loadAdminData();
            break;
    }
}

// ===== DEPARTMENT MANAGEMENT =====

function updateDepartmentInfo(department, count) {
    currentDepartment = department;
    const info = document.getElementById('departmentInfo');
    if (department !== null && count > 0) {
        document.getElementById('currentDepartment').textContent = department;
        document.getElementById('itemCount').textContent = count;
        info.classList.add('active');
    } else {
        info.classList.remove('active');
    }
    
    if (cachedProducts.length > 0) {
        cachedProducts.forEach(p => {
            p.is_different_department = (department !== null && p.department !== department);
            p.current_list_department = department;
        });
        updateSearchResults();
    }
}

// ===== UI HELPERS =====

function updateListBadge(count) { 
    const badge = document.getElementById('listBadge'); 
    if (count > 0) { 
        badge.textContent = count; 
        badge.style.display = 'block'; 
    } else { 
        badge.style.display = 'none'; 
    } 
}

function updateSearchBoxVisibility() { 
    const searchBox = document.getElementById('searchBoxContainer'); 
    if (currentTab === 'search') { 
        searchBox.style.display = 'block'; 
    } else { 
        searchBox.style.display = 'none'; 
    } 
}

function switchTab(tab) { 
    currentTab = tab; 
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active')); 
    document.querySelectorAll('.content').forEach(c => c.classList.remove('active')); 
    
    const tabs = {
        'search': [0,'searchTab'], 
        'list': [1,'listTab'], 
        'archives': [2,'archivesTab'], 
        'admin': [3,'adminContent']
    }; 
    
    const [idx, id] = tabs[tab]; 
    document.querySelectorAll('.tab')[idx].classList.add('active'); 
    document.getElementById(id).classList.add('active'); 
    updateSearchBoxVisibility(); 
    
    if (typeof updateFiltersButtonVisibility === 'function') {
        updateFiltersButtonVisibility();
    }
    
    if (tab === 'list') loadList(); 
    if (tab === 'archives') loadArchives(); 
    if (tab === 'admin' && isAdmin) loadAdminData();
}

function goToArchives() { 
    document.getElementById('successModal').classList.remove('active'); 
    switchTab('archives'); 
}

function startNewSearch() { 
    document.getElementById('successModal').classList.remove('active'); 
    switchTab('search'); 
    document.getElementById('searchInput').focus(); 
}

// ===== SEARCH =====

document.getElementById('searchInput').addEventListener('input', (e) => { 
    clearTimeout(searchTimeout); 
    const query = e.target.value.trim(); 
    if (query.length < 2) { 
        document.getElementById('searchResults').innerHTML = ''; 
        cachedProducts = []; 
        return; 
    } 
    searchTimeout = setTimeout(() => search(query), 500); 
});

function renderProduct(p) {
    const isLocked = p.is_different_department;
    const lockedClass = isLocked ? ' locked' : '';
    const statusClass = isLocked ? ' locked' : '';
    const statusText = isLocked ? '🔒 Заблоковано' : '✅ Знайдено';
    const clickHandler = isLocked 
        ? `onclick="showLockedAlert(${p.current_list_department})"` 
        : `onclick='openAddModal(${JSON.stringify(p).replace(/'/g, "&#39;")})'`;
    
    return `<div class="product-card${lockedClass}" data-product-id="${p.id}" ${clickHandler}>
        <div class="lock-overlay">🔒</div>
        <div class="product-header">
            <span class="product-article">🆔 ${p.article}</span>
            <span class="product-status${statusClass}">${statusText}</span>
        </div>
        <div class="product-name">📝 ${p.name}</div>
        <div class="product-details">
            <div class="product-detail-row"><span class="product-detail-label">🏢 Відділ:</span><span class="product-detail-value">${p.department}</span></div>
            <div class="product-detail-row"><span class="product-detail-label">📂 Група:</span><span class="product-detail-value">${p.group}</span></div>
            <div class="product-detail-row"><span class="product-detail-label">⏳ Без руху (міс):</span><span class="product-detail-value ${p.months_without_movement > 3 ? 'warning' : ''}">${p.months_without_movement}</span></div>
            <div class="product-detail-row"><span class="product-detail-label">💰 Сума залишку:</span><span class="product-detail-value highlight">${p.balance_sum.toFixed(2)} грн</span></div>
            <div class="product-detail-row"><span class="product-detail-label">📦 Доступно:</span><span class="product-detail-value success">${p.available}</span></div>
            ${p.user_reserved > 0 ? `<div class="product-detail-row"><span class="product-detail-label">🛒 В резерві:</span><span class="product-detail-value warning">${p.user_reserved} (${p.user_reserved_sum.toFixed(2)} грн)</span></div>` : ''}
        </div>
    </div>`;
}

function showLockedAlert(dept) {
    tg.showAlert(`🔒 Цей товар з іншого відділу.\n\nПоточний список для відділу ${dept}.\nЗбережіть або очистіть список щоб почати новий.`);
}

function updateSearchResults() {
    const results = document.getElementById('searchResults');
    const visibleProducts = cachedProducts.filter(p => p.available > 0);
    
    if (visibleProducts.length === 0) {
        results.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено або все зарезервовано</div>';
        return;
    }
    
    results.innerHTML = visibleProducts.map(p => renderProduct(p)).join('');
}

async function search(query) { 
    const results = document.getElementById('searchResults'); 
    results.innerHTML = '<div class="loader">🔍 Пошук...</div>'; 
    try { 
        const response = await fetch('/api/search', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({query, user_id: userId}) 
        }); 
        const data = await response.json(); 
        
        if (!data.products || data.products.length === 0) { 
            results.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено</div>'; 
            cachedProducts = [];
            return; 
        }
        
        cachedProducts = data.products.filter(p => p.available > 0);
        updateSearchResults();
    } catch (error) { 
        results.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка пошуку</div>'; 
        cachedProducts = [];
    } 
}

// ===== ADD MODAL =====

function openAddModal(product) { 
    selectedProduct = product; 
    currentQuantity = 1; 
    document.getElementById('modalTitle').textContent = product.article; 
    document.getElementById('modalPrice').textContent = `Ціна: ${product.price.toFixed(2)} грн`; 
    document.getElementById('modalAvailable').textContent = `Доступно: ${product.available} шт.`; 
    document.getElementById('qtyDisplay').textContent = 1; 
    document.getElementById('customInputBox').style.display = 'none'; 
    document.getElementById('normalSelector').style.display = 'block'; 
    document.getElementById('customQtyInput').value = ''; 
    document.getElementById('addModal').classList.add('active'); 
}

function closeModal() { 
    document.getElementById('addModal').classList.remove('active'); 
}

function changeQty(d) { 
    currentQuantity = Math.max(1, Math.min(selectedProduct.available, currentQuantity + d)); 
    document.getElementById('qtyDisplay').textContent = currentQuantity; 
}

function addAllAvailable() { 
    currentQuantity = selectedProduct.available; 
    document.getElementById('qtyDisplay').textContent = currentQuantity; 
    tg.HapticFeedback.notificationOccurred('success'); 
}

function showCustomInput() { 
    document.getElementById('customInputBox').style.display = 'block'; 
    document.getElementById('normalSelector').style.display = 'none'; 
    document.getElementById('customQtyInput').focus(); 
}

function applyCustomQty() { 
    const v = parseInt(document.getElementById('customQtyInput').value); 
    if (isNaN(v) || v < 1) { 
        tg.showAlert('❌ Введіть коректне число'); 
        return; 
    } 
    if (v > selectedProduct.available) { 
        tg.showAlert(`⚠️ Максимум: ${selectedProduct.available} шт.`); 
        return; 
    } 
    currentQuantity = v; 
    document.getElementById('qtyDisplay').textContent = v; 
    document.getElementById('customInputBox').style.display = 'none'; 
    document.getElementById('normalSelector').style.display = 'block'; 
    tg.HapticFeedback.notificationOccurred('success'); 
}

async function confirmAdd() { 
    try { 
        const r = await fetch('/api/add', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({
                user_id: userId, 
                product_id: selectedProduct.id, 
                quantity: currentQuantity
            }) 
        }); 
        const d = await r.json(); 
        
        if (d.success) { 
            tg.showAlert(`✅ ${d.message}`); 
            closeModal(); 
            
            const productIndex = cachedProducts.findIndex(p => p.id === selectedProduct.id);
            if (productIndex !== -1) {
                cachedProducts[productIndex].user_reserved += currentQuantity;
                cachedProducts[productIndex].user_reserved_sum += currentQuantity * selectedProduct.price;
                cachedProducts[productIndex].available -= currentQuantity;
            }
            
            const listResponse = await fetch(`/api/list/${userId}`);
            const listData = await listResponse.json();
            
            const deptResponse = await fetch(`/api/list/department/${userId}`);
            const deptData = await deptResponse.json();
            
            updateDepartmentInfo(deptData.department, listData.count || 0);
            updateListBadge(listData.count || 0);
        } else { 
            tg.showAlert('❌ ' + d.message); 
        } 
    } catch (e) { 
        tg.showAlert('❌ ' + e.message); 
    } 
}

// ===== EDIT MODAL =====

function openEditModal(item) { 
    editingItem = item; 
    editQuantity = item.quantity; 
    document.getElementById('editModalTitle').textContent = item.article; 
    document.getElementById('editModalPrice').textContent = `Ціна: ${item.price.toFixed(2)} грн`; 
    document.getElementById('editQtyDisplay').textContent = editQuantity; 
    document.getElementById('editModal').classList.add('active'); 
}

function closeEditModal() { 
    document.getElementById('editModal').classList.remove('active'); 
}

function changeEditQty(d) { 
    editQuantity = Math.max(1, editQuantity + d); 
    document.getElementById('editQtyDisplay').textContent = editQuantity; 
}

async function confirmUpdate() { 
    try { 
        const r = await fetch('/api/update', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({
                user_id: userId, 
                product_id: editingItem.product_id, 
                quantity: editQuantity
            }) 
        }); 
        const d = await r.json(); 
        
        if (d.success) { 
            tg.showAlert(`✅ ${d.message}`); 
            closeEditModal(); 
            loadList(); 
        } else { 
            tg.showAlert('❌ ' + d.message); 
        } 
    } catch (e) { 
        tg.showAlert('❌ ' + e.message); 
    } 
}

async function confirmDelete() { 
    if (!confirm('Видалити товар зі списку?')) return; 
    
    try { 
        const r = await fetch('/api/delete', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({
                user_id: userId, 
                product_id: editingItem.product_id
            }) 
        }); 
        const d = await r.json(); 
        
        if (d.success) { 
            tg.showAlert(`✅ ${d.message}`); 
            closeEditModal(); 
            loadList(); 
        } else { 
            tg.showAlert('❌ ' + d.message); 
        } 
    } catch (e) { 
        tg.showAlert('❌ ' + e.message); 
    } 
}

// ===== LIST MANAGEMENT =====

async function saveList() { 
    try { 
        const r = await fetch(`/api/save/${userId}`, { method: 'POST' }); 
        const d = await r.json(); 
        
        if (d.success) { 
            tg.HapticFeedback.notificationOccurred('success'); 
            if (d.cleared) { 
                loadList(); 
                updateDepartmentInfo(null, 0); 
            } 
            document.getElementById('successModal').classList.add('active'); 
        } else { 
            tg.showAlert('❌ ' + d.message); 
        } 
    } catch (e) { 
        tg.showAlert('❌ ' + e.message); 
    } 
}

async function clearList() { 
    if (!confirm('Очистити весь список?')) return; 
    
    try { 
        const r = await fetch(`/api/clear/${userId}`, { method: 'POST' }); 
        const d = await r.json(); 
        
        if (d.success) { 
            tg.showAlert(`✅ ${d.message}`); 
            updateDepartmentInfo(null, 0); 
            loadList(); 
        } else { 
            tg.showAlert('❌ ' + d.message); 
        } 
    } catch (e) { 
        tg.showAlert('❌ ' + e.message); 
    } 
}

async function loadList() { 
    const el = document.getElementById('listContent'); 
    el.innerHTML = '<div class="loader">⏳ Завантаження...</div>'; 
    
    try { 
        const r = await fetch(`/api/list/${userId}`); 
        const d = await r.json(); 
        
        if (!d.items || d.items.length === 0) { 
            el.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div>Список порожній</div>'; 
            document.getElementById('totalBox').style.display = 'none'; 
            updateListBadge(0); 
            updateDepartmentInfo(null, 0); 
            return; 
        } 
        
        const deptR = await fetch(`/api/list/department/${userId}`); 
        const deptD = await deptR.json(); 
        updateDepartmentInfo(deptD.department, d.count); 
        
        let html = '<div class="action-buttons">';
        html += '<button class="save-btn" onclick="saveList()">💾 Зберегти</button>';
        html += '<button class="clear-btn" onclick="clearList()">🗑️ Очистити</button>';
        html += '</div>';
        
        html += d.items.map(item => 
            `<div class="list-item" onclick='openEditModal(${JSON.stringify(item)})'>
                <div class="list-header">
                    <strong>${item.article}</strong>
                    <span>${item.total.toFixed(2)} грн</span>
                </div>
                <div>${item.name}</div>
                <div style="margin-top:8px;color:var(--hint-color)">
                    ${item.quantity} шт. × ${item.price.toFixed(2)} грн
                </div>
            </div>`
        ).join(''); 
        
        el.innerHTML = html; 
        document.getElementById('totalSum').textContent = d.total.toFixed(2); 
        document.getElementById('totalItems').textContent = d.count; 
        document.getElementById('totalBox').style.display = 'flex'; 
        updateListBadge(d.count); 
    } catch (e) { 
        el.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка завантаження</div>'; 
        updateListBadge(0); 
        updateDepartmentInfo(null, 0); 
    } 
}

// ===== ARCHIVES =====

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

async function loadArchiveStats(filename) { 
    try { 
        const r = await fetch(`/api/archive/stats/${filename}?user_id=${userId}`); 
        const d = await r.json(); 
        
        if (d.success) { 
            return `<div class="stat-row"><span class="stat-label">📦 Товарів:</span><span class="stat-value">${d.items_count}</span></div>
                    <div class="stat-row"><span class="stat-label">🏢 Відділ:</span><span class="stat-value">${d.department}</span></div>
                    <div class="stat-row"><span class="stat-label">👤 Автор:</span><span class="stat-value">ID ${d.author_id}</span></div>`; 
        } 
        return ''; 
    } catch (e) { 
        return ''; 
    } 
}

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
        
        let html = `<button class="download-all-btn" onclick="downloadAllArchives()">
                        📦 Завантажити всі архіви (${d.archives.length})
                    </button>`;
        
        for (const a of d.archives) { 
            const stats = await loadArchiveStats(a.filename); 
            html += `<div class="archive-item">
                <div class="archive-header">
                    <strong>📄 ${a.date}</strong>
                    <span class="archive-badge ${a.is_surplus ? 'surplus' : 'main'}">${a.type}</span>
                </div>
                ${stats ? `<div class="archive-stats">${stats}</div>` : ''}
                <div class="archive-actions">
                    <button class="download-btn" onclick="downloadArchive('${a.filename}')">📥 Завантажити</button>
                    <button class="delete-archive-btn" onclick="deleteArchive('${a.filename}')">🗑️ Видалити</button>
                </div>
            </div>`; 
        } 
        el.innerHTML = html; 
    } catch (e) { 
        el.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка</div>'; 
    } 
}

function downloadAllArchives() {
    window.open(`/api/archives/download-all/${userId}`, '_blank');
    tg.HapticFeedback.notificationOccurred('success');
}

function downloadArchive(f) { 
    window.open(`/api/archive/download/${f}`, '_blank'); 
    tg.HapticFeedback.notificationOccurred('success'); 
}

async function deleteArchive(filename) { 
    if (!confirm(`Видалити файл "${filename}"?`)) return; 
    
    try { 
        const r = await fetch(`/api/archive/delete/${filename}?user_id=${userId}`, { 
            method: 'DELETE' 
        }); 
        const d = await r.json(); 
        
        if (d.success) { 
            tg.showAlert(`✅ ${d.message}`); 
            tg.HapticFeedback.notificationOccurred('success'); 
            loadArchives(); 
        } else { 
            tg.showAlert('❌ Помилка видалення'); 
        } 
    } catch (e) { 
        tg.showAlert('❌ Помилка: ' + e.message); 
    } 
}

// ===== ADMIN FUNCTIONS =====

async function loadAdminData() {
    if (!isAdmin) return;
    console.log('👑 Loading admin data...');
    await loadAdminStats();
    await loadAdminActiveUsers();
}

async function loadAdminStats() {
    const container = document.getElementById('adminStatsGrid');
    try {
        console.log('📊 Fetching admin statistics...');
        const response = await fetch(`/api/admin/statistics?user_id=${userId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data && data.success === false) throw new Error(data.message || data.error || 'Admin statistics error');
        console.log('📊 Stats data:', data);
        
        const productsResponse = await fetch(`/api/admin/products/info?user_id=${userId}`);
        const productsData = await productsResponse.json();
        cachedProductsInfo = productsData;
        
        const productsDisplay = productsData.success 
            ? `${productsData.current_articles} / ${productsData.original_articles}`
            : (data.total_products || 0);
        
        container.innerHTML = `
            <div class="admin-stat-card" style="cursor: pointer;" onclick="showAllUsers()">
                <div class="admin-stat-icon">👥</div>
                <div class="admin-stat-value">${data.total_users || 0}</div>
                <div class="admin-stat-label">Користувачів</div>
            </div>
            <div class="admin-stat-card success" style="cursor: pointer;" onclick="showActiveUsers()">
                <div class="admin-stat-icon">🔥</div>
                <div class="admin-stat-value">${data.active_users || 0}</div>
                <div class="admin-stat-label">Активних</div>
            </div>
            <div class="admin-stat-card warning" style="cursor: pointer;" onclick="showProductsInfo()">
                <div class="admin-stat-icon">📦</div>
                <div class="admin-stat-value">${productsDisplay}</div>
                <div class="admin-stat-label">Товарів</div>
            </div>
            <div class="admin-stat-card danger" style="cursor: pointer;" onclick="showReservedByDepartment()">
                <div class="admin-stat-icon">💰</div>
                <div class="admin-stat-value">${(data.total_reserved_sum || 0).toLocaleString('uk-UA')} ₴</div>
                <div class="admin-stat-label">Зарезервовано</div>
            </div>
        `;
    } catch (error) {
        console.error('❌ Error loading admin stats:', error);
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка завантаження</div>';
    }
}

async function loadAdminActiveUsers() {
    try {
        console.log('👥 Fetching active users...');
        const response = await fetch(`/api/admin/users/active?user_id=${userId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data && data.success === false) throw new Error(data.message || data.error || 'Active users error');
        console.log('👥 Active users data:', data);
        
        const container = document.getElementById('adminActiveUsers');
        
        if (!data.users || data.users.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">👥</div>Немає активних списків</div>';
            return;
        }
        
        container.innerHTML = data.users.map(user => `
            <div class="user-item">
                <div class="user-info">
                    <div class="user-name">👤 ${user.username || 'User ' + user.user_id}</div>
                    <div class="user-details">
                        🏢 ${user.department || '-'} • 📦 ${user.items_count} • 💰 ${(user.total_sum || 0).toLocaleString('uk-UA')} ₴
                    </div>
                </div>
                <button class="btn btn-success" style="flex: 0 0 auto; padding: 8px 16px; font-size: 12px;" onclick="forceSave(${user.user_id})">
                    💾 Зберегти
                </button>
            </div>
        `).join('');
    } catch (error) {
        console.error('❌ Error loading active users:', error);
        document.getElementById('adminActiveUsers').innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка завантаження</div>';
    }
}

async function forceSave(targetUserId) {
    if (!confirm(`Примусово зберегти список користувача ${targetUserId}?`)) return;
    
    try {
        const response = await fetch(`/api/admin/force-save/${targetUserId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: userId })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        
        if (data.success) {
            tg.showAlert('✅ ' + data.message);
            loadAdminActiveUsers();
        } else {
            tg.showAlert('❌ ' + (data.message || 'Помилка збереження'));
        }
    } catch (error) {
        tg.showAlert('❌ Помилка: ' + error.message);
    }
}

// ===== FILE UPLOAD =====

const dropZone = document.getElementById('dropZone');

if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--button-color)';
        dropZone.style.background = 'rgba(0,136,204,0.1)';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--hint-color)';
        dropZone.style.background = '';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--hint-color)';
        dropZone.style.background = '';
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            selectedFile = files[0];
            updateFileInfo();
        }
    });
}

function handleFileSelect(event) {
    selectedFile = event.target.files[0];
    updateFileInfo();
}

function updateFileInfo() {
    if (selectedFile) {
        document.getElementById('fileInfo').textContent = `📄 ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(2)} KB)`;
        document.getElementById('fileInfo').style.display = 'block';
        document.getElementById('uploadBtn').disabled = false;
    }
}

function cancelUpload(clearAlert = false) {
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('uploadBtn').disabled = true;
    if (clearAlert) {
        document.getElementById('importAlert').innerHTML = '';
    }
}

async function uploadFile() {
    if (!selectedFile) {
        tg.showAlert('❌ Оберіть файл для завантаження');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    const notifyChecked = document.getElementById('notifyUsers').checked;
    
    document.getElementById('uploadBtn').disabled = true;
    document.getElementById('uploadBtn').textContent = '⏳ Завантаження...';
    
    try {
        const response = await fetch(`/api/admin/import?user_id=${userId}&notify_users=${notifyChecked}`, {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        
        if (data.success || data.added !== undefined) {
            document.getElementById('importAlert').innerHTML = `
                <div class="alert alert-success">
                    <span style="font-size: 20px;">✅</span>
                    <div>Імпорт успішний<br><small>Додано: ${data.added || 0}, Оновлено: ${data.updated || 0}, Деактивовано: ${data.deactivated || 0}</small></div>
                </div>
            `;
            selectedFile = null;
            document.getElementById('fileInput').value = '';
            document.getElementById('fileInfo').style.display = 'none';
            document.getElementById('uploadBtn').disabled = true;
            loadAdminStats();
        } else {
            document.getElementById('importAlert').innerHTML = `
                <div class="alert alert-error">
                    <span style="font-size: 20px;">❌</span>
                    <div>${data.error || data.message || 'Помилка імпорту'}</div>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('importAlert').innerHTML = `
            <div class="alert alert-error">
                <span style="font-size: 20px;">❌</span>
                <div>Помилка: ${error.message}</div>
            </div>
        `;
    } finally {
        document.getElementById('uploadBtn').disabled = false;
        document.getElementById('uploadBtn').textContent = '📤 Імпортувати';
    }
}

async function exportStock() {
    try {
        window.open(`/api/admin/export/stock?user_id=${userId}`, '_blank');
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        tg.showAlert('❌ Помилка експорту: ' + error.message);
    }
}

// ===== ADMIN MODALS =====

async function showAdminArchives() {
    try {
        const response = await fetch(`/api/admin/archives?user_id=${userId}`);
        const data = await response.json();
        
        if (data.success && data.files && data.files.length > 0) {
            let html = '<h2 style="margin-bottom: 16px;">🗄 Архіви користувачів</h2>';
            html += '<button class="btn btn-primary" style="width: 100%; margin-bottom: 16px;" onclick="downloadAllAdminArchives(); closeAdminArchivesModal();">📥 Завантажити всі (ZIP)</button>';
            html += '<div style="max-height: 400px; overflow-y: auto;">';
            data.files.forEach(file => {
                html += `<div style="background: var(--secondary-bg-color); padding: 12px; margin-bottom: 8px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">`;
                html += `<div><div style="font-weight: 600;">📄 ${file.filename}</div><div style="font-size: 12px; color: var(--hint-color);">${(file.size / 1024).toFixed(1)} KB | ${file.modified}</div></div>`;
                html += `<button class="btn btn-primary" style="padding: 6px 12px; font-size: 12px; min-width: auto;" onclick="downloadAdminArchive('${file.filename}')">📥</button></div>`;
            });
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeAdminArchivesModal()">Закрити</button>';
            
            document.getElementById('adminArchivesModalContent').innerHTML = html;
            document.getElementById('adminArchivesModal').classList.add('active');
        } else {
            tg.showAlert('📁 Немає архівів');
        }
    } catch (error) {
        tg.showAlert('❌ Помилка: ' + error.message);
    }
}

async function showAllUsers() {
    try {
        const response = await fetch(`/api/admin/users/all?user_id=${userId}`);
        const data = await response.json();
        
        if (data.success && data.users && data.users.length > 0) {
            let html = '<h2 style="margin-bottom: 16px;">👥 Всі користувачі</h2>';
            html += '<div style="max-height: 450px; overflow-y: auto;">';
            data.users.forEach(user => {
                html += `<div style="background: var(--secondary-bg-color); padding: 12px; margin-bottom: 8px; border-radius: 8px;">`;
                html += `<div style="font-weight: 600;">👤 ID: ${user.user_id}${user.username ? ' (@' + user.username + ')' : ''}</div>`;
                html += `<div style="font-size: 12px; color: var(--hint-color); margin-top: 4px;">`;
                html += `📁 Архівів: ${user.archives_count || 0} | 💰 Сума: ${(user.total_amount || 0).toLocaleString('uk-UA')} ₴`;
                if (user.last_activity) html += ` | 🕐 ${user.last_activity}`;
                html += `</div></div>`;
            });
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeStatsModal()">Закрити</button>';
            
            document.getElementById('statsModalContent').innerHTML = html;
            document.getElementById('statsModal').classList.add('active');
        } else {
            tg.showAlert('📁 Немає користувачів');
        }
    } catch (error) {
        tg.showAlert('❌ Помилка: ' + error.message);
    }
}

async function showActiveUsers() {
    try {
        const response = await fetch(`/api/admin/users/active?user_id=${userId}`);
        const data = await response.json();
        
        if (data.success && data.users && data.users.length > 0) {
            let html = '<h2 style="margin-bottom: 16px;">🔥 Активні користувачі</h2>';
            html += '<div style="max-height: 450px; overflow-y: auto;">';
            data.users.forEach(user => {
                html += `<div style="background: var(--secondary-bg-color); padding: 12px; margin-bottom: 8px; border-radius: 8px;">`;
                html += `<div style="font-weight: 600;">👤 ${user.username || 'User ' + user.user_id}</div>`;
                html += `<div style="font-size: 12px; color: var(--hint-color); margin-top: 4px;">`;
                html += `🏢 ${user.department || '-'} | 📦 ${user.items_count} товарів | 💰 ${(user.total_sum || 0).toLocaleString('uk-UA')} ₴`;
                html += `</div></div>`;
            });
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeStatsModal()">Закрити</button>';
            
            document.getElementById('statsModalContent').innerHTML = html;
            document.getElementById('statsModal').classList.add('active');
        } else {
            tg.showAlert('📁 Немає активних користувачів');
        }
    } catch (error) {
        tg.showAlert('❌ Помилка: ' + error.message);
    }
}

async function showProductsInfo() {
    try {
        let data = cachedProductsInfo;
        if (!data) {
            const response = await fetch(`/api/admin/products/info?user_id=${userId}`);
            data = await response.json();
            cachedProductsInfo = data;
        }
        
        if (data.success) {
            let html = '<h2 style="margin-bottom: 8px;">📦 Інформація про товари</h2>';
            if (data.last_import) {
                html += `<div style="padding: 10px; background: rgba(52,199,89,0.1); border-radius: 8px; margin-bottom: 12px; font-size: 13px;">`;
                html += `✅ Базу оновлено ${data.last_import}`;
                html += `</div>`;
            }
            
            html += `<div style="padding: 14px; background: linear-gradient(135deg, rgba(255,152,0,0.15) 0%, rgba(255,204,0,0.15) 100%); border-radius: 10px; margin-bottom: 14px;">`;
            html += `<div style="text-align: center; font-size: 15px; font-weight: 600; margin-bottom: 10px;">📊 Було / Стало</div>`;
            html += `<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; text-align: center;">`;
            html += `<div><div style="font-size: 22px; font-weight: 700; color: #ff9500;">${data.original_articles || 0}</div><div style="font-size: 11px; opacity: 0.7;">Було артикулів</div></div>`;
            html += `<div><div style="font-size: 22px; font-weight: 700; color: #34c759;">→</div><div style="font-size: 11px; opacity: 0.7;">Зібрано</div></div>`;
            html += `<div><div style="font-size: 22px; font-weight: 700; color: #0088cc;">${data.current_articles || 0}</div><div style="font-size: 11px; opacity: 0.7;">Залишилось</div></div>`;
            html += `</div></div>`;
            
            html += `<div style="padding: 12px; background: var(--secondary-bg-color); border-radius: 8px; margin-bottom: 12px;">`;
            html += `<div style="font-weight: 600; margin-bottom: 8px;">💰 Суми:</div>`;
            html += `<div style="font-size: 13px; line-height: 1.6;">`;
            html += `📌 Було: <strong>${(data.original_sum || 0).toLocaleString('uk-UA')} грн</strong><br>`;
            html += `🛒 Зібрано: <strong style="color: #ff9500;">${(data.collected_sum || 0).toLocaleString('uk-UA')} грн</strong> (${data.collected_articles || 0} арт.)<br>`;
            html += `✅ Залишилось: <strong style="color: #34c759;">${(data.current_sum || 0).toLocaleString('uk-UA')} грн</strong>`;
            html += `</div></div>`;
            
            html += '<div style="font-weight: 600; margin-bottom: 8px;">📦 По відділах (було → стало):</div>';
            html += '<div style="max-height: 300px; overflow-y: auto;">';
            if (data.departments && data.departments.length > 0) {
                data.departments.forEach(dept => {
                    const wasCollected = (dept.original_count || 0) - (dept.current_count || 0);
                    const collectedPercent = dept.original_count > 0 ? Math.round((wasCollected / dept.original_count) * 100) : 0;
                    html += `<div style="padding: 10px 12px; background: var(--secondary-bg-color); margin-bottom: 6px; border-radius: 6px;">`;
                    html += `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">`;
                    html += `<span style="font-weight: 600;">🏢 Відділ ${dept.department}</span>`;
                    html += `<span style="font-weight: 600; color: var(--button-color);">${dept.original_count || 0} → ${dept.current_count || 0}</span>`;
                    html += `</div>`;
                    if (wasCollected > 0) {
                        html += `<div style="font-size: 12px; color: var(--hint-color);">`;
                        html += `🛒 Зібрано: ${wasCollected} арт. (${collectedPercent}%)`;
                        html += `</div>`;
                    }
                    html += `</div>`;
                });
            }
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeStatsModal()">Закрити</button>';
            
            document.getElementById('statsModalContent').innerHTML = html;
            document.getElementById('statsModal').classList.add('active');
        } else {
            tg.showAlert('📁 Немає даних');
        }
    } catch (error) {
        tg.showAlert('❌ Помилка: ' + error.message);
    }
}

async function showReservedByDepartment() {
    try {
        const response = await fetch(`/api/admin/reserved/by-department?user_id=${userId}`);
        const data = await response.json();
        
        if (data.success && data.departments && data.departments.length > 0) {
            let html = '<h2 style="margin-bottom: 16px;">💰 Резерви по відділах</h2>';
            html += '<div style="max-height: 450px; overflow-y: auto;">';
            const total = data.departments.reduce((sum, d) => sum + (d.reserved_sum || 0), 0);
            data.departments.forEach(dept => {
                const percent = total > 0 ? ((dept.reserved_sum / total) * 100).toFixed(1) : 0;
                html += `<div style="background: var(--secondary-bg-color); padding: 12px; margin-bottom: 8px; border-radius: 8px;">`;
                html += `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">`;
                html += `<div style="font-weight: 600;">🏢 Відділ ${dept.department}</div>`;
                html += `<div style="font-weight: 600; color: var(--button-color);">${(dept.reserved_sum || 0).toLocaleString('uk-UA')} ₴</div>`;
                html += `</div>`;
                html += `<div style="background: var(--hint-color); height: 6px; border-radius: 3px; overflow: hidden;">`;
                html += `<div style="background: var(--button-color); width: ${percent}%; height: 100%;"></div>`;
                html += `</div>`;
                html += `<div style="font-size: 12px; color: var(--hint-color); margin-top: 4px;">`;
                html += `📦 ${dept.products_count || 0} товарів | 👥 ${dept.users_count || 0} користувачів | ${percent}%`;
                html += `</div></div>`;
            });
            html += '</div>';
            html += '<button class="add-btn cancel-btn" style="margin-top: 16px;" onclick="closeStatsModal()">Закрити</button>';
            
            document.getElementById('statsModalContent').innerHTML = html;
            document.getElementById('statsModal').classList.add('active');
        } else {
            tg.showAlert('📁 Немає резервів');
        }
    } catch (error) {
        tg.showAlert('❌ Помилка: ' + error.message);
    }
}

function closeStatsModal() {
    document.getElementById('statsModal').classList.remove('active');
}

function closeAdminArchivesModal() {
    document.getElementById('adminArchivesModal').classList.remove('active');
}

function downloadAdminArchive(filename) {
    window.open(`/api/admin/archives/download/${filename}?user_id=${userId}`, '_blank');
    tg.HapticFeedback.notificationOccurred('success');
}

function downloadAllAdminArchives() {
    window.open(`/api/admin/archives/download-all?user_id=${userId}`, '_blank');
    tg.HapticFeedback.notificationOccurred('success');
}

// ===== BROADCAST =====

async function sendBroadcast() {
    const message = document.getElementById('broadcastMessage').value.trim();
    
    if (!message) {
        tg.showAlert('❌ Введіть текст повідомлення');
        return;
    }
    
    if (!confirm(`Розіслати повідомлення всім користувачам?\n\nТекст: "${message}"`)) return;
    
    try {
        const response = await fetch(`/api/admin/broadcast?user_id=${userId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: userId,
                message: message
            })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('broadcastAlert').innerHTML = `
                <div class="alert alert-success">
                    <span style="font-size: 20px;">✅</span>
                    <div>${data.message || 'Розсилка завершена'}<br><small>Розіслано: ${data.sent || 0} користувачам</small></div>
                </div>
            `;
            document.getElementById('broadcastMessage').value = '';
        } else {
            document.getElementById('broadcastAlert').innerHTML = `
                <div class="alert alert-error">
                    <span style="font-size: 20px;">❌</span>
                    <div>${data.message || 'Помилка розсилки'}</div>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('broadcastAlert').innerHTML = `
            <div class="alert alert-error">
                <span style="font-size: 20px;">❌</span>
                <div>Помилка: ${error.message}</div>
            </div>
        `;
    }
}

// ===== INITIALIZATION =====

if (userId) loadList();
updateSearchBoxVisibility();

// Debug info
console.log('App initialized:', { userId, isAdmin, ADMIN_IDS });
console.log('🚀 PWA Ready!');
console.log('📱 Display mode:', 
  window.matchMedia('(display-mode: standalone)').matches ? 'Standalone (PWA)' : 'Browser'
);