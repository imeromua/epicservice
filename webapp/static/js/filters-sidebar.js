// 🎛️ Filters Sidebar Component
// Бокова панель з фільтрами для товарів

let filterState = {
    departments: [],
    sortBy: 'balance_sum',
    offset: 0,
    limit: 500,  // ✅ Збільшено з 50 до 500
    isActive: false,
    hasMore: false,
    isLoading: false,
    totalAvailable: 0,
    availableDepartments: []
};

let filteredProducts = [];
let filterStats = null;

// Створення HTML бокової панелі
function createFiltersSidebar() {
    const sidebar = document.createElement('div');
    sidebar.id = 'filtersSidebar';
    sidebar.className = 'filters-sidebar';
    sidebar.innerHTML = `
        <div class="filters-header">
            <h3>🎛️ Фільтри</h3>
            <button class="close-filters-btn" onclick="closeFiltersSidebar()">✕</button>
        </div>
        
        <div class="filters-content">
            <div class="filter-section">
                <div class="filter-section-title">🏢 Відділи</div>
                <div id="departmentCheckboxes" class="department-checkboxes">
                    <div class="loader" style="padding: 12px; text-align: center; color: var(--hint-color);">⏳ Завантаження...</div>
                </div>
            </div>
            
            <div class="filter-section">
                <div class="filter-section-title">📊 Сортування</div>
                <div class="sort-buttons">
                    <button class="sort-btn active" data-sort="balance_sum" onclick="setSortBy('balance_sum')">
                        💰 Сума залишку
                    </button>
                    <button class="sort-btn" data-sort="months_without_movement" onclick="setSortBy('months_without_movement')">
                        ⏳ Місяці без руху
                    </button>
                    <button class="sort-btn" data-sort="quantity" onclick="setSortBy('quantity')">
                        📦 Кількість
                    </button>
                    <button class="sort-btn" data-sort="article" onclick="setSortBy('article')">
                        🆔 Артикул
                    </button>
                </div>
            </div>
            
            <div id="filterStatsBox" class="filter-stats" style="display: none;">
                <div class="stat-row">
                    <span>📊 Знайдено:</span>
                    <span id="filterStatsCount">0</span>
                </div>
                <div class="stat-row">
                    <span>💰 Загальна сума:</span>
                    <span id="filterStatsSum">0 грн</span>
                </div>
                <div class="stat-row">
                    <span>📦 Загальна кількість:</span>
                    <span id="filterStatsQty">0</span>
                </div>
            </div>
        </div>
        
        <div class="filters-footer">
            <button class="apply-filters-btn" onclick="applyFilters()">✅ Застосувати</button>
            <button class="reset-filters-btn" onclick="resetFilters()">🔄 Скинути</button>
        </div>
    `;
    
    document.body.appendChild(sidebar);
    
    // Створюємо overlay
    const overlay = document.createElement('div');
    overlay.id = 'filtersOverlay';
    overlay.className = 'filters-overlay';
    overlay.onclick = closeFiltersSidebar;
    document.body.appendChild(overlay);
    
    // Створюємо floating button
    const floatingBtn = document.createElement('button');
    floatingBtn.id = 'filtersFloatingBtn';
    floatingBtn.className = 'filters-floating-btn';
    floatingBtn.innerHTML = '🎛️';
    floatingBtn.onclick = openFiltersSidebar;
    document.body.appendChild(floatingBtn);
    
    // Завантажуємо відділи
    loadDepartments();
    
    // Встановлюємо початкову видимість кнопки
    setTimeout(() => {
        updateFiltersButtonVisibility();
    }, 100);
    
    // 🎯 INFINITE SCROLL для фільтрів з debounce
    const debouncedFiltersScroll = Utils.debounce(handleFiltersScroll, 200);
    window.addEventListener('scroll', debouncedFiltersScroll);
}

async function loadDepartments() {
    try {
        const response = await fetch('/api/products/departments');
        const data = await response.json();
        
        if (data.departments && data.departments.length > 0) {
            filterState.availableDepartments = data.departments;
            renderDepartmentCheckboxes(data.departments);
        }
    } catch (error) {
        console.error('❌ Error loading departments:', error);
        document.getElementById('departmentCheckboxes').innerHTML = '<div class="empty-state" style="padding: 12px; text-align: center; color: var(--hint-color);">❌ Помилка завантаження</div>';
    }
}

function renderDepartmentCheckboxes(departments) {
    const container = document.getElementById('departmentCheckboxes');
    
    container.innerHTML = departments.map(dept => `
        <label class="department-checkbox">
            <input type="checkbox" 
                   value="${dept.department}" 
                   onchange="toggleDepartment('${dept.department}')">
            <span class="checkbox-label">
                🏢 ${dept.department}
                <span class="dept-count">(${dept.count})</span>
            </span>
        </label>
    `).join('');
}

function toggleDepartment(dept) {
    const index = filterState.departments.indexOf(dept);
    
    if (index > -1) {
        filterState.departments.splice(index, 1);
    } else {
        filterState.departments.push(dept);
    }
    
    console.log('🎛️ Selected departments:', filterState.departments);
}

