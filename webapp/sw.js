// Service Worker для PWA EpicService
// Мінімальна версія без кешування

const CACHE_NAME = 'epicservice-v1';
const DEBUG = true;

// Логування для відлагодження
function log(...args) {
  if (DEBUG) {
    console.log('[SW]', ...args);
  }
}

// Встановлення Service Worker
self.addEventListener('install', (event) => {
  log('Installing Service Worker...');
  // skipWaiting() примусово активує новий SW
  self.skipWaiting();
});

// Активація Service Worker
self.addEventListener('activate', (event) => {
  log('Activating Service Worker...');
  event.waitUntil(
    // Видаляємо старі кеші при оновленні
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => cacheName !== CACHE_NAME)
          .map((cacheName) => {
            log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          })
      );
    }).then(() => {
      log('Service Worker activated');
      // Забираємо контроль над всіма відкритими сторінками
      return self.clients.claim();
    })
  );
});

// Обробка запитів
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Не кешуємо API запити та динамічний контент
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.includes('telegram.org') ||
    event.request.method !== 'GET'
  ) {
    // Просто проксуємо запит без кешування
    event.respondWith(fetch(event.request));
    return;
  }
  
  // Для статичних файлів використовуємо стратегію Network First
  // (спочатку мережа, якщо недоступна - кеш)
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Клонуємо відповідь для збереження в кеш
        const responseToCache = response.clone();
        
        // Зберігаємо в кеш тільки успішні відповіді
        if (response.status === 200) {
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        
        return response;
      })
      .catch(() => {
        // Якщо мережа недоступна, пробуємо взяти з кешу
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            log('Serving from cache:', event.request.url);
            return cachedResponse;
          }
          
          // Якщо в кеші теж немає, повертаємо базову відповідь
          return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({
              'Content-Type': 'text/plain'
            })
          });
        });
      })
  );
});

// Обробка повідомлень від клієнта
self.addEventListener('message', (event) => {
  log('Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.delete(CACHE_NAME).then(() => {
        log('Cache cleared');
        event.ports[0].postMessage({ success: true });
      })
    );
  }
});

log('Service Worker script loaded');
