/* =============================================
   UTILS.JS - Утіліти та UI helpers
   Pull-to-refresh, tabs, badges, department info
   ============================================= */

// Tab Management
function switchTab(tab) {
    AppState.currentTab = tab;
    
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
    
    const tabs = {
        'search': [0, 'searchTab'],
        'list': [1, 'listTab'],
        'archives': [2, 'archivesTab'],
        'admin': [3, 'adminContent']
    };
    
    const [idx, id] = tabs[tab];
    document.querySelectorAll('.tab')[idx].classList.add('active');
    document.getElementById(id).classList.add('active');
    
    updateSearchBoxVisibility();
    
    // Update filters button visibility
    if (typeof updateFiltersButtonVisibility === 'function') {
        updateFiltersButtonVisibility();
    }
    
    // Load tab-specific data
    if (tab === 'list') loadList();
    if (tab === 'archives') loadArchives();
    if (tab === 'admin' && AppState.isAdmin) loadAdminData();
}

function updateSearchBoxVisibility() {
    const searchBox = document.getElementById('searchBoxContainer');
    if (searchBox) {
        searchBox.style.display = AppState.currentTab === 'search' ? 'block' : 'none';
    }
}

// Badge Management
function updateListBadge(count) {
    const badge = document.getElementById('listBadge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    }
}

// Department Info
function updateDepartmentInfo(department, count) {
    AppState.currentDepartment = department;
    const info = document.getElementById('departmentInfo');
    
    if (!info) return;
    
    if (department !== null && count > 0) {
        document.getElementById('currentDepartment').textContent = department;
        document.getElementById('itemCount').textContent = count;
        info.classList.add('active');
    } else {
        info.classList.remove('active');
    }
    
    // Update product cards locked state
    if (AppState.cachedProducts.length > 0) {
        AppState.cachedProducts.forEach(p => {
            p.is_different_department = (department !== null && p.department !== department);
            p.current_list_department = department;
        });
        updateSearchResults();
    }
}

// Pull-to-Refresh
function initPullToRefresh() {
    document.addEventListener('touchstart', e => {
        if (window.scrollY === 0) {
            AppState.pullStartY = e.touches[0].clientY;
            AppState.pulling = true;
        }
    }, {passive: true});
    
    document.addEventListener('touchmove', e => {
        if (!AppState.pulling) return;
        const pullDistance = e.touches[0].clientY - AppState.pullStartY;
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
        if (!AppState.pulling) return;
        const pullDistance = e.changedTouches[0].clientY - AppState.pullStartY;
        const indicator = document.getElementById('pullIndicator');
        
        if (pullDistance >= 80) {
            indicator.textContent = '⟳ Оновлення...';
            if (window.tg) window.tg.HapticFeedback.impactOccurred('medium');
            refreshCurrentTab();
        }
        
        setTimeout(() => {
            indicator.classList.remove('active');
            indicator.style.opacity = 0;
            indicator.style.transform = 'translateY(-100%)';
            indicator.textContent = '↓ Потягніть для оновлення';
        }, 500);
        
        AppState.pulling = false;
    }, {passive: true});
}

function refreshCurrentTab() {
    switch(AppState.currentTab) {
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
            if (AppState.isAdmin) loadAdminData();
            break;
    }
}

// Navigation helpers
function goToArchives() {
    document.getElementById('successModal').classList.remove('active');
    switchTab('archives');
}

function startNewSearch() {
    document.getElementById('successModal').classList.remove('active');
    switchTab('search');
    document.getElementById('searchInput').focus();
}

// Export functions
window.switchTab = switchTab;
window.updateSearchBoxVisibility = updateSearchBoxVisibility;
window.updateListBadge = updateListBadge;
window.updateDepartmentInfo = updateDepartmentInfo;
window.initPullToRefresh = initPullToRefresh;
window.refreshCurrentTab = refreshCurrentTab;
window.goToArchives = goToArchives;
window.startNewSearch = startNewSearch;