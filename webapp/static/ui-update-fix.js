// 🔧 UI Update Fix (In-place DOM Update)
// Патч для оновлення відображення після резервування товару
// Працює in-place: не перемальовує весь DOM, тому скрол 100% не стрибає і картки не зникають

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

            // 1. Оновлюємо дані локально
            let targetProduct = null;
            if (typeof cachedProducts !== 'undefined') {
                const idx = cachedProducts.findIndex(p => p.id === selectedProduct.id);
                if (idx !== -1) {
                    cachedProducts[idx].user_reserved += currentQuantity;
                    cachedProducts[idx].user_reserved_sum += currentQuantity * selectedProduct.price;
                    cachedProducts[idx].available -= currentQuantity;
                    targetProduct = cachedProducts[idx];
                }
            }
            if (typeof filteredProducts !== 'undefined') {
                const idx = filteredProducts.findIndex(p => p.id === selectedProduct.id);
                if (idx !== -1) {
                    filteredProducts[idx].user_reserved += currentQuantity;
                    filteredProducts[idx].user_reserved_sum += currentQuantity * selectedProduct.price;
                    filteredProducts[idx].available -= currentQuantity;
                    if (!targetProduct) targetProduct = filteredProducts[idx];
                }
            }

            // 2. Отримуємо нові дані списку з сервера (лише шапка)
            const listResponse = await fetch(`/api/list/${userId}`);
            const listData = await listResponse.json();

            const deptResponse = await fetch(`/api/list/department/${userId}`);
            const deptData = await deptResponse.json();

            // 3. Оновлюємо шапку (Department Info)
            if (typeof currentDepartment !== 'undefined') {
                currentDepartment = deptData.department;
            }
            const info = document.getElementById('departmentInfo');
            if (info) {
                if (deptData.department !== null && listData.count > 0) {
                    document.getElementById('currentDepartment').textContent = deptData.department;
                    document.getElementById('itemCount').textContent = listData.count;
                    info.classList.add('active');
                } else {
                    info.classList.remove('active');
                }
            }
            if (typeof updateListBadge === 'function') {
                updateListBadge(listData.count || 0);
            }

            // 4. ТОЧКОВЕ ОНОВЛЕННЯ DOM (IN-PLACE)
            // Знаходимо всі картки на екрані і оновлюємо їх без перезавантаження контейнера
            const cards = document.querySelectorAll('.product-card');
            let foundAny = false;

            cards.forEach(card => {
                // Витягуємо ID товару
                let pid = card.dataset.productId;
                if (!pid) {
                    const onclickStr = card.getAttribute('onclick') || '';
                    const match = onclickStr.match(/"id":\s*(\d+)/);
                    if (match) pid = match[1];
                }
                if (!pid) return;
                pid = parseInt(pid);
                
                // Знаходимо актуальні дані товару
                let p = null;
                if (typeof cachedProducts !== 'undefined') p = cachedProducts.find(x => x.id === pid);
                if (!p && typeof filteredProducts !== 'undefined') p = filteredProducts.find(x => x.id === pid);
                if (!p) return;
                
                // Оновлюємо статус департаменту (для замків)
                p.is_different_department = (deptData.department !== null && p.department !== deptData.department);
                p.current_list_department = deptData.department;
                
                // Якщо товару більше немає в наявності - ховаємо картку
                if (p.available <= 0) {
                    card.style.display = 'none';
                    return;
                }
                
                foundAny = true;

                // Оновлюємо картку через renderProduct
                if (typeof window.renderProduct === 'function') {
                    const newHtml = window.renderProduct(p);
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = newHtml;
                    const newCard = tempDiv.firstElementChild;
                    if (newCard) {
                        card.replaceWith(newCard);
                    }
                }
            });

            // Якщо після приховування не лишилось видимих карток
            if (!foundAny) {
                const results = document.getElementById('searchResults');
                if (results) {
                    results.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>Нічого не знайдено або все зарезервовано</div>';
                }
            }

            console.log('✅ UI updated IN-PLACE. DOM wasn\\'t destroyed, scroll preserved!');
        } else {
            tg.showAlert('❌ ' + d.message);
        }
    } catch (e) {
        tg.showAlert('❌ ' + e.message);
    }
};

console.log('🔧 UI update fix loaded (True In-Place DOM Strategy)');
