// 🎛️ Filters Sidebar Component
// Бокова панель з фільтрами для товарів

let filterState = {
    departments: [],
    sortBy: 'balance_sum',
    offset: 0,
    limit: 20,
    isActive: false,
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
    try {
        filterState.isActive = true;
        filterState.offset = 0;
        
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
            filteredProducts = data.products;
            filterStats = data.statistics;
            
            // Показуємо статистику
            updateFilterStats(data.statistics);
            
            // Оновлюємо результати пошуку
            displayFilteredProducts(data.products);
            
            // Закриваємо панель
            closeFiltersSidebar();
            
            // Haptic feedback
            if (window.Telegram?.WebApp?.HapticFeedback) {
                window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
            }
            
            console.log('✅ Filters applied:', data.statistics);
        }
    } catch (error) {
        console.error('❌ Error applying filters:', error);
        if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.showAlert('❌ Помилка застосування фільтрів');
        }
    }
}

function updateFilterStats(stats) {
    if (!stats) return;
    
    document.getElementById('filterStatsCount').textContent = stats.total_articles || 0;
    document.getElementById('filterStatsSum').textContent = (stats.total_sum || 0).toLocaleString('uk-UA') + ' грн';
    document.getElementById('filterStatsQty').textContent = Math.floor(stats.total_quantity || 0);
    document.getElementById('filterStatsBox').style.display = 'block';
}

function displayFilteredProducts(products) {
    const resultsContainer = document.getElementById('searchResults');
    
    if (!products || products.length === 0) {
        resultsContainer.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено за цими фільтрами</div>';
        return;
    }
    
    // Оновлюємо cachedProducts для сумісності з існуючим renderProduct
    if (typeof window.cachedProducts !== 'undefined') {
        window.cachedProducts = products;
    }
    
    // Використовуємо існуючу функцію renderProduct з index.html
    if (typeof window.renderProduct === 'function') {
        resultsContainer.innerHTML = products.map(p => window.renderProduct(p)).join('');
    } else {
        // Fallback рендер
        resultsContainer.innerHTML = products.map(p => `
            <div class="product-card" onclick='openAddModal(${JSON.stringify(p).replace(/'/g, "&#39;")})'>
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
    }
    
    // Прокручуємо вгору
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function resetFilters() {
    filterState.departments = [];
    filterState.sortBy = 'balance_sum';
    filterState.offset = 0;
    filterState.isActive = false;
    
    // Скидаємо всі чекбокси
    document.querySelectorAll('#departmentCheckboxes input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
    
    // Відновлюємо active стан сортування
    setSortBy('balance_sum');
    
    // Ховаємо статистику
    document.getElementById('filterStatsBox').style.display = 'none';
    
    // Очищаємо результати
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
        
        // Показуємо floating button після закриття анімації
        setTimeout(() => {
            const currentTab = document.querySelector('.tab.active')?.textContent?.includes('Пошук');
            if (currentTab) {
                floatingBtn.style.display = 'flex';
            }
        }, 300);
    }
}


// Показ/ховаємо floating button в залежності від табу
function updateFiltersButtonVisibility() {
    const floatingBtn = document.getElementById('filtersFloatingBtn');
    
    if (floatingBtn && typeof window.currentTab !== 'undefined') {
        if (window.currentTab === 'search') {
            floatingBtn.style.display = 'flex';
        } else {
            floatingBtn.style.display = 'none';
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
}

console.log('🎛️ Filters sidebar component loaded');
