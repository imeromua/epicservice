#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re

print("🔧 Етап 3: Модульність JavaScript")

# Читаємо app.js
js_file = '../static/js/app.js'
with open(js_file, 'r', encoding='utf-8') as f:
    app_js = f.read()

print(f"📦 Розмір app.js: {len(app_js)} символів")

# ============= ВИЗНАЧАЄМО МОДУЛІ =============

# 1. CORE.JS - глобальні змінні та утиліти
core_js = '''// EpicService - Core Module
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
    const tabs = {'search': [0,'searchTab'], 'list': [1,'listTab'], 'archives': [2,'archivesTab'], 'admin': [3,'adminContent']}; 
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

function goToArchives() { document.getElementById('successModal').classList.remove('active'); switchTab('archives'); }
function startNewSearch() { document.getElementById('successModal').classList.remove('active'); switchTab('search'); document.getElementById('searchInput').focus(); }
'''

# Знаходимо початок search функцій
search_start = app_js.find('// Pull-to-refresh')
search_end = app_js.find('async function loadList()')

# 2. SEARCH.JS - пошук та pull-to-refresh
search_section = app_js[search_start:search_end]

search_js = f'''// EpicService - Search Module
// Product search, rendering, and pull-to-refresh

{search_section}
'''

# 3. LIST.JS - список товарів
list_start = app_js.find('async function loadList()')
list_end = app_js.find('async function loadStatistics()')

list_section = app_js[list_start:list_end]

list_js = f'''// EpicService - List Module
// Shopping list management

{list_section}
'''

# 4. ARCHIVES.JS - архіви
archives_start = app_js.find('async function loadStatistics()')
archives_end = app_js.find('// === ADMIN FUNCTIONS ===')

archives_section = app_js[archives_start:archives_end]

archives_js = f'''// EpicService - Archives Module
// Archive management and statistics

{archives_section}
'''

# 5. ADMIN.JS - адмін функції
admin_start = app_js.find('// === ADMIN FUNCTIONS ===')
admin_end = app_js.find("if (userId) loadList();")

admin_section = app_js[admin_start:admin_end]

admin_js = f'''// EpicService - Admin Module
// Admin panel and management functions

{admin_section}
'''

# 6. INIT.JS - ініціалізація
init_js = '''// EpicService - Initialization
// App startup and debug

if (userId) loadList();
updateSearchBoxVisibility();

// Debug info
console.log('App initialized:', { userId, isAdmin, ADMIN_IDS });
console.log('🚀 PWA Ready!');
console.log('📱 Display mode:', 
  window.matchMedia('(display-mode: standalone)').matches ? 'Standalone (PWA)' : 'Browser'
);
'''

# ============= ЗБЕРІГАЄМО МОДУЛІ =============

js_dir = '../static/js'
modules = {
    'core.js': core_js,
    'search.js': search_js,
    'list.js': list_js,
    'archives.js': archives_js,
    'admin.js': admin_js,
    'init.js': init_js
}

for filename, content in modules.items():
    filepath = os.path.join(js_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ {filename}: {len(content)} символів")

# ============= ОНОВЛЮЄМО INDEX.HTML =============

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Замінюємо app.js на модулі
old_script = '<script src="/static/js/app.js"></script>'
new_scripts = '''<script src="/static/js/core.js"></script>
    <script src="/static/js/search.js"></script>
    <script src="/static/js/list.js"></script>
    <script src="/static/js/archives.js"></script>
    <script src="/static/js/admin.js"></script>
    <script src="/static/js/init.js"></script>'''

html = html.replace(old_script, new_scripts)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ index.html оновлено - додано 6 модулів")

# Видаляємо старий app.js
if os.path.exists(js_file):
    os.remove(js_file)
    print("🗑️ Видалено старий app.js")

# Git
os.chdir('../..')
os.system('git add webapp/static/js/')
os.system('git add webapp/templates/index.html')
os.system('git commit -m "refactor(step3): split JS into modules (core, search, list, archives, admin, init)"')
os.system('git push')

print("\n🎉 Етап 3 завершено!")
print("📦 Створено 6 модулів:")
print("   - core.js (глобальний стан)")
print("   - search.js (пошук)")
print("   - list.js (список)")
print("   - archives.js (архіви)")
print("   - admin.js (адмін)")
print("   - init.js (ініціалізація)")
print("\n📱 ТЕСТУЙ В ЖИВУ!")

