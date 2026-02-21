/**
 * Photo gallery, upload and moderation functionality
 */

let currentPhotoIndex = 0;
let uploadingPhoto = false;

// ============================================================
// Автозавантаження модерації при відкритті адмін-табу
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const adminContent = document.getElementById('adminContent');
    if (!adminContent) return;

    // Спостерігаємо зміни class — коли таб стає active, завантажуємо модерацію
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'class' && adminContent.classList.contains('active')) {
                loadPhotoModeration();
            }
        });
    });
    observer.observe(adminContent, { attributes: true });

    // Якщо адмін вже активний при завантаженні
    if (adminContent.classList.contains('active')) {
        loadPhotoModeration();
    }
});


// ============================================================
// Модерація
// ============================================================

/**
 * Завантажити фото на модерацію (адмін)
 */
async function loadPhotoModeration() {
    const container = document.getElementById('photoModeration');
    if (!container) return;

    container.innerHTML = '<div class="loader">Завантаження...</div>';

    try {
        const uid = typeof userId !== 'undefined' ? userId : 0;
        const response = await fetch(`/api/photos/moderation/pending?user_id=${uid}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (!data.success) {
            container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div>Помилка: ${data.message || 'Невідома'}</div>`;
            return;
        }

        if (!data.photos || data.photos.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div>Немає фото на модерацію</div>';
            return;
        }

        container.innerHTML = data.photos.map(photo => `
            <div class="moderation-item" id="mod-${photo.id}">
                <img src="/static/${photo.file_path}"
                     alt="Фото ${photo.article}"
                     class="moderation-photo"
                     onerror="this.src=''; this.alt='✖ Фото не знайдено'">
                <div class="moderation-details">
                    <strong>${photo.article}</strong> &mdash; ${photo.product_name}<br>
                    👤 ${photo.uploaded_by} &bull; 📅 ${photo.uploaded_at}<br>
                    💾 ${(photo.file_size / 1024).toFixed(0)} KB
                    (з ${(photo.original_size / 1024).toFixed(0)} KB)
                </div>
                <div class="moderation-actions">
                    <button class="btn btn-success" onclick="moderatePhoto(${photo.id}, 'approved')">✅ Схвалити</button>
                    <button class="btn btn-danger"  onclick="moderatePhoto(${photo.id}, 'rejected')">❌ Відхилити</button>
                </div>
            </div>
        `).join('');

    } catch (error) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div>Помилка: ${error.message}</div>`;
        console.error('❌ loadPhotoModeration error:', error);
    }
}

/**
 * Схвалити або відхилити фото
 */
async function moderatePhoto(photoId, status) {
    try {
        const formData = new FormData();
        formData.append('status', status);
        formData.append('user_id', typeof userId !== 'undefined' ? userId : 0);

        if (status === 'rejected') {
            const reason = prompt('Причина відхилення (необов’язково):');
            if (reason) formData.append('reason', reason);
        }

        const response = await fetch(`/api/photos/moderation/${photoId}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            // Видаляємо картку з анімацією
            const card = document.getElementById(`mod-${photoId}`);
            if (card) {
                card.style.transition = 'opacity 0.3s, transform 0.3s';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    card.remove();
                    // Показати порожню статистику якщо більше нічого немає
                    const container = document.getElementById('photoModeration');
                    if (container && container.querySelectorAll('.moderation-item').length === 0) {
                        container.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div>Немає фото на модерацію</div>';
                    }
                }, 300);
            }

            if (typeof tg !== 'undefined' && tg.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
        } else {
            if (typeof tg !== 'undefined') tg.showAlert('❌ ' + (data.message || 'Помилка'));
        }
    } catch (error) {
        console.error('❌ moderatePhoto error:', error);
        if (typeof tg !== 'undefined') tg.showAlert('❌ Помилка: ' + error.message);
    }
}


// ============================================================
// Галерея та завантаження фото
// ============================================================

function openModalWithPhotos(product) {
    selectedProduct = product;
    currentQuantity = 1;
    currentPhotoIndex = 0;

    document.getElementById('modalTitle').textContent = product.article;
    document.getElementById('modalPrice').textContent = `Ціна: ${product.price.toFixed(2)} грн`;
    document.getElementById('modalAvailable').textContent = `Доступно: ${product.available} шт.`;

    const modalContent = document.querySelector('#addModal .modal-content');

    // Видаляємо старі елементи
    const existingGallery = modalContent.querySelector('.photo-gallery');
    if (existingGallery) existingGallery.remove();
    const existingPhotoBtn = modalContent.querySelector('.add-photo-btn');
    if (existingPhotoBtn) existingPhotoBtn.remove();

    // Галерея (якщо є фото)
    if (product.photos && product.photos.length > 0) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = createPhotoGallery(product);
        modalContent.insertBefore(tempDiv.firstElementChild, modalContent.querySelector('.quick-actions'));
    }

    // Кнопка додавання фото
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = createPhotoButton(product);
    modalContent.insertBefore(tempDiv.firstElementChild, modalContent.querySelector('.cancel-btn'));

    document.getElementById('qtyDisplay').textContent = 1;
    document.getElementById('customInputBox').style.display = 'none';
    document.getElementById('normalSelector').style.display = 'block';
    document.getElementById('customQtyInput').value = '';

    document.getElementById('addModal').classList.add('active');
}

