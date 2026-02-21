/**
 * Photo gallery and upload functionality
 */

let currentPhotoIndex = 0;
let uploadingPhoto = false;

/**
 * Update renderProduct function to include photo badge
 */
function addPhotoBadgeToProduct(productHTML, photos) {
    if (photos && photos.length > 0) {
        const badge = `<span class="photo-badge">📷 ${photos.length}</span>`;
        return productHTML.replace('<div class="lock-overlay">', badge + '<div class="lock-overlay">');
    }
    return productHTML;
}

/**
 * Open modal with photo gallery
 */
function openModalWithPhotos(product) {
    selectedProduct = product;
    currentQuantity = 1;
    currentPhotoIndex = 0;
    
    // Set basic info
    document.getElementById('modalTitle').textContent = product.article;
    document.getElementById('modalPrice').textContent = `Ціна: ${product.price.toFixed(2)} грн`;
    document.getElementById('modalAvailable').textContent = `Доступно: ${product.available} шт.`;
    
    const modalContent = document.querySelector('#addModal .modal-content');
    
    // Remove existing gallery and photo button
    const existingGallery = modalContent.querySelector('.photo-gallery');
    if (existingGallery) existingGallery.remove();
    
    const existingPhotoBtn = modalContent.querySelector('.add-photo-btn');
    if (existingPhotoBtn) existingPhotoBtn.remove();
    
    // Add photo gallery if photos exist
    if (product.photos && product.photos.length > 0) {
        const galleryHTML = createPhotoGallery(product);
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = galleryHTML;
        modalContent.insertBefore(tempDiv.firstElementChild, modalContent.querySelector('.quick-actions'));
    }
    
    // Add photo upload button
    const photoButtonHTML = createPhotoButton(product);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = photoButtonHTML;
    const cancelBtn = modalContent.querySelector('.cancel-btn');
    modalContent.insertBefore(tempDiv.firstElementChild, cancelBtn);
    
    // Reset quantity selector
    document.getElementById('qtyDisplay').textContent = 1;
    document.getElementById('customInputBox').style.display = 'none';
    document.getElementById('normalSelector').style.display = 'block';
    document.getElementById('customQtyInput').value = '';
    
    document.getElementById('addModal').classList.add('active');
}

/**
 * Create photo gallery HTML
 */
function createPhotoGallery(product) {
    const hasMultiple = product.photos.length > 1;
    
    return `
        <div class="photo-gallery" id="photoGallery">
            <img src="/static/uploads/photos/${product.article}/${product.photos[0]}" 
                 alt="Product photo" 
                 class="product-photo" 
                 id="currentPhoto"
                 onclick="fullscreenPhoto(event)">
            ${hasMultiple ? `
                <div class="photo-nav">
                    <button class="photo-nav-btn" onclick="previousPhoto(event)">◀</button>
                    <span class="photo-counter" id="photoCounter">1/${product.photos.length}</span>
                    <button class="photo-nav-btn" onclick="nextPhoto(event)">▶</button>
                </div>
            ` : `
                <div class="photo-nav">
                    <span class="photo-counter">1/1</span>
                </div>
            `}
        </div>
    `;
}

/**
 * Create photo upload button HTML
 */
function createPhotoButton(product) {
    const photosCount = product.photos ? product.photos.length : 0;
    const canAddMore = photosCount < 3;
    
    return `
        <button class="add-photo-btn ${!canAddMore ? 'disabled' : ''}" 
                id="addPhotoBtn"
                onclick="${canAddMore ? 'openPhotoUpload(event)' : ''}"
                ${!canAddMore ? 'disabled' : ''}>
            📷 ${photosCount > 0 ? `Додати ще фото (${photosCount}/3)` : 'Додати фото (0/3)'}
        </button>
    `;
}

/**
 * Navigate to previous photo
 */
