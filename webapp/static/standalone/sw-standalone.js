/**
 * Service Worker для автономного додатку EpicService.
 * Забезпечує офлайн-роботу через стратегію cache-first для статичних ресурсів
 * та network-first для API запитів.
 */
const CACHE_NAME = 'epicservice-standalone-v1';
const STATIC_ASSETS = [
    '/standalone',
    '/static/css/variables.css',
    '/static/css/reset.css',
    '/static/css/main.css',
    '/static/css/layout.css',
    '/static/css/components.css',
    '/static/css/admin.css',
    '/static/css/filters-sidebar.css',
    '/static/css/photos.css',
    '/static/js/core.js',
    '/static/js/search.js',
    '/static/js/list.js',
    '/static/js/archives.js',
    '/static/js/admin.js',
    '/static/js/user-management.js',
    '/static/js/init.js',
    '/static/js/swipe.js',
    '/static/js/api.js',
    '/static/js/utils.js',
    '/static/js/photos.js',
    '/static/js/filters-sidebar.js',
    '/static/standalone/auth.js',
    '/static/standalone/standalone-utils.js'
];

// Install - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activate - clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// Fetch - network-first for API, cache-first for static
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // API requests: network-first with cache fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request).then((response) => {
                // Cache successful GET responses
                if (event.request.method === 'GET' && response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                }
                return response;
            }).catch(() => caches.match(event.request))
        );
        return;
    }

    // Static assets: cache-first
    event.respondWith(
        caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
});
