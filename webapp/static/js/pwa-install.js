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
    showNotification('⚠️ Не вдалося встановити. Спробуйте через меню браузера.');
    return;
  }
  
  console.log('[PWA] Showing install prompt...');
  
  try {
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`[PWA] User response: ${outcome}`);
    
    if (outcome === 'accepted') {
      showNotification('✅ Встановлення розпочато...');
    } else {
      showNotification('ℹ️ Ви можете встановити додаток пізніше');
    }
    
    deferredPrompt = null;
    
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
  
  if (installButton) {
    installButton.addEventListener('click', installPWA);
  }
  
  const bannerButton = document.querySelector('#pwa-install-banner button.btn-primary');
  if (bannerButton && bannerButton !== installButton) {
    bannerButton.addEventListener('click', installPWA);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPWAHandlers);
} else {
  initPWAHandlers();
}

window.addEventListener('appinstalled', (e) => {
  console.log('[PWA] ✅ App successfully installed');
  deferredPrompt = null;
  
  const installBanner = getInstallBanner();
  const installButton = getInstallButton();
  
  if (installBanner) installBanner.style.display = 'none';
  if (installButton) installButton.style.display = 'none';
  
  showNotification('🎉 Epic Service успішно встановлено!');
});

// Реєстрація Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      console.log('[PWA] ✅ Service Worker registered:', registration.scope);
      
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            showUpdateNotification();
          }
        });
      });
    } catch (error) {
      console.error('[PWA] ❌ Service Worker registration failed:', error);
    }
  });
}

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
  
  document.getElementById('pwa-update-btn').addEventListener('click', () => {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
    }
    window.location.reload();
  });
  
  document.getElementById('pwa-update-dismiss').addEventListener('click', () => {
    updateBanner.remove();
  });
}

function showNotification(message) {
  const notification = document.createElement('div');
  notification.className = 'pwa-notification';
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed; top: 20px; right: 20px;
    background: #10b981; color: white;
    padding: 16px 24px; border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    z-index: 10000; animation: slideIn 0.3s ease-out;
  `;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-in';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

function isPWA() {
  return window.matchMedia('(display-mode: standalone)').matches ||
         window.navigator.standalone === true;
}

window.PWA = { isPWA, showNotification, installPWA };
