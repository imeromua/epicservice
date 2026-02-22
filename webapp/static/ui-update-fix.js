// 🔧 UI Update Fix
// Патч для оновлення відображення після резервування товару
// Зберігає позицію скролу та не скидає фільтри

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

            // 📌 1. Запам'ятовуємо позицію скролу
            const currentScrollPos = window.scrollY;

            // 2. Оновлюємо дані в cachedProducts локально
            const productIndex = cachedProducts.findIndex(p => p.id === selectedProduct.id);
            if (productIndex !== -1) {
                cachedProducts[productIndex].user_reserved += currentQuantity;
                cachedProducts[productIndex].user_reserved_sum += currentQuantity * selectedProduct.price;
                cachedProducts[productIndex].available -= currentQuantity;
            }

            // 3. Оновлюємо бейдж і інфо про відділ з сервера
            const listResponse = await fetch(`/api/list/${userId}`);
            const listData = await listResponse.json();

            const deptResponse = await fetch(`/api/list/department/${userId}`);
            const deptData = await deptResponse.json();

            // updateDepartmentInfo оновлює блокування відділів і викликає updateSearchResults()
            // Це повністю перемалює поточні картки (пошук або фільтр) БЕЗ повторного запиту на сервер
            updateDepartmentInfo(deptData.department, listData.count || 0);
            updateListBadge(listData.count || 0);

            // Якщо раптом updateDepartmentInfo не викликав updateSearchResults
            if (!cachedProducts || cachedProducts.length === 0) {
                if (typeof updateSearchResults === 'function') updateSearchResults();
            }

            // 📌 4. Відновлюємо скрол миттєво після оновлення DOM
            requestAnimationFrame(() => {
                window.scrollTo(0, currentScrollPos);
            });

            console.log('✅ UI refreshed in-place, scroll preserved at:', currentScrollPos);
        } else {
            tg.showAlert('❌ ' + d.message);
        }
    } catch (e) {
        tg.showAlert('❌ ' + e.message);
    }
};

console.log('🔧 UI update fix loaded (with smooth scroll preservation)');
