/**
 * js/api.js
 * Єдиний мережевий шар для взаємодії з бекендом EpicService.
 * Збирає всі HTTP-запити в одному місці для зручного рефакторингу та обробки помилок.
 */

const API = (function() {
    const BASE_URL = '/api';

    // Helper: get validated Telegram initData for TMA auth header
    function _tmaInitData() {
        return window.Telegram?.WebApp?.initData || null;
    }

    // Внутрішній метод для виконання запитів із базовою обробкою помилок
    async function request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
        
        const headers = {
            'Accept': 'application/json',
            ...options.headers
        };

        // Automatically add TMA initData header for all /api requests
        const tmaData = _tmaInitData();
        if (tmaData && !headers['X-Telegram-Init-Data']) {
            headers['X-Telegram-Init-Data'] = tmaData;
        }

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

    /**
     * Download a file using the appropriate method for the current environment.
     *
     * In Telegram Mini App (TMA) the embedded WebView blocks programmatic blob
     * downloads (the `download` attribute on <a> elements is ignored).  Instead
     * we request a short-lived one-time token from the backend and open the
     * download URL via Telegram.WebApp.openLink() which launches the user's
     * external browser where normal file downloads work.
     *
     * In a regular browser (standalone / desktop) we keep the existing
     * fetch-blob-anchor approach.
     *
     * @param {string} url              - The API URL to fetch the file from.
     * @param {string} defaultFilename  - Fallback filename for the download.
     * @param {string} [tokenEndpoint]  - Backend endpoint to request a download
     *                                    token from.  Defaults to '/api/download-token'.
     *                                    Use '/api/admin/download-token' for admin
     *                                    downloads.
     */
    async function downloadFile(url, defaultFilename, tokenEndpoint) {
        const isTMA = !!(window.Telegram?.WebApp?.initData);

        if (isTMA) {
            // TMA path: obtain a one-time token and open via Telegram.WebApp.openLink()
            try {
                const tmaData = window.Telegram.WebApp.initData;
                const endpoint = tokenEndpoint || '/api/download-token';

                const tokenResp = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Telegram-Init-Data': tmaData,
                    },
                    body: JSON.stringify({ resource_url: url }),
                });

                if (!tokenResp.ok) {
                    let errMsg = `HTTP ${tokenResp.status}`;
                    try {
                        const errData = await tokenResp.json();
                        errMsg = errData.detail || errData.error || errMsg;
                    } catch (_) {}
                    throw new Error(errMsg);
                }

                const { token } = await tokenResp.json();
                const separator = url.includes('?') ? '&' : '?';
                const downloadUrl = `${url}${separator}dl_token=${encodeURIComponent(token)}`;

                // Open in the user's external browser where downloads work normally.
                window.Telegram.WebApp.openLink(downloadUrl);
            } catch (e) {
                console.error('[API] downloadFile TMA error:', e.message);
                if (typeof tg !== 'undefined') tg.showAlert('❌ Помилка завантаження: ' + e.message);
                else alert('❌ Помилка завантаження: ' + e.message);
            }
            return;
        }

        // Non-TMA path: fetch blob and trigger browser download via anchor click.
        try {
            const tmaData = _tmaInitData();
            const dlHeaders = {};
            if (tmaData) dlHeaders['X-Telegram-Init-Data'] = tmaData;

            const resp = await fetch(url, { headers: dlHeaders });
            if (!resp.ok) {
                let errMsg = `HTTP ${resp.status}`;
                try {
                    const errData = await resp.json();
                    errMsg = errData.detail || errData.error || errMsg;
                } catch (_) {}
                throw new Error(errMsg);
            }

            const contentDisposition = resp.headers.get('Content-Disposition') || '';
            const fnMatch = contentDisposition.match(/filename[^;=\n]*=(?:(['"])(.+?)\1|([^;\n]*))/i);
            const filename = (fnMatch && (fnMatch[2] || fnMatch[3])) || defaultFilename;

            const blob = await resp.blob();
            const objectUrl = URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = objectUrl;
            anchor.download = filename;
            document.body.appendChild(anchor);
            anchor.click();
            document.body.removeChild(anchor);
            URL.revokeObjectURL(objectUrl);
        } catch (e) {
            console.error('[API] downloadFile error:', e.message);
            if (typeof tg !== 'undefined') tg.showAlert('❌ Помилка завантаження: ' + e.message);
            else alert('❌ Помилка завантаження: ' + e.message);
        }
    }

    // Публічний інтерфейс модула
    return {
        downloadFile,
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