function createPhotoGallery(product) {
    const hasMultiple = product.photos.length > 1;
    return `
        <div class="photo-gallery" id="photoGallery">
            <img src="/static/uploads/photos/${product.article}/${product.photos[0]}"
                 alt="Фото товару"
                 class="product-photo"
                 id="currentPhoto"
                 onclick="fullscreenPhoto(event)">
            <div class="photo-nav">
                ${hasMultiple ? `<button class="photo-nav-btn" onclick="previousPhoto(event)">◄</button>` : ''}
                <span class="photo-counter" id="photoCounter">1/${product.photos.length}</span>
                ${hasMultiple ? `<button class="photo-nav-btn" onclick="nextPhoto(event)">►</button>` : ''}
            </div>
        </div>`;
}

function createPhotoButton(product) {
    const count = product.photos ? product.photos.length : 0;
    const canAdd = count < 3;
    return `
        <button class="add-photo-btn ${!canAdd ? 'disabled' : ''}"
                id="addPhotoBtn"
                ${!canAdd ? 'disabled' : 'onclick="openPhotoUpload(event)"'}>
            📷 ${count > 0 ? `Додати ще фото (${count}/3)` : 'Додати фото (0/3)'}
        </button>`;
}

function previousPhoto(e) {
    e.stopPropagation();
    if (!selectedProduct.photos || selectedProduct.photos.length <= 1) return;
    currentPhotoIndex = (currentPhotoIndex - 1 + selectedProduct.photos.length) % selectedProduct.photos.length;
    updatePhotoDisplay();
    if (typeof tg !== 'undefined' && tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
}

function nextPhoto(e) {
    e.stopPropagation();
    if (!selectedProduct.photos || selectedProduct.photos.length <= 1) return;
    currentPhotoIndex = (currentPhotoIndex + 1) % selectedProduct.photos.length;
    updatePhotoDisplay();
    if (typeof tg !== 'undefined' && tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
}

function updatePhotoDisplay() {
    const img = document.getElementById('currentPhoto');
    const counter = document.getElementById('photoCounter');
    if (img && selectedProduct.photos) {
        img.src = `/static/uploads/photos/${selectedProduct.article}/${selectedProduct.photos[currentPhotoIndex]}`;
        if (counter) counter.textContent = `${currentPhotoIndex + 1}/${selectedProduct.photos.length}`;
    }
}

function fullscreenPhoto(e) {
    e.stopPropagation();
    const img = e.target;
    const fn = img.requestFullscreen || img.webkitRequestFullscreen || img.mozRequestFullScreen;
    if (fn) fn.call(img);
}

async function openPhotoUpload(e) {
    e.stopPropagation();
    if (uploadingPhoto) {
        if (typeof tg !== 'undefined') tg.showAlert('⏳ Зачекайте, попереднє фото ще завантажується');
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
            if (typeof tg !== 'undefined') tg.showAlert('❌ Оберіть файл зображення');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            if (typeof tg !== 'undefined') tg.showAlert('❌ Файл занадто великий (макс 10MB)');
            return;
        }
        await uploadPhoto(file);
    };
    input.click();
}

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
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Завантаження...'; }

    try {
        const formData = new FormData();
        formData.append('photo', file);
        formData.append('article', selectedProduct.article);
        formData.append('user_id', userId);

        const response = await fetch('/api/photos/upload', { method: 'POST', body: formData });
        const data = await response.json();

        if (data.success) {
            if (typeof tg !== 'undefined') {
                tg.showAlert('✅ Фото надіслано на модерацію');
                if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
            }
            selectedProduct.photos = data.photos || [];
            closeModal();
            setTimeout(() => openModalWithPhotos(selectedProduct), 300);
        } else {
            if (typeof tg !== 'undefined') tg.showAlert('❌ ' + (data.message || 'Помилка завантаження'));
        }
    } catch (error) {
        if (typeof tg !== 'undefined') tg.showAlert('❌ Помилка: ' + error.message);
    } finally {
        uploadingPhoto = false;
    }
}

async function loadProductPhotos(article) {
    try {
        const response = await fetch(`/api/photos/product/${article}`);
        const data = await response.json();
        if (data.success) {
            return data.photos.map(p => p.file_path.split('/').pop());
        }
    } catch (error) {
        console.error('❌ Error loading photos:', error);
    }
    return [];
}
