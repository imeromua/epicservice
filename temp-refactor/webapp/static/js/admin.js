 /**
 * js/admin.js
 * Модуль адміністративної панелі.
 * Ізолює логіку статистики, розсилок та управління базою даних.
 */

const Admin = (function() {
    // Приватні змінні модуля
    let updateInterval = null;

    // Оновлення UI статистики
    async function loadStatistics() {
        const userId = Utils.getUserId();
        if (!userId) return;

        try {
            const data = await API.admin.getStatistics(userId);
            
            // Безпечно оновлюємо DOM, тільки якщо елементи існують
            const elTotalUsers = document.getElementById('totalUsersVal');
            const elTotalProducts = document.getElementById('totalProductsVal');
            const elReservedSum = document.getElementById('reservedSumVal');

            if (elTotalUsers) elTotalUsers.textContent = data.total_users || 0;
            if (elTotalProducts) elTotalProducts.textContent = data.total_products || 0;
            if (elReservedSum) elReservedSum.textContent = Utils.formatCurrency(data.total_reserved_sum || 0);

        } catch (error) {
            console.error('[Admin] Помилка завантаження статистики:', error);
        }
    }

    // Завантаження активних користувачів
    async function loadActiveUsers() {
        const userId = Utils.getUserId();
        if (!userId) return;

        const container = document.getElementById('activeUsersSection');
        if (!container) return; // Якщо ми не на сторінці адмінки

        try {
            const data = await API.admin.getActiveUsers(userId);
            const elActiveCount = document.getElementById('activeUsersVal');
            
            if (elActiveCount) {
                elActiveCount.textContent = data.count || 0;
            }

            if (!data.users || data.users.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: var(--hint-color); padding: 20px;">Немає активних кошиків</div>';
                return;
            }

            let html = '<div style="display: flex; flex-direction: column; gap: 12px;">';
            data.users.forEach(user => {
                html += `
                    <div style="background: var(--tg-theme-secondary-bg-color, #fff); padding: 12px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 600; margin-bottom: 4px;">Користувач: ${user.user_id}</div>
                            <div style="font-size: 14px; color: var(--hint-color);">Товарів: ${user.items_count}</div>
                        </div>
                        <div style="font-weight: 600; color: var(--tg-theme-button-color, #3b82f6);">
                            ${Utils.formatCurrency(user.reserved_sum)}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;

        } catch (error) {
            console.error('[Admin] Помилка завантаження активних користувачів:', error);
            container.innerHTML = '<div style="text-align: center; color: #ef4444; padding: 20px;">Помилка завантаження даних</div>';
        }
    }

    // Обробка розсилки (Broadcast)
    async function handleBroadcast() {
        const messageInput = document.getElementById('broadcastMessage');
        const alertBox = document.getElementById('broadcastAlert');
        
        if (!messageInput || !alertBox) return;

        const message = messageInput.value.trim();
        if (!message) {
            Utils.showAlert('❌ Введіть текст повідомлення');
            return;
        }

        Utils.showConfirm('Відправити це повідомлення всім користувачам?', async (confirmed) => {
            if (!confirmed) return;

            const userId = Utils.getUserId();
            alertBox.innerHTML = '<div class="alert alert-info">⏳ Виконується розсилка...</div>';

            try {
                const data = await API.admin.sendBroadcast(userId, message);
                
                if (data.success) {
                    Utils.haptic.success();
                    alertBox.innerHTML = `
                        <div class="alert alert-success" style="padding: 12px; border-radius: 8px; background: rgba(34, 197, 94, 0.1); color: #166534; margin-top: 12px;">
                            <span style="font-size: 20px;">✅</span>
                            <div>${data.message || 'Розсилка завершена'}<br><small>Розіслано: ${data.sent || 0} користувачам</small></div>
                        </div>
                    `;
                    messageInput.value = '';
                } else {
                    throw new Error(data.message || 'Невідома помилка сервера');
                }
            } catch (error) {
                Utils.haptic.error();
                alertBox.innerHTML = `
                    <div class="alert alert-error" style="padding: 12px; border-radius: 8px; background: rgba(239, 68, 68, 0.1); color: #991b1b; margin-top: 12px;">
                        <span style="font-size: 20px;">❌</span>
                        <div>Помилка: ${error.message}</div>
                    </div>
                `;
            }
        });
    }

    // Завантаження бази даних (Excel)
    async function handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const userId = Utils.getUserId();
        const uploadStatus = document.getElementById('uploadStatus');
        
        if (uploadStatus) {
            uploadStatus.style.display = 'block';
            uploadStatus.className = 'alert alert-info';
            uploadStatus.innerHTML = '⏳ Завантаження та обробка файлу...';
        }

        try {
            const data = await API.admin.uploadDatabase(userId, file);
            
            Utils.haptic.success();
            if (uploadStatus) {
                uploadStatus.className = 'alert alert-success';
                uploadStatus.innerHTML = `✅ ${data.message || 'Базу успішно оновлено!'}`;
                
                setTimeout(() => {
                    uploadStatus.style.display = 'none';
                }, 5000);
            }
            
            // Оновлюємо статистику після завантаження бази
            loadStatistics();
        } catch (error) {
            Utils.haptic.error();
            if (uploadStatus) {
                uploadStatus.className = 'alert alert-error';
                uploadStatus.innerHTML = `❌ Помилка: ${error.message}`;
            }
            Utils.showAlert(`Помилка: ${error.message}`);
        } finally {
            // Очищаємо input, щоб можна було завантажити той самий файл ще раз за потреби
            event.target.value = '';
        }
    }

    // Ініціалізація адмін-панелі
    function init() {
        const userId = Utils.getUserId();
        // Перевіряємо, чи є в нас глобальна змінна ADMIN_IDS (з index.html)
        const adminIds = window.ADMIN_IDS || [];
        const isAdmin = adminIds.includes(userId);

        // Біндимо кнопки, якщо вони є на сторінці
        const broadcastBtn = document.getElementById('sendBroadcastBtn');
        if (broadcastBtn) {
            broadcastBtn.addEventListener('click', handleBroadcast);
        }

        const fileInput = document.getElementById('dbUpload');
        if (fileInput) {
            fileInput.addEventListener('change', handleFileUpload);
        }

        // Кліки по плитках статистики
        const tileTotalUsers = document.getElementById('totalUsers');
        if (tileTotalUsers) {
            tileTotalUsers.addEventListener('click', async () => {
                Utils.haptic.selection();
                try {
                    const data = await API.admin.getUsers(userId);
                    if (data.users) {
                        Utils.showAlert(`Всього користувачів: ${data.count}\n\nID: ${data.users.slice(0, 10).join(', ')}${data.users.length > 10 ? '...' : ''}`);
                    }
                } catch (e) {
                    console.error('Помилка отримання списку користувачів:', e);
                }
            });
        }

        const tileActiveUsers = document.getElementById('activeUsers');
        if (tileActiveUsers) {
            tileActiveUsers.addEventListener('click', () => {
                Utils.haptic.selection();
                const section = document.getElementById('activeUsersSection');
                if (section) section.scrollIntoView({behavior: 'smooth'});
            });
        }

        const tileTotalProducts = document.getElementById('totalProducts');
        if (tileTotalProducts) {
            tileTotalProducts.addEventListener('click', () => {
                Utils.haptic.selection();
                Utils.showAlert('📦 Загальна кількість товарів у базі (оновлюється при завантаженні Excel)');
            });
        }

        const tileReservedSum = document.getElementById('reservedSum');
        if (tileReservedSum) {
            tileReservedSum.addEventListener('click', () => {
                Utils.haptic.selection();
                const section = document.getElementById('activeUsersSection');
                if (section) section.scrollIntoView({behavior: 'smooth'});
            });
        }

        // Запускаємо цикли оновлення тільки якщо ми на сторінці адмінки
        if (document.getElementById('adminPanelContainer') || document.querySelector('.stats-grid')) {
            loadStatistics();
            loadActiveUsers();
            
            // Очищаємо попередній інтервал, якщо init викликали двічі
            if (updateInterval) clearInterval(updateInterval);
            
            updateInterval = setInterval(() => {
                loadStatistics();
                loadActiveUsers();
            }, 30000); // Оновлювати кожні 30 секунд
        }
    }

    // Публічний інтерфейс
    return {
        init,
        loadStatistics,
        loadActiveUsers
    };
})();

// Експорт у глобальну область видимості
if (typeof window !== 'undefined') {
    window.Admin = Admin;
}

