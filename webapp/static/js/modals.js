/* =============================================
   MODALS.JS - Модальні вікна
   Add product, Edit product, Success modals
   ============================================= */

// === ADD MODAL ===

function openAddModal(product) {
    AppState.selectedProduct = product;
    AppState.currentQuantity = 1;
    
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

function changeQty(delta) {
    AppState.currentQuantity = Math.max(1, Math.min(
        AppState.selectedProduct.available,
        AppState.currentQuantity + delta
    ));
    document.getElementById('qtyDisplay').textContent = AppState.currentQuantity;
}

function addAllAvailable() {
    AppState.currentQuantity = AppState.selectedProduct.available;
    document.getElementById('qtyDisplay').textContent = AppState.currentQuantity;
    if (window.tg) window.tg.HapticFeedback.notificationOccurred('success');
}

function showCustomInput() {
    document.getElementById('customInputBox').style.display = 'block';
    document.getElementById('normalSelector').style.display = 'none';
    document.getElementById('customQtyInput').focus();
}

function applyCustomQty() {
    const value = parseInt(document.getElementById('customQtyInput').value);
    
    if (isNaN(value) || value < 1) {
        if (window.tg) window.tg.showAlert('❌ Введіть коректне число');
        return;
    }
    
    if (value > AppState.selectedProduct.available) {
        if (window.tg) window.tg.showAlert(`⚠️ Максимум: ${AppState.selectedProduct.available} шт.`);
        return;
    }
    
    AppState.currentQuantity = value;
    document.getElementById('qtyDisplay').textContent = value;
    document.getElementById('customInputBox').style.display = 'none';
    document.getElementById('normalSelector').style.display = 'block';
    if (window.tg) window.tg.HapticFeedback.notificationOccurred('success');
}

async function confirmAdd() {
    try {
        const response = await fetch('/api/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: AppState.userId,
                product_id: AppState.selectedProduct.id,
                quantity: AppState.currentQuantity
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (window.tg) window.tg.showAlert(`✅ ${data.message}`);
            closeModal();
            
            // Update cached product
            const productIndex = AppState.cachedProducts.findIndex(
                p => p.id === AppState.selectedProduct.id
            );
            if (productIndex !== -1) {
                AppState.cachedProducts[productIndex].user_reserved += AppState.currentQuantity;
                AppState.cachedProducts[productIndex].user_reserved_sum += 
                    AppState.currentQuantity * AppState.selectedProduct.price;
                AppState.cachedProducts[productIndex].available -= AppState.currentQuantity;
            }
            
            // Refresh list info
            const listResponse = await fetch(`/api/list/${AppState.userId}`);
            const listData = await listResponse.json();
            
            const deptResponse = await fetch(`/api/list/department/${AppState.userId}`);
            const deptData = await deptResponse.json();
            
            updateDepartmentInfo(deptData.department, listData.count || 0);
            updateListBadge(listData.count || 0);
        } else {
            if (window.tg) window.tg.showAlert('❌ ' + data.message);
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ ' + error.message);
        console.error('Add error:', error);
    }
}

// === EDIT MODAL ===

function openEditModal(item) {
    AppState.editingItem = item;
    AppState.editQuantity = item.quantity;
    
    document.getElementById('editModalTitle').textContent = item.article;
    document.getElementById('editModalPrice').textContent = `Ціна: ${item.price.toFixed(2)} грн`;
    document.getElementById('editQtyDisplay').textContent = AppState.editQuantity;
    document.getElementById('editModal').classList.add('active');
}

function closeEditModal() {
    document.getElementById('editModal').classList.remove('active');
}

function changeEditQty(delta) {
    AppState.editQuantity = Math.max(1, AppState.editQuantity + delta);
    document.getElementById('editQtyDisplay').textContent = AppState.editQuantity;
}

async function confirmUpdate() {
    try {
        const response = await fetch('/api/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: AppState.userId,
                product_id: AppState.editingItem.product_id,
                quantity: AppState.editQuantity
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (window.tg) window.tg.showAlert(`✅ ${data.message}`);
            closeEditModal();
            loadList();
        } else {
            if (window.tg) window.tg.showAlert('❌ ' + data.message);
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ ' + error.message);
        console.error('Update error:', error);
    }
}

async function confirmDelete() {
    if (!confirm('Видалити товар зі списку?')) return;
    
    try {
        const response = await fetch('/api/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: AppState.userId,
                product_id: AppState.editingItem.product_id
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (window.tg) window.tg.showAlert(`✅ ${data.message}`);
            closeEditModal();
            loadList();
        } else {
            if (window.tg) window.tg.showAlert('❌ ' + data.message);
        }
    } catch (error) {
        if (window.tg) window.tg.showAlert('❌ ' + error.message);
        console.error('Delete error:', error);
    }
}

// Export functions
window.openAddModal = openAddModal;
window.closeModal = closeModal;
window.changeQty = changeQty;
window.addAllAvailable = addAllAvailable;
window.showCustomInput = showCustomInput;
window.applyCustomQty = applyCustomQty;
window.confirmAdd = confirmAdd;
window.openEditModal = openEditModal;
window.closeEditModal = closeEditModal;
window.changeEditQty = changeEditQty;
window.confirmUpdate = confirmUpdate;
window.confirmDelete = confirmDelete;