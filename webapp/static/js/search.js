// EpicService - Search Module
// Product search, rendering, and pull-to-refresh

// Pull-to-refresh
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
        case 'moderation':
            loadModeratorPhotoModeration();
            break;
        case 'admin':
            if (isAdmin) loadAdminData();
            break;
    }
}

document.getElementById('userInfo').textContent = userId ? `Користувач: ${tg.initDataUnsafe.user.first_name}${isAdmin ? ' 👑' : ''}` : 'Тестовий режим';

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

function updateListBadge(count) { const badge = document.getElementById('listBadge'); if (count > 0) { badge.textContent = count; badge.style.display = 'block'; } else { badge.style.display = 'none'; } }
function updateSearchBoxVisibility() { const searchBox = document.getElementById('searchBoxContainer'); if (currentTab === 'search') { searchBox.style.display = 'block'; } else { searchBox.style.display = 'none'; } }
function switchTab(tab) { 
    currentTab = tab; 
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active')); 
    document.querySelectorAll('.content').forEach(c => c.classList.remove('active')); 
    const tabs = {'search': ['searchTabBtn','searchTab'], 'list': ['listTabBtn','listTab'], 'archives': ['archivesTabBtn','archivesTab'], 'moderation': ['moderationTabBtn','moderationContent'], 'admin': ['adminTabBtn','adminContent']}; 
    const [btnId, id] = tabs[tab]; 
    document.getElementById(btnId).classList.add('active'); 
    document.getElementById(id).classList.add('active'); 
    updateSearchBoxVisibility(); 
    
    // Update filters button visibility
    if (typeof updateFiltersButtonVisibility === 'function') {
        updateFiltersButtonVisibility();
    }
    
    if (tab === 'list') loadList(); 
    if (tab === 'archives') loadArchives(); 
    if (tab === 'moderation') loadModeratorPhotoModeration();
    if (tab === 'admin' && isAdmin) loadAdminData();
}
function goToArchives() { document.getElementById('successModal').classList.remove('active'); switchTab('archives'); }
function startNewSearch() { document.getElementById('successModal').classList.remove('active'); switchTab('search'); document.getElementById('searchInput').focus(); }
document.getElementById('searchInput').addEventListener('input', (e) => { clearTimeout(searchTimeout); const query = e.target.value.trim(); if (query.length < 2) { document.getElementById('searchResults').innerHTML = ''; cachedProducts = []; return; } searchTimeout = setTimeout(() => search(query), 500); });

function renderProduct(p) {
    const isLocked = p.is_different_department;
    const lockedClass = isLocked ? ' locked' : '';
    const statusClass = isLocked ? ' locked' : '';
    const statusText = isLocked ? '🔒 Заблоковано' : '✅ Знайдено';
    const clickHandler = isLocked ? `onclick=\"showLockedAlert('${p.current_list_department}')\"` : `onclick='openModalWithPhotos(${JSON.stringify(p).replace(/'/g, "&#39;")})'`;
    const hasPhotos = p.photos && p.photos.length > 0;
    const photoIndicator = hasPhotos ? `<span class=\"photo-badge photo-badge-inline\">📷 ${p.photos.length}</span>` : '';
    
    return `<div class=\"product-card${lockedClass}\" data-product-id=\"${p.id}\" ${clickHandler}>
        <div class=\"lock-overlay\">🔒</div>
        <div class=\"product-header\">
            <span class=\"product-article\">🆔 ${p.article}</span>
            <div class=\"product-status-row\">
                ${photoIndicator}
                <span class=\"product-status${statusClass}\">${statusText}</span>
            </div>
        </div>
        <div class=\"product-name\">📝 ${p.name}</div>
        <div class=\"product-details\">
            <div class=\"product-detail-row\"><span class=\"product-detail-label\">🏢 Відділ:</span><span class=\"product-detail-value\">${p.department}</span></div>
            <div class=\"product-detail-row\"><span class=\"product-detail-label\">📂 Група:</span><span class=\"product-detail-value\">${p.group}</span></div>
            <div class=\"product-detail-row\"><span class=\"product-detail-label\">⌛ Без руху (міс):</span><span class=\"product-detail-value ${p.months_without_movement > 3 ? 'warning' : ''}\">${p.months_without_movement}</span></div>
            <div class=\"product-detail-row\"><span class=\"product-detail-label\">💰 Сума залишку:</span><span class=\"product-detail-value highlight\">${p.balance_sum.toFixed(2)} грн</span></div>
            <div class=\"product-detail-row\"><span class=\"product-detail-label\">📦 Доступно:</span><span class=\"product-detail-value success\">${p.available}</span></div>
            ${p.user_reserved > 0 ? `<div class=\"product-detail-row\"><span class=\"product-detail-label\">🛒 В резерві:</span><span class=\"product-detail-value warning\">${p.user_reserved} (${p.user_reserved_sum.toFixed(2)} грн)</span></div>` : ''}
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
        const response = await fetch('/api/search', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({query, user_id: userId}) }); 
        const data = await response.json(); 
        if (!data.products || data.products.length === 0) { 
            results.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено</div>'; 
            cachedProducts = [];
            return; 
        }

        // Завантаження фото паралельно для всіх товарів
        await Promise.all(data.products.map(async p => {
            p.photos = await loadProductPhotos(p.article);
        }));
        
        cachedProducts = data.products.filter(p => p.available > 0);
        updateSearchResults();
    } catch (error) { 
        results.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div>Помилка пошуку</div>'; 
        cachedProducts = [];
    } 
}

