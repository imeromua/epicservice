// Service Worker для Epic Service PWA
const CACHE_NAME = 'epicservice-v1.0.1';
const RUNTIME_CACHE = 'epicservice-runtime-v1.0.1';

// Файли для кешування при встановленні
const PRECACHE_URLS = [
  '/',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Встановлення Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Precaching app shell');
        return cache.addAll(PRECACHE_URLS);
      })
      .then(() => self.skipWaiting())
  );
});

// Активація Service Worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => {
            return cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE;
          })
          .map((cacheName) => {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// Обробка запитів (Network First з Fallback на Cache)
self.addEventListener('fetch', (event) => {
  // Пропускаємо POST запити та external домени
  if (event.request.method !== 'GET' || 
      !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Клонуємо відповідь для кешу
        const responseToCache = response.clone();
        
        caches.open(RUNTIME_CACHE).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        
        return response;
      })
      .catch(() => {
        // При помилці мережі - повертаємо з кешу
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          
          // Якщо нічого не знайдено - показуємо офлайн сторінку
          if (event.request.destination === 'document') {
            return caches.match('/');
          }
          
          return new Response('Офлайн режим', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({
              'Content-Type': 'text/plain; charset=utf-8'
            })
          });
        });
      })
  );
});

// Обробка повідомлень від клієнта
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Синхронізація в фоні (для майбутнього використання)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-orders') {
    event.waitUntil(syncOrders());
  }
});

async function syncOrders() {
  console.log('[SW] Синхронізація замовлень...');
  // Тут можна додати логіку синхронізації
}