function setSortBy(sortBy) {
    filterState.sortBy = sortBy;
    
    // Оновлюємо active стан кнопок
    document.querySelectorAll('.sort-btn').forEach(btn => {
        if (btn.dataset.sort === sortBy) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    console.log('📊 Sort by:', sortBy);
}

async function applyFilters() {
    filterState.isActive = true;
    filterState.offset = 0;
    filteredProducts = [];
    
    await loadFilteredProducts(true);
    
    closeFiltersSidebar();
}

async function loadFilteredProducts(isNewFilter = false) {
    if (filterState.isLoading) {
        console.log('⏸️ Already loading filters, skipping...');
        return;
    }
    if (!isNewFilter && !filterState.hasMore) {
        console.log('⛔ No more filtered products');
        return;
    }
    
    filterState.isLoading = true;
    
    const resultsContainer = document.getElementById('searchResults');
    if (isNewFilter && resultsContainer) {
        resultsContainer.innerHTML = '<div class="loader" style="text-align:center; padding:20px;">⏳ Фільтруємо...</div>';
    } else {
        showFiltersLoadingIndicator();
    }
    
    try {
        console.log(`🎛️ Filter request: offset=${filterState.offset}, limit=${filterState.limit}`);
        
        const response = await fetch('/api/products/filter', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: userId,
                departments: filterState.departments,
                sort_by: filterState.sortBy,
                offset: filterState.offset,
                limit: filterState.limit
            })
        });
        
        const data = await response.json();
        
        if (data.products) {
            const newProducts = data.products || [];
            filterState.totalAvailable = data.total || 0;
            
            console.log(`✅ Got ${newProducts.length} filtered products, total=${data.total}`);
            
            // Перевіряємо чи є ще товари
            filterState.hasMore = (filterState.offset + newProducts.length) < filterState.totalAvailable;
            filterState.offset += newProducts.length;
            
            if (isNewFilter) {
                filteredProducts = newProducts;
                filterStats = data.statistics;
                updateFilterStats(data.statistics);
            } else {
                filteredProducts = [...filteredProducts, ...newProducts];
            }
            
            displayFilteredProducts(filteredProducts, isNewFilter);
            
            if (isNewFilter && window.Telegram?.WebApp?.HapticFeedback) {
                window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
            }
            
            console.log(`📊 Total loaded: ${filteredProducts.length}/${filterState.totalAvailable}, hasMore=${filterState.hasMore}`);
        }
    } catch (error) {
        console.error('❌ Error applying filters:', error);
        if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.showAlert('❌ Помилка застосування фільтрів');
        }
    } finally {
        filterState.isLoading = false;
        hideFiltersLoadingIndicator();
    }
}

// 🎯 SCROLL LISTENER для infinite scroll фільтрів
function handleFiltersScroll() {
    // Працює тільки коли фільтри активні
    if (!filterState.isActive || filterState.isLoading || !filterState.hasMore) return;
    if (window.currentTab !== 'search') return;
    
    const scrollPercentage = (window.scrollY + window.innerHeight) / document.documentElement.scrollHeight;
    
    // Завантажуємо коли доскролили до 85%
    if (scrollPercentage > 0.85) {
        console.log('📜 Filters scroll 85% reached, loading more...');
        loadFilteredProducts(false);
    }
}

function showFiltersLoadingIndicator() {
    const resultsContainer = document.getElementById('searchResults');
    if (!resultsContainer) return;
    
    const oldLoader = document.getElementById('filtersLoadingMore');
    if (oldLoader) oldLoader.remove();
    
    const loader = document.createElement('div');
    loader.id = 'filtersLoadingMore';
    loader.style.cssText = 'text-align:center; padding:20px; color:var(--hint-color);';
    loader.innerHTML = '⏳ Завантаження...';
    resultsContainer.appendChild(loader);
}

function hideFiltersLoadingIndicator() {
    const loader = document.getElementById('filtersLoadingMore');
    if (loader) loader.remove();
}

function updateFilterStats(stats) {
    if (!stats) return;
    
    document.getElementById('filterStatsCount').textContent = stats.total_articles || 0;
    document.getElementById('filterStatsSum').textContent = (stats.total_sum || 0).toLocaleString('uk-UA') + ' грн';
    document.getElementById('filterStatsQty').textContent = Math.floor(stats.total_quantity || 0);
    document.getElementById('filterStatsBox').style.display = 'block';
}