function openAddModal(product) { selectedProduct = product; currentQuantity = 1; document.getElementById('modalTitle').textContent = product.article; document.getElementById('modalPrice').textContent = `Ціна: ${product.price.toFixed(2)} грн`; document.getElementById('modalAvailable').textContent = `Доступно: ${product.available} шт.`; document.getElementById('qtyDisplay').textContent = 1; document.getElementById('customInputBox').style.display = 'none'; document.getElementById('normalSelector').style.display = 'block'; document.getElementById('customQtyInput').value = ''; document.getElementById('addModal').classList.add('active'); }
function closeModal() { document.getElementById('addModal').classList.remove('active'); }
function changeQty(d) { currentQuantity = Math.max(1, Math.min(selectedProduct.available, currentQuantity + d)); document.getElementById('qtyDisplay').textContent = currentQuantity; }
function addAllAvailable() { currentQuantity = selectedProduct.available; document.getElementById('qtyDisplay').textContent = currentQuantity; tg.HapticFeedback.notificationOccurred('success'); }
function showCustomInput() { document.getElementById('customInputBox').style.display = 'block'; document.getElementById('normalSelector').style.display = 'none'; document.getElementById('customQtyInput').focus(); }
function applyCustomQty() { const v = parseInt(document.getElementById('customQtyInput').value); if (isNaN(v) || v < 1) { tg.showAlert('❌ Введіть коректне число'); return; } if (v > selectedProduct.available) { tg.showAlert(`⚠️ Максимум: ${selectedProduct.available} шт.`); return; } currentQuantity = v; document.getElementById('qtyDisplay').textContent = v; document.getElementById('customInputBox').style.display = 'none'; document.getElementById('normalSelector').style.display = 'block'; tg.HapticFeedback.notificationOccurred('success'); }

async function confirmAdd() { 
    try { 
        const r = await fetch('/api/add', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({user_id: userId, product_id: selectedProduct.id, quantity: currentQuantity}) }); 
        const d = await r.json(); 
        if (d.success) { 
            tg.showAlert(`✅ ${d.message}`); 
            closeModal(); 
            
            const scrollPos = window.scrollY;
            
            // Оновлюємо основний кеш
            const productIndex = cachedProducts.findIndex(p => p.id === selectedProduct.id);
            if (productIndex !== -1) {
                cachedProducts[productIndex].user_reserved += currentQuantity;
                cachedProducts[productIndex].user_reserved_sum += currentQuantity * selectedProduct.price;
                cachedProducts[productIndex].available -= currentQuantity;
                selectedProduct = cachedProducts[productIndex];
            }
            
            const listResponse = await fetch(`/api/list/${userId}`);
            const listData = await listResponse.json();
            
            const deptResponse = await fetch(`/api/list/department/${userId}`);
            const deptData = await deptResponse.json();
            
            // Оновлюємо інтерфейс
            updateDepartmentInfo(deptData.department, listData.count || 0);
            updateListBadge(listData.count || 0);
            
            // Оновлюємо DOM цього товару
            const card = document.querySelector(`.product-card[data-product-id="${selectedProduct.id}"]`);
            if (card) {
                if (selectedProduct.available <= 0) {
                    card.remove();
                } else {
                    card.outerHTML = renderProduct(selectedProduct);
                }
            } else if (!window.filterState || !window.filterState.isActive) {
                updateSearchResults();
            }

            // Відновлюємо скрол
            requestAnimationFrame(() => window.scrollTo(0, scrollPos));
            
        } else { 
            tg.showAlert('❌ ' + d.message); 
        } 
    } catch (e) { 
        tg.showAlert('❌ ' + e.message); 
    } 
}

