/* =============================================
   SEARCH.JS - Пошук товарів та рендеринг
   ============================================= */

// Search products
async function search(query) {
    const results = document.getElementById('searchResults');
    results.innerHTML = '<div class="loader">🔍 Пошук...</div>';
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query, user_id: AppState.userId})
        });
        
        const data = await response.json();
        
        if (!data.products || data.products.length === 0) {
            results.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено</div>';
            AppState.cachedProducts = [];
            return;
        }
        
        AppState.cachedProducts = data.products.filter(p => p.available > 0);
        updateSearchResults();
    } catch (error) {
        results.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка пошуку</div>';
        AppState.cachedProducts = [];
        console.error('Search error:', error);
    }
}

// Update search results display
function updateSearchResults() {
    const results = document.getElementById('searchResults');
    const visibleProducts = AppState.cachedProducts.filter(p => p.available > 0);
    
    if (visibleProducts.length === 0) {
        results.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено або все зарезервовано</div>';
        return;
    }
    
    results.innerHTML = visibleProducts.map(p => renderProduct(p)).join('');
}

// Render single product card
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
            <div class="product-detail-row"><span class="product-detail-label">🏮 Відділ:</span><span class="product-detail-value">${p.department}</span></div>
            <div class="product-detail-row"><span class="product-detail-label">📂 Група:</span><span class="product-detail-value">${p.group}</span></div>
            <div class="product-detail-row"><span class="product-detail-label">⌛ Без руху (міс):</span><span class="product-detail-value ${p.months_without_movement > 3 ? 'warning' : ''}">${p.months_without_movement}</span></div>
            <div class="product-detail-row"><span class="product-detail-label">💰 Сума залишку:</span><span class="product-detail-value highlight">${p.balance_sum.toFixed(2)} грн</span></div>
            <div class="product-detail-row"><span class="product-detail-label">📦 Доступно:</span><span class="product-detail-value success">${p.available}</span></div>
            ${p.user_reserved > 0 ? `<div class="product-detail-row"><span class="product-detail-label">🛍️ В резерві:</span><span class="product-detail-value warning">${p.user_reserved} (${p.user_reserved_sum.toFixed(2)} грн)</span></div>` : ''}
        </div>
    </div>`;
}

// Show locked product alert
function showLockedAlert(dept) {
    if (window.tg) {
        window.tg.showAlert(`🔒 Цей товар з іншого відділу.\n\nПоточний список для відділу ${dept}.\nЗбережіть або очистіть список щоб почати новий.`);
    }
}

// Initialize search input listener
function initSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(AppState.searchTimeout);
            const query = e.target.value.trim();
            
            if (query.length < 2) {
                document.getElementById('searchResults').innerHTML = '';
                AppState.cachedProducts = [];
                return;
            }
            
            AppState.searchTimeout = setTimeout(() => search(query), 500);
        });
    }
}

// Export functions
window.search = search;
window.updateSearchResults = updateSearchResults;
window.renderProduct = renderProduct;
window.showLockedAlert = showLockedAlert;
window.initSearch = initSearch;