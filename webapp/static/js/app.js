/**
 * js/app.js
 * Головний модуль клієнтського інтерфейсу.
 * Відповідає за ініціалізацію, навігацію та оркестрацію бізнес-процесів.
 * Використовує Utils, API, та Admin модулі.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Ініціалізація Telegram WebApp через нашу безпечну утиліту
    Utils.tg.expand?.();
    Utils.tg.ready?.();

    const userId = Utils.getUserId();
    const adminIds = window.ADMIN_IDS || [];
    const isAdmin = adminIds.includes(userId);

    // Стан додатку
    let currentTab = 'search';
    window.currentTab = currentTab; // глобально для filters-sidebar.js

    // Кешування DOM-елементів для швидкого доступу
    const DOM = {
        userInfo: document.getElementById('userInfo'),
        adminTabBtn: document.getElementById('adminTabBtn'),
        tabs: document.querySelectorAll('.tab'),
        tabContents: document.querySelectorAll('.tab-content'),
        
        // Пошук
        searchInput: document.getElementById('searchInput'),
        searchResults: document.getElementById('searchResults'),
        
        // Кошик
        cartList: document.getElementById('cartList'),
        cartTotal: document.getElementById('cartTotal'),
        checkoutBtn: document.getElementById('checkoutBtn'),
        clearCartBtn: document.getElementById('clearCartBtn'),
        
        // Архіви
        archivesList: document.getElementById('archivesList')
    };

    // ===== ІНІЦІАЛІЗАЦІЯ =====
    function init() {
        // Відображення інфо про користувача
        if (DOM.userInfo) {
            DOM.userInfo.textContent = userId 
                ? `Користувач: ${Utils.getUserName()}${isAdmin ? ' 👑' : ''}` 
                : 'Тестовий режим';
        }

        // Показуємо вкладку адмінки, якщо користувач має права
        if (isAdmin && DOM.adminTabBtn) {
            DOM.adminTabBtn.classList.remove('hidden');
            // Ініціалізуємо адмінський модуль
            if (window.Admin) Admin.init();
        }

        setupEventListeners();
        
        // Завантажуємо кошик при старті, якщо є ID
        if (userId) {
            CartModule.load();
        }

        console.log('🚀 App module initialized successfully', { userId, isAdmin });
    }

    // ===== НАВІГАЦІЯ (ВКЛАДКИ) =====
    function switchTab(tabId) {
        currentTab = tabId;
        window.currentTab = currentTab;
        
        // Оновлюємо UI вкладок
        DOM.tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });
        
        DOM.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `${tabId}Tab`);
        });

        // Викликаємо оновлення даних для специфічних вкладок при їх відкритті
        if (tabId === 'cart') CartModule.load();
        if (tabId === 'archives') ArchivesModule.load();
        if (tabId === 'admin' && window.Admin) {
            Admin.loadStatistics();
            Admin.loadActiveUsers();
        }
        
        // Синхронізація з боковою панеллю фільтрів
        if (window.updateFiltersButtonVisibility) {
            window.updateFiltersButtonVisibility();
        }
        
        Utils.haptic.selection();
    }

    // ===== EVENT LISTENERS =====
    function setupEventListeners() {
        // Навігація по вкладках
        DOM.tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.dataset.tab;
                if (tabId) switchTab(tabId);
            });
        });

        // Пошук
        if (DOM.searchInput) {
            DOM.searchInput.addEventListener('input', SearchModule.handleInput);
        }

        // Кошик
        if (DOM.checkoutBtn) {
            DOM.checkoutBtn.addEventListener('click', CartModule.checkout);
        }
        if (DOM.clearCartBtn) {
            DOM.clearCartBtn.addEventListener('click', CartModule.clear);
        }
    }

    // ===== МОДУЛЬ ПОШУКУ =====
    const SearchModule = {
        handleInput: Utils.debounce(async (e) => {
            const query = e.target.value.trim();
            if (query.length < 2) {
                if (DOM.searchResults) DOM.searchResults.innerHTML = '<div style="text-align:center; padding:20px; color:var(--hint-color);">Введіть мінімум 2 символи для пошуку</div>';
                return;
            }

            if (DOM.searchResults) DOM.searchResults.innerHTML = '<div class="loader" style="text-align:center; padding:20px;">⏳ Шукаємо...</div>';

            try {
                const data = await API.client.searchProducts(query, userId);
                SearchModule.render(data.products || []);
            } catch (error) {
                if (DOM.searchResults) DOM.searchResults.innerHTML = `<div style="text-align:center; color:#ef4444; padding:20px;">❌ Помилка: ${error.message}</div>`;
            }
        }, 500),

        render: (products) => {
            if (!DOM.searchResults) return;
            
            if (products.length === 0) {
                DOM.searchResults.innerHTML = '<div style="text-align:center; padding:20px; color:var(--hint-color);">Нічого не знайдено 😔</div>';
                return;
            }

            // Динамічний рендер карток
            let html = '<div class="products-grid" style="display:flex; flex-direction:column; gap:12px;">';
            products.forEach(p => {
                html += `
                    <div class="product-card" style="background:var(--tg-theme-secondary-bg-color, #fff); padding:16px; border-radius:12px;">
                        <div style="font-weight:600; margin-bottom:8px;">${p.назва || p.name}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="color:var(--tg-theme-button-color, #3b82f6); font-weight:bold;">${Utils.formatCurrency(p.ціна || p.price)}</div>
                            <button onclick="App.CartModule.add(${p.id})" style="background:var(--tg-theme-button-color, #3b82f6); color:var(--tg-theme-button-text-color, #fff); border:none; padding:8px 16px; border-radius:8px; cursor:pointer;">В кошик</button>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            DOM.searchResults.innerHTML = html;
        }
    };

    // ===== МОДУЛЬ КОШИКА (СПИСКУ) =====
    const CartModule = {
        load: async () => {
            if (!DOM.cartList) return;
            DOM.cartList.innerHTML = '<div class="loader" style="text-align:center; padding:20px;">⏳ Завантаження списку...</div>';
            
            try {
                const data = await API.client.getTempList(userId);
                CartModule.render(data.items || [], data.total_sum || 0);
            } catch (error) {
                DOM.cartList.innerHTML = `<div style="text-align:center; color:#ef4444; padding:20px;">❌ Помилка: ${error.message}</div>`;
            }
        },

        add: async (productId, quantity = 1) => {
            try {
                await API.client.addToList(userId, productId, quantity);
                Utils.haptic.success();
                Utils.showAlert('✅ Додано до списку');
                if (currentTab === 'cart') CartModule.load(); // Оновлюємо UI, якщо ми вже в кошику
            } catch (error) {
                Utils.haptic.error();
                Utils.showAlert(`❌ Помилка: ${error.message}`);
            }
        },

        render: (items, totalSum) => {
            if (!DOM.cartList) return;

            if (DOM.cartTotal) {
                DOM.cartTotal.textContent = `Разом: ${Utils.formatCurrency(totalSum)}`;
            }

            if (items.length === 0) {
                DOM.cartList.innerHTML = '<div style="text-align:center; padding:40px; color:var(--hint-color);">Список порожній 🛒</div>';
                if (DOM.checkoutBtn) DOM.checkoutBtn.style.display = 'none';
                if (DOM.clearCartBtn) DOM.clearCartBtn.style.display = 'none';
                return;
            }

            if (DOM.checkoutBtn) DOM.checkoutBtn.style.display = 'block';
            if (DOM.clearCartBtn) DOM.clearCartBtn.style.display = 'block';

            let html = '<div class="cart-items" style="display:flex; flex-direction:column; gap:12px;">';
            items.forEach(item => {
                html += `
                    <div class="cart-item" style="background:var(--tg-theme-secondary-bg-color, #fff); padding:16px; border-radius:12px; display:flex; justify-content:space-between; align-items:center;">
                        <div style="flex:1; padding-right:12px;">
                            <div style="font-weight:500; margin-bottom:4px;">${item.product?назва || item.product?.name || 'Невідомий товар'}</div>
                            <div style="color:var(--hint-color); font-size:14px;">${Utils.formatCurrency(item.product?ціна || item.product?.price || 0)} x ${item.quantity} шт</div>
                        </div>
                        <button onclick="App.CartModule.remove(${item.id})" style="background:#ef4444; color:#fff; border:none; width:36px; height:36px; border-radius:8px; cursor:pointer; display:flex; align-items:center; justify-content:center;">🗑️</button>
                    </div>
                `;
            });
            html += '</div>';
            DOM.cartList.innerHTML = html;
        },

        remove: async (itemId) => {
            Utils.showConfirm('Видалити цей товар?', async (confirmed) => {
                if (!confirmed) return;
                try {
                    await API.client.deleteFromList(userId, itemId);
                    Utils.haptic.impact('light');
                    CartModule.load();
                } catch (error) {
                    Utils.showAlert(`Помилка: ${error.message}`);
                }
            });
        },

        clear: async () => {
            Utils.showConfirm('Очистити весь список?', async (confirmed) => {
                if (!confirmed) return;
                try {
                    await API.client.clearList(userId);
                    Utils.haptic.success();
                    CartModule.load();
                } catch (error) {
                    Utils.showAlert(`Помилка: ${error.message}`);
                }
            });
        },

        checkout: async () => {
            Utils.showConfirm('Відправити замовлення?', async (confirmed) => {
                if (!confirmed) return;
                try {
                    await API.client.checkoutList(userId);
                    Utils.haptic.success();
                    Utils.showAlert('✅ Замовлення успішно відправлено!');
                    CartModule.load();
                } catch (error) {
                    Utils.showAlert(`Помилка: ${error.message}`);
                }
            });
        }
    };

    // ===== МОДУЛЬ АРХІВІВ =====
    const ArchivesModule = {
        load: async () => {
            if (!DOM.archivesList) return;
            DOM.archivesList.innerHTML = '<div class="loader" style="text-align:center; padding:20px;">⏳ Завантаження архівів...</div>';
            
            try {
                const data = await API.client.getArchives(userId);
                ArchivesModule.render(data.archives || []);
            } catch (error) {
                DOM.archivesList.innerHTML = `<div style="text-align:center; color:#ef4444; padding:20px;">❌ Помилка: ${error.message}</div>`;
            }
        },

        render: (archives) => {
            if (!DOM.archivesList) return;

            if (archives.length === 0) {
                DOM.archivesList.innerHTML = '<div style="text-align:center; padding:40px; color:var(--hint-color);">У вас ще немає архівів 📁</div>';
                return;
            }

            let html = '<div class="archives-grid" style="display:flex; flex-direction:column; gap:12px;">';
            archives.forEach(archive => {
                html += `
                    <div class="archive-card" style="background:var(--tg-theme-secondary-bg-color, #fff); padding:16px; border-radius:12px;">
                        <div style="font-weight:600; margin-bottom:8px;">📄 ${archive.date || archive.filename}</div>
                        <div style="display:flex; gap:8px; margin-top:12px;">
                            <button onclick="window.open('${API.client.getDownloadArchiveUrl(archive.filename, userId)}', '_blank')" style="flex:1; background:var(--tg-theme-button-color, #3b82f6); color:var(--tg-theme-button-text-color, #fff); border:none; padding:8px; border-radius:8px; cursor:pointer;">📥 Завантажити</button>
                            <button onclick="App.ArchivesModule.delete('${archive.filename}')" style="background:#ef4444; color:#fff; border:none; width:40px; border-radius:8px; cursor:pointer;">🗑️</button>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            DOM.archivesList.innerHTML = html;
        },

        delete: async (filename) => {
            Utils.showConfirm(`Видалити архів "${filename}"?`, async (confirmed) => {
                if (!confirmed) return;
                try {
                    await API.client.deleteArchive(filename, userId);
                    Utils.haptic.success();
                    ArchivesModule.load();
                } catch (error) {
                    Utils.showAlert(`Помилка: ${error.message}`);
                }
            });
        }
    };

    // Експортуємо глобально для використання в HTML
    window.App = {
        CartModule,
        ArchivesModule,
        SearchModule
    };

    // Запускаємо ініціалізацію
    init();
});