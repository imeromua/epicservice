// EpicService - Service Worker (self-unregister)
// Цей файл видаляє раніше зареєстрований Service Worker,
// щоб браузери перестали робити зайві запити на /sw.js

self.addEventListener('install', () => {
    self.skipWaiting();
});

self.addEventListener('activate', () => {
    self.registration.unregister();
});