function displayFilteredProducts(products, isNewFilter = false) {
    const resultsContainer = document.getElementById('searchResults');
    
    if (!products || products.length === 0) {
        resultsContainer.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено за цими фільтрами</div>';
        return;
    }
    
    // ✅ ФІЛЬТРУЄМО ТІЛЬКИ ДОСТУПНІ ТОВАРИ (available > 0)
    const availableProducts = products.filter(p => p.available > 0);
    
    if (availableProducts.length === 0) {
        resultsContainer.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Всі товари зарезервовані або закінчились</div>';
        return;
    }
    
    // Оновлюємо cachedProducts для сумісності з існуючим renderProduct
    if (typeof window.cachedProducts !== 'undefined') {
        window.cachedProducts = availableProducts;
    }
    
    // Використовуємо існуючу функцію renderProduct з index.html
    if (typeof window.renderProduct === 'function') {
        if (isNewFilter) {
            resultsContainer.innerHTML = availableProducts.map(p => window.renderProduct(p)).join('');
        } else {
            // Додаємо нові товари без перемальовування всього
            const existingCount = resultsContainer.querySelectorAll('.product-card').length;
            const newProductsHtml = availableProducts.slice(existingCount).map(p => window.renderProduct(p)).join('');
            resultsContainer.insertAdjacentHTML('beforeend', newProductsHtml);
        }
    } else {
        // Fallback рендер
        const html = availableProducts.map(p => `
            <div class="product-card" data-product-id="${p.id}" onclick="openAddModalById(${p.id})">
                <div class="product-header">
                    <span class="product-article">🆔 ${p.article}</span>
                    <span class="product-status">✅ Знайдено</span>
                </div>
                <div class="product-name">📝 ${p.name}</div>
                <div class="product-details">
                    <div class="product-detail-row"><span class="product-detail-label">🏢 Відділ:</span><span class="product-detail-value">${p.department}</span></div>
                    <div class="product-detail-row"><span class="product-detail-label">📊 Сума залишку:</span><span class="product-detail-value highlight">${p.balance_sum.toFixed(2)} грн</span></div>
                    <div class="product-detail-row"><span class="product-detail-label">📦 Доступно:</span><span class="product-detail-value success">${p.available}</span></div>
                </div>
            </div>
        `).join('');
        
        if (isNewFilter) {
            resultsContainer.innerHTML = html;
        } else {
            resultsContainer.insertAdjacentHTML('beforeend', html);
        }
    }
    
    // Прокручуємо вгору тільки при новому фільтрі
    if (isNewFilter) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function resetFilters() {
    filterState.departments = [];
    filterState.sortBy = 'balance_sum';
    filterState.offset = 0;
    filterState.isActive = false;
    filterState.hasMore = false;
    filterState.totalAvailable = 0;
    
    filteredProducts = [];
    
    // Скидаємо всі чекбокси
    document.querySelectorAll('#departmentCheckboxes input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
    
    // Відновлюємо active стан сортування
    setSortBy('balance_sum');
    
    // Ховаємо статистику
    document.getElementById('filterStatsBox').style.display = 'none';
    
    // Очищуємо результати
    document.getElementById('searchResults').innerHTML = '';
    
    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
    
    console.log('🔄 Filters reset');
}

function openFiltersSidebar() {
    const sidebar = document.getElementById('filtersSidebar');
    const overlay = document.getElementById('filtersOverlay');
    const floatingBtn = document.getElementById('filtersFloatingBtn');
    
    if (sidebar && overlay) {
        sidebar.classList.add('active');
        overlay.classList.add('active');
        floatingBtn.style.display = 'none';
        
        // Haptic feedback
        if (window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
        }
    }
}

function closeFiltersSidebar() {
    const sidebar = document.getElementById('filtersSidebar');
    const overlay = document.getElementById('filtersOverlay');
    const floatingBtn = document.getElementById('filtersFloatingBtn');
    
    if (sidebar && overlay) {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
        
        // Показуємо floating button після закриття анімації тільки якщо на вкладці Пошук
        setTimeout(() => {
            updateFiltersButtonVisibility();
        }, 300);
    }
}

// Показ/ховаємо floating button в залежності від табу
function updateFiltersButtonVisibility() {
    const floatingBtn = document.getElementById('filtersFloatingBtn');
    
    if (floatingBtn) {
        // Перевіряємо глобальну змінну currentTab
        if (typeof window.currentTab !== 'undefined') {
            if (window.currentTab === 'search') {
                floatingBtn.style.display = 'flex';
            } else {
                floatingBtn.style.display = 'none';
            }
        } else {
            // Якщо currentTab ще не визначений, показуємо тільки якщо активна вкладка "Пошук"
            const activeTab = document.querySelector('.tab.active');
            if (activeTab && activeTab.textContent.includes('Пошук')) {
                floatingBtn.style.display = 'flex';
            } else {
                floatingBtn.style.display = 'none';
            }
        }
    }
}

// Ініціалізація при завантаженні сторінки
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createFiltersSidebar);
} else {
    createFiltersSidebar();
}

// Export functions for global access
if (typeof window !== 'undefined') {
    window.openFiltersSidebar = openFiltersSidebar;
    window.closeFiltersSidebar = closeFiltersSidebar;
    window.toggleDepartment = toggleDepartment;
    window.setSortBy = setSortBy;
    window.applyFilters = applyFilters;
    window.resetFilters = resetFilters;
    window.updateFiltersButtonVisibility = updateFiltersButtonVisibility;
    window.filterState = filterState;
}

console.log('🎛️ Filters sidebar with debounced infinite scroll loaded');

function openAddModalById(id) {
    const p = cachedProducts && cachedProducts.find(x => x.id === id);
    if (p) openAddModal(p);
    else console.error('Product not found in cache for id:', id);
}
