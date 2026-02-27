/**
 * js/api.js
 * Єдиний мережевий шар для взаємодії з бекендом EpicService.
 * Збирає всі HTTP-запити в одному місці для зручного рефакторингу та обробки помилок.
 */

const API = (function() {
    const BASE_URL = '/api';

    // Внутрішній метод для виконання запитів із базовою обробкою помилок
    async function request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
        
        const headers = {
            'Accept': 'application/json',
            ...options.headers
        };

        // Автоматично серіалізуємо об'єкти в JSON (окрім FormData для файлів)
        if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, { ...options, headers });
            
            const data = await response.json();
            
            if (!response.ok) {
                const errorMessage = data.detail || data.message || `Помилка HTTP: ${response.status}`;
                throw new Error(errorMessage);
            }
            
            return data;
        } catch (error) {
            console.error(`[API Error] ${options.method || 'GET'} ${url}:`, error.message);
            throw error;
        }
    }

    // Публічний інтерфейс модула
    return {
        // КЛІЄНТСЬКА ЧАСТИНА (клієнтські запити)
        client: {
            searchProducts: (query, userId, offset = 0, limit = 500) => 
                request('/search', { 
                    method: 'POST', 
                    body: { query, user_id: userId, offset, limit } 
                }),
                
            getTempList: (userId) => 
                request(`/list/${userId}`),
                
            addToList: (userId, productId, quantity) => 
                request('/add', {
                    method: 'POST',
                    body: { user_id: userId, product_id: productId, quantity }
                }),
                
            updateQuantity: (userId, productId, quantity) => 
                request('/update', {
                    method: 'POST',
                    body: { user_id: userId, product_id: productId, quantity }
                }),
                
            deleteFromList: (userId, productId) => 
                request('/delete', {
                    method: 'POST',
                    body: { user_id: userId, product_id: productId }
                }),
                
            clearList: (userId) => 
                request(`/clear/${userId}`, {
                    method: 'POST'
                }),
                
            saveList: (userId) => 
                request(`/save/${userId}`, {
                    method: 'POST'
                }),

            getArchives: (userId) => 
                request(`/archives/${userId}`),

            deleteArchive: (filename, userId) => 
                request(`/archive/delete/${encodeURIComponent(filename)}?user_id=${userId}`, {
                    method: 'DELETE'
                }),
                
            // Для завантаження файлу повертаємо просто URL, оскільки це обробляється через window.location.href
            getDownloadArchiveUrl: (filename, userId) => 
                `${BASE_URL}/archive/download/${encodeURIComponent(filename)}?user_id=${userId}`
        },
        
        // АДМІНІСТРАТИВНА ЧАСТИНА (запити адмін-панелі)
        admin: {
            getStatistics: (userId) => 
                request(`/admin/statistics?user_id=${userId}`),

            getUsers: (userId) => 
                request(`/admin/users?user_id=${userId}`),

            getActiveUsers: (userId) => 
                request(`/admin/users/active?user_id=${userId}`),

            getReservesByDepartments: (userId) => 
                request(`/admin/reserved/by-department?user_id=${userId}`),

            sendBroadcast: (userId, message) => 
                request('/admin/broadcast', {
                    method: 'POST',
                    body: { user_id: userId, message: message }
                }),

            uploadDatabase: async (userId, file) => {
                const formData = new FormData();
                formData.append('file', file);
                
                // Для FormData використовуємо нативний fetch, щоб браузер сам проставив правильний Content-Type з boundary
                try {
                    const response = await fetch(`${BASE_URL}/admin/import?user_id=${userId}`, {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.detail || data.message || 'Помилка завантаження');
                    return data;
                } catch (error) {
                    console.error('[API Error] POST /admin/import:', error.message);
                    throw error;
                }
            }
        }
    };
})();

// Експортуємо глобально для використання у Vanilla JS
if (typeof window !== 'undefined') {
    window.API = API;
}