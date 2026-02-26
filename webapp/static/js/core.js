// EpicService - Core Module
// Global state and utilities

let currentQuantity = 1, editQuantity = 1, selectedProduct = null, editingItem = null, searchTimeout = null, currentTab = 'search';
var cachedProducts = [];
let currentDepartment = null;
let pullStartY = 0, pulling = false;
let selectedFile = null;
let cachedProductsInfo = null;

// Show admin tab if user is admin
if (isAdmin) {
    const adminBtn = document.getElementById('adminTabBtn');
    if (adminBtn) adminBtn.classList.remove('hidden');
}

// Перевірка ролі користувача (модератор/адмін з БД)
let userRole = 'user';

async function checkUserRole() {
    if (!userId) return;
    try {
        const resp = await fetch(`/api/user/role?user_id=${userId}`);
        const data = await resp.json();
        userRole = data.role || 'user';
        if (userRole === 'moderator' || userRole === 'admin') {
            const modBtn = document.getElementById('moderationTabBtn');
            if (modBtn) modBtn.classList.remove('hidden');
        }
    } catch (e) {
        console.warn('⚠️ Не вдалося отримати роль користувача:', e);
    }
}

checkUserRole();

// Update functions
function updateListBadge(count) { const badge = document.getElementById('listBadge'); if (count > 0) { badge.textContent = count; badge.style.display = 'block'; } else { badge.style.display = 'none'; } }
function updateSearchBoxVisibility() { const searchBox = document.getElementById('searchBoxContainer'); if (currentTab === 'search') { searchBox.style.display = 'block'; } else { searchBox.style.display = 'none'; } }

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

function switchTab(tab) { 
    currentTab = tab; 
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active')); 
    document.querySelectorAll('.content').forEach(c => c.classList.remove('active')); 
    const tabs = {'search': [0,'searchTab'], 'list': [1,'listTab'], 'archives': [2,'archivesTab'], 'moderation': [3,'moderationContent'], 'admin': [4,'adminContent']}; 
    const [idx, id] = tabs[tab]; 
    document.querySelectorAll('.tab')[idx].classList.add('active'); 
    document.getElementById(id).classList.add('active'); 
    updateSearchBoxVisibility(); 
    
    if (typeof updateFiltersButtonVisibility === 'function') {
        updateFiltersButtonVisibility();
    }
    
    if (tab === 'list') loadList(); 
    if (tab === 'archives') loadArchives(); 
    if (tab === 'moderation' && (userRole === 'moderator' || userRole === 'admin' || isAdmin)) loadModeratorPhotoModeration();
    if (tab === 'admin' && isAdmin) loadAdminData();
}

function goToArchives() { document.getElementById('successModal').classList.remove('active'); switchTab('archives'); }
function startNewSearch() { document.getElementById('successModal').classList.remove('active'); switchTab('search'); document.getElementById('searchInput').focus(); }
