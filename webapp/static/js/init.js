// EpicService - Initialization
// App startup and debug

if (userId) loadList();
updateSearchBoxVisibility();

// Debug info
console.log('App initialized:', { userId, isAdmin, ADMIN_IDS });
console.log('🚀 PWA Ready!');
console.log('📱 Display mode:', 
  window.matchMedia('(display-mode: standalone)').matches ? 'Standalone (PWA)' : 'Browser'
);