function openEditModal(item) { editingItem = item; editQuantity = item.quantity; document.getElementById('editModalTitle').textContent = item.article; document.getElementById('editModalPrice').textContent = `Ціна: ${item.price.toFixed(2)} грн`; document.getElementById('editQtyDisplay').textContent = editQuantity; document.getElementById('editModal').classList.add('active'); }
function closeEditModal() { document.getElementById('editModal').classList.remove('active'); }
function changeEditQty(d) { editQuantity = Math.max(1, editQuantity + d); document.getElementById('editQtyDisplay').textContent = editQuantity; }
async function confirmUpdate() { 
    const oldQuantity = editingItem.quantity;
    try { 
        const r = await fetch('/api/update', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({user_id: userId, product_id: editingItem.product_id, quantity: editQuantity}) 
        }); 
        const d = await r.json(); 
        if (d.success) { 
            tg.showAlert(`✅ ${d.message}`); 
            closeEditModal();
            
            const productIndex = cachedProducts.findIndex(p => p.id === editingItem.product_id);
            if (productIndex !== -1) {
                const quantityDiff = editQuantity - oldQuantity;
                cachedProducts[productIndex].user_reserved += quantityDiff;
                cachedProducts[productIndex].user_reserved_sum += quantityDiff * editingItem.price;
                cachedProducts[productIndex].available -= quantityDiff;
                
                const card = document.querySelector(`.product-card[data-product-id="${editingItem.product_id}"]`);
                if (card) {
                    if (cachedProducts[productIndex].available <= 0) {
                        card.remove();
                    } else {
                        card.outerHTML = renderProduct(cachedProducts[productIndex]);
                    }
                } else if (!window.filterState || !window.filterState.isActive) {
                    updateSearchResults();
                }
            }
            
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
            body: JSON.stringify({user_id: userId, product_id: editingItem.product_id}) 
        }); 
        const d = await r.json(); 
        if (d.success) { 
            tg.showAlert(`✅ ${d.message}`); 
            closeEditModal();
            
            const productIndex = cachedProducts.findIndex(p => p.id === editingItem.product_id);
            if (productIndex !== -1) {
                cachedProducts[productIndex].available += editingItem.quantity;
                cachedProducts[productIndex].user_reserved -= editingItem.quantity;
                cachedProducts[productIndex].user_reserved_sum -= editingItem.quantity * editingItem.price;
                
                const card = document.querySelector(`.product-card[data-product-id="${editingItem.product_id}"]`);
                if (card) {
                    card.outerHTML = renderProduct(cachedProducts[productIndex]);
                } else if (!window.filterState || !window.filterState.isActive) {
                    updateSearchResults();
                }
            }
            
            loadList(); 
        } else { 
            tg.showAlert('❌ ' + d.message); 
        } 
    } catch (e) { 
        tg.showAlert('❌ ' + e.message); 
    } 
}
async function saveList() { try { const r = await fetch(`/api/save/${userId}`, { method: 'POST' }); const d = await r.json(); if (d.success) { tg.HapticFeedback.notificationOccurred('success'); if (d.cleared) { loadList(); updateDepartmentInfo(null, 0); } document.getElementById('successModal').classList.add('active'); } else { tg.showAlert('❌ ' + d.message); } } catch (e) { tg.showAlert('❌ ' + e.message); } }
async function clearList() { 
    if (!confirm('Очистити весь список?')) return; 
    try { 
        const r = await fetch(`/api/clear/${userId}`, { method: 'POST' }); 
        const d = await r.json(); 
        if (d.success) { 
            tg.showAlert(`✅ ${d.message}`); 
            updateDepartmentInfo(null, 0);
            
            cachedProducts.forEach(p => {
                p.available += (p.user_reserved || 0);
                p.user_reserved = 0;
                p.user_reserved_sum = 0;
            });
            
            if (!window.filterState || !window.filterState.isActive) {
                updateSearchResults();
            } else {
                document.querySelectorAll('.product-card').forEach(card => {
                    const productId = parseInt(card.getAttribute('data-product-id'));
                    const product = cachedProducts.find(p => p.id === productId);
                    if (product) {
                        card.outerHTML = renderProduct(product);
                    }
                });
            }
            
            loadList(); 
        } else { 
            tg.showAlert('❌ ' + d.message); 
        } 
    } catch (e) { 
        tg.showAlert('❌ ' + e.message); 
    } 
}
