// PWA Installation Handler
let deferredPrompt;

// Отримуємо елементи (підтримка різних ID)
function getInstallButton() {
  return document.getElementById('pwa-install-btn') || 
         document.getElementById('pwa-install-btn-action');
}

function getInstallBanner() {
  return document.getElementById('pwa-install-banner');
}

// Відстеження події beforeinstallprompt
window.addEventListener('beforeinstallprompt', (e) => {
  console.log('[PWA] ✅ beforeinstallprompt event fired');
  e.preventDefault();
  deferredPrompt = e;
  
  const installBanner = getInstallBanner();
  const installButton = getInstallButton();
  
  // Показуємо банер установки
  if (installBanner) {
    console.log('[PWA] Showing install banner');
    installBanner.style.display = 'block';
  } else {
    console.warn('[PWA] Install banner element not found');
  }
  
  // Активуємо кнопку установки
  if (installButton) {
    console.log('[PWA] Enabling install button');
    installButton.style.display = 'inline-block';
  } else {
    console.warn('[PWA] Install button element not found');
  }
});

// Функція установки PWA
async function installPWA() {
  console.log('[PWA] Install button clicked');
  
  if (!deferredPrompt) {
    console.error('[PWA] ❌ No deferred prompt available');
    console.log('[PWA] Possible reasons:');
    console.log('  1. PWA already installed');
    console.log('  2. beforeinstallprompt event not fired yet');
    console.log('  3. Browser does not support PWA');
    console.log('  4. Site not served over HTTPS (or not localhost)');
    
    // Показуємо повідомлення користувачу
    showNotification('⚠️ Не вдалося встановити. Спробуйте через меню браузера.');
    return;
  }
  
  console.log('[PWA] Showing install prompt...');
  
  try {
    // Показуємо промпт установки
    await deferredPrompt.prompt();
    
    // Чекаємо на вибір користувача
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`[PWA] User response: ${outcome}`);
    
    if (outcome === 'accepted') {
      console.log('[PWA] ✅ User accepted installation');
      showNotification('✅ Встановлення розпочато...');
    } else {
      console.log('[PWA] ❌ User dismissed installation');
      showNotification('ℹ️ Ви можете встановити додаток пізніше');
    }
    
    // Очищуємо deferred prompt
    deferredPrompt = null;
    
    // Ховаємо банер
    const installBanner = getInstallBanner();
    if (installBanner) {
      installBanner.style.display = 'none';
    }
  } catch (error) {
    console.error('[PWA] Install prompt failed:', error);
    showNotification('❌ Помилка встановлення. Спробуйте ще раз.');
  }
}

// Ініціалізація обробників після завантаження DOM
function initPWAHandlers() {
  const installButton = getInstallButton();
  const installBanner = getInstallBanner();
  
  console.log('[PWA] Initializing PWA handlers...');
  console.log('[PWA] Install button found:', !!installButton);
  console.log('[PWA] Install banner found:', !!installBanner);
  
  // Додаємо обробник на всі можливі кнопки
  if (installButton) {
    console.log('[PWA] Attaching click handler to button:', installButton.id);
    installButton.addEventListener('click', installPWA);
  }
  
  // Додатковий обробник для кнопки в банері
  const bannerButton = document.querySelector('#pwa-install-banner button.btn-primary');
  if (bannerButton && bannerButton !== installButton) {
    console.log('[PWA] Attaching click handler to banner button');
    bannerButton.addEventListener('click', installPWA);
  }
}

// Ініціалізація при завантаженні DOM
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPWAHandlers);
} else {
  initPWAHandlers();
}

// Відстеження успішної установки
window.addEventListener('appinstalled', (e) => {
  console.log('[PWA] ✅ App successfully installed');
  deferredPrompt = null;
  
  const installBanner = getInstallBanner();
  const installButton = getInstallButton();
  
  // Ховаємо елементи установки
  if (installBanner) {
    installBanner.style.display = 'none';
  }
  if (installButton) {
    installButton.style.display = 'none';
  }
  
  // Показуємо повідомлення про успішну установку
  showNotification('🎉 Epic Service успішно встановлено!');
});

// Реєстрація Service Worker (ШЛЯХ ЗМІНЕНО НА /sw.js)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      });
      console.log('[PWA] ✅ Service Worker registered:', registration.scope);
      
      // Перевірка оновлень
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        console.log('[PWA] 🔄 New Service Worker found');
        
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('[PWA] ✅ New version available');
            showUpdateNotification();
          }
        });
      });
      
    } catch (error) {
      console.error('[PWA] ❌ Service Worker registration failed:', error);
    }
  });
} else {
  console.warn('[PWA] ⚠️ Service Workers not supported in this browser');
}

// Показати повідомлення про оновлення
function showUpdateNotification() {
  const updateBanner = document.createElement('div');
  updateBanner.className = 'pwa-update-banner';
  updateBanner.innerHTML = `
    <div class="pwa-update-content">
      <span>🎉 Доступна нова версія!</span>
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

// Діагностика при завантаженні
window.addEventListener('load', () => {
  console.log('\n' + '='.repeat(50));
  console.log('[PWA] 📊 Diagnostics');
  console.log('='.repeat(50));
  console.log('[PWA] Running as:', isPWA() ? 'Installed PWA ✅' : 'Browser 🌐');
  console.log('[PWA] Protocol:', window.location.protocol);
  console.log('[PWA] Service Worker support:', 'serviceWorker' in navigator ? 'Yes ✅' : 'No ❌');
  console.log('[PWA] Online status:', navigator.onLine ? 'Online ✅' : 'Offline ⚠️');
  console.log('[PWA] Install button:', !!getInstallButton() ? 'Found ✅' : 'Not found ❌');
  console.log('[PWA] Install banner:', !!getInstallBanner() ? 'Found ✅' : 'Not found ❌');
  console.log('='.repeat(50) + '\n');
});

// Експорт для використання в інших скриптах
window.PWA = {
  isPWA,
  showNotification,
  installPWA,
  checkCompatibility: () => {
    const checks = {
      serviceWorker: 'serviceWorker' in navigator,
      https: window.location.protocol === 'https:' || window.location.hostname === 'localhost',
      standalone: isPWA(),
      online: navigator.onLine
    };
    console.table(checks);
    return checks;
  }
};
