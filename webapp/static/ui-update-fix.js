// 🔧 UI Update Fix
// Патч для оновлення відображення після резервування товару

// Перевизначаємо confirmAdd з підтримкою оновлення UI
window.confirmAdd = async function() { 
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
            
            // Оновлюємо дані в cachedProducts
            const productIndex = cachedProducts.findIndex(p => p.id === selectedProduct.id);
            if (productIndex !== -1) {
                cachedProducts[productIndex].user_reserved += currentQuantity;
                cachedProducts[productIndex].user_reserved_sum += currentQuantity * selectedProduct.price;
                cachedProducts[productIndex].available -= currentQuantity;
            }
            
            // Оновлюємо бейдж і інфо про відділ
            const listResponse = await fetch(`/api/list/${userId}`);
            const listData = await listResponse.json();
            
            const deptResponse = await fetch(`/api/list/department/${userId}`);
            const deptData = await deptResponse.json();
            
            updateDepartmentInfo(deptData.department, listData.count || 0);
            updateListBadge(listData.count || 0);
            
            // ✅ ОНОВЛЮЄМО UI З ЗБЕРЕЖЕННЯМ ФІЛЬТРІВ
            if (typeof window.filterState !== 'undefined' && window.filterState.isActive) {
                // Якщо активні фільтри — використовуємо reapplyFilters
                console.log('🎛️ Refreshing with filters...');
                if (typeof window.reapplyFilters === 'function') {
                    await window.reapplyFilters();
                } else {
                    console.warn('⚠️ reapplyFilters not available, using fallback');
                    updateSearchResults();
                }
            } else {
                // Звичайний пошук — використовуємо updateSearchResults
                console.log('🔍 Refreshing search results...');
                updateSearchResults();
            }
            
            console.log('✅ UI refreshed after adding product');
        } else { 
            tg.showAlert('❌ ' + d.message); 
        } 
    } catch (e) { 
        tg.showAlert('❌ ' + e.message); 
    } 
};

console.log('🔧 UI update fix loaded');
