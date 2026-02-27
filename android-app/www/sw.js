/**
 * sw.js — Service Worker для EpicService Android App
 * Забезпечує офлайн-роботу шляхом кешування статичних ресурсів.
 */

const CACHE_NAME = 'epicservice-v1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/css/app.css',
    '/js/api.js',
    '/js/phone-auth.js',
    '/js/app.js',
    '/manifest.json',
];

// Встановлення — кешуємо статику
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Активація — видаляємо старі кеші
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// Запити — стратегія: мережа спочатку, кеш як запасний варіант
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // API-запити — лише мережа (не кешуємо)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // Статика — Network First із fallback на кеш
    event.respondWith(
        fetch(event.request)
            .then(resp => {
                if (resp.ok) {
                    const clone = resp.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                }
                return resp;
            })
            .catch(() => caches.match(event.request))
    );
});
