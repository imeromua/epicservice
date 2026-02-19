// PWA Installation Handler
let deferredPrompt;
const installButton = document.getElementById('pwa-install-btn');
const installBanner = document.getElementById('pwa-install-banner');

// Відстеження події beforeinstallprompt
window.addEventListener('beforeinstallprompt', (e) => {
  console.log('[PWA] beforeinstallprompt event fired');
  e.preventDefault();
  deferredPrompt = e;
  
  // Показуємо банер установки (якщо є)
  if (installBanner) {
    installBanner.style.display = 'block';
  }
  
  // Активуємо кнопку установки (якщо є)
  if (installButton) {
    installButton.style.display = 'inline-block';
  }
});

// Обробник кліку на кнопку установки
if (installButton) {
  installButton.addEventListener('click', async () => {
    if (!deferredPrompt) {
      console.log('[PWA] No deferred prompt available');
      return;
    }
    
    // Показуємо промпт установки
    deferredPrompt.prompt();
    
    // Чекаємо на вибір користувача
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`[PWA] User response: ${outcome}`);
    
    if (outcome === 'accepted') {
      console.log('[PWA] User accepted installation');
    } else {
      console.log('[PWA] User dismissed installation');
    }
    
    // Очищуємо deferred prompt
    deferredPrompt = null;
    
    //Ховаємо банер
    if (installBanner) {
      installBanner.style.display = 'none';
    }
  });
}

// Відстеження успішної установки
window.addEventListener('appinstalled', (e) => {
  console.log('[PWA] App successfully installed');
  deferredPrompt = null;
  
  // Ховаємо елементи установки
  if (installBanner) {
    installBanner.style.display = 'none';
  }
  if (installButton) {
    installButton.style.display = 'none';
  }
  
  // Можна показати повідомлення про успішну установку
  showNotification('Epic Service успішно встановлено! 🎉');
});

// Реєстрація Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/static/sw.js', {
        scope: '/'
      });
      console.log('[PWA] Service Worker registered:', registration.scope);
      
      // Перевірка оновлень
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        console.log('[PWA] New Service Worker found');
        
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // Нова версія доступна
            showUpdateNotification();
          }
        });
      });
      
    } catch (error) {
      console.error('[PWA] Service Worker registration failed:', error);
    }
  });
}

// Показати повідомлення про оновлення
function showUpdateNotification() {
  const updateBanner = document.createElement('div');
  updateBanner.className = 'pwa-update-banner';
  updateBanner.innerHTML = `
    <div class="pwa-update-content">
      <span>Доступна нова версія! 🎉</span>
      <button id="pwa-update-btn" class="btn btn-sm btn-primary">Оновити</button>
      <button id="pwa-update-dismiss" class="btn btn-sm btn-secondary">Пізніше</button>
    </div>
  `;
  document.body.appendChild(updateBanner);
  
  // Обробник оновлення
  document.getElementById('pwa-update-btn').addEventListener('click', () => {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
    }
    window.location.reload();
  });
  
  // Обробник відхилення
  document.getElementById('pwa-update-dismiss').addEventListener('click', () => {
    updateBanner.remove();
  });
}

// Показати повідомлення
function showNotification(message) {
  const notification = document.createElement('div');
  notification.className = 'pwa-notification';
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: #10b981;
    color: white;
    padding: 16px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    z-index: 10000;
    animation: slideIn 0.3s ease-out;
  `;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-in';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Перевірка чи додаток запущено як PWA
function isPWA() {
  return window.matchMedia('(display-mode: standalone)').matches ||
         window.navigator.standalone === true;
}

// Логування стану PWA
if (isPWA()) {
  console.log('[PWA] Running as installed app');
} else {
  console.log('[PWA] Running in browser');
}

// Експорт для використання в інших скриптах
window.PWA = {
  isPWA,
  showNotification
};