function previousPhoto(e) {
    e.stopPropagation();
    if (!selectedProduct.photos || selectedProduct.photos.length <= 1) return;
    
    currentPhotoIndex = (currentPhotoIndex - 1 + selectedProduct.photos.length) % selectedProduct.photos.length;
    updatePhotoDisplay();
    
    if (typeof tg !== 'undefined' && tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }
}

/**
 * Navigate to next photo
 */
function nextPhoto(e) {
    e.stopPropagation();
    if (!selectedProduct.photos || selectedProduct.photos.length <= 1) return;
    
    currentPhotoIndex = (currentPhotoIndex + 1) % selectedProduct.photos.length;
    updatePhotoDisplay();
    
    if (typeof tg !== 'undefined' && tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }
}

/**
 * Update photo display
 */
function updatePhotoDisplay() {
    const img = document.getElementById('currentPhoto');
    const counter = document.getElementById('photoCounter');
    
    if (img && selectedProduct.photos) {
        img.src = `/static/uploads/photos/${selectedProduct.article}/${selectedProduct.photos[currentPhotoIndex]}`;
        if (counter) {
            counter.textContent = `${currentPhotoIndex + 1}/${selectedProduct.photos.length}`;
        }
    }
}

/**
 * Open photo in fullscreen
 */
function fullscreenPhoto(e) {
    e.stopPropagation();
    const img = e.target;
    
    if (img.requestFullscreen) {
        img.requestFullscreen();
    } else if (img.webkitRequestFullscreen) {
        img.webkitRequestFullscreen();
    } else if (img.mozRequestFullScreen) {
        img.mozRequestFullScreen();
    }
}

/**
 * Open photo upload dialog
 */
async function openPhotoUpload(e) {
    e.stopPropagation();
    
    if (uploadingPhoto) {
        if (typeof tg !== 'undefined') {
            tg.showAlert('⏳ Зачекайте, попереднє фото ще завантажується');
        }
        return;
    }
    
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    
    input.onchange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.type.startsWith('image/')) {
            if (typeof tg !== 'undefined') {
                tg.showAlert('❌ Оберіть файл зображення');
            }
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) {
            if (typeof tg !== 'undefined') {
                tg.showAlert('❌ Файл занадто великий (макс 10MB)');
            }
            return;
        }
        
        await uploadPhoto(file);
    };
    
    input.click();
}

/**
 * Upload photo to server
 */
async function uploadPhoto(file) {
    uploadingPhoto = true;
    
    const gallery = document.getElementById('photoGallery');
    if (gallery) {
        const loader = document.createElement('div');
        loader.className = 'photo-uploading';
        loader.innerHTML = '<div class="photo-uploading-spinner">⟳</div><div>Завантаження...</div>';
        gallery.appendChild(loader);
    }
    
    const btn = document.getElementById('addPhotoBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ Завантаження...';
    }
    
    try {
        const formData = new FormData();
        formData.append('photo', file);
        formData.append('article', selectedProduct.article);
        formData.append('user_id', userId);
        
        const response = await fetch('/api/photos/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (typeof tg !== 'undefined') {
                tg.showAlert('✅ Фото надіслано на модерацію');
                tg.HapticFeedback.notificationOccurred('success');
            }
            
            selectedProduct.photos = data.photos || [];
            
            closeModal();
            setTimeout(() => openModalWithPhotos(selectedProduct), 300);
        } else {
            if (typeof tg !== 'undefined') {
                tg.showAlert('❌ ' + (data.message || 'Помилка завантаження'));
            }
        }
    } catch (error) {
        if (typeof tg !== 'undefined') {
            tg.showAlert('❌ Помилка: ' + error.message);
        }
    } finally {
        uploadingPhoto = false;
    }
}

/**
 * Load product photos from server
 */
async function loadProductPhotos(article) {
    try {
        const response = await fetch(`/api/photos/product/${article}`);
        const data = await response.json();
        
        if (data.success) {
            return data.photos.map(p => p.file_path.split('/').pop());
        }
    } catch (error) {
        console.error('Error loading photos:', error);
    }
    
    return [];
}
