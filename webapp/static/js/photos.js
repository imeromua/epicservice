/**
 * Photo gallery, upload and moderation functionality
 */

let currentPhotoIndex = 0;
let uploadingPhoto = false;
let currentModerationPhoto = null;

// ============================================================
// Автозавантаження модерації при відкритті адмін-табу
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const adminContent = document.getElementById('adminContent');
    if (adminContent) {
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
    }

    // Автозавантаження модерації для вкладки модератора
    const moderationContent = document.getElementById('moderationContent');
    if (moderationContent) {
        const modObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class' && moderationContent.classList.contains('active')) {
                    loadModeratorPhotoModeration();
                }
            });
        });
        modObserver.observe(moderationContent, { attributes: true });

        if (moderationContent.classList.contains('active')) {
            loadModeratorPhotoModeration();
        }
    }
});


// ============================================================
// Утиліти
// ============================================================

/**
 * Безпечний парсинг JSON відповіді з діагностикою
 */
async function safeParseResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    const raw = await response.text();

    try {
        return JSON.parse(raw);
    } catch (e) {
        const snippet = raw.slice(0, 300).replace(/\s+/g, ' ');
        throw new Error(`Не JSON. HTTP ${response.status}. Content-Type: ${contentType}. Відповідь: ${snippet}`);
    }
}

/**
 * Стиснення фото перед upload (до 1920px, JPEG quality 0.85)
 */
async function compressImage(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // Розрахунок нових розмірів (макс 1920px по довгій стороні)
                const maxSize = 1920;
                let width = img.width;
                let height = img.height;
                
                if (width > height && width > maxSize) {
                    height = Math.round((height * maxSize) / width);
                    width = maxSize;
                } else if (height > maxSize) {
                    width = Math.round((width * maxSize) / height);
                    height = maxSize;
                }
                
                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);
                
                canvas.toBlob(
                    (blob) => {
                        if (blob) {
                            resolve(new File([blob], file.name, { type: 'image/jpeg' }));
                        } else {
                            reject(new Error('Не вдалося стиснути фото'));
                        }
                    },
                    'image/jpeg',
                    0.85
                );
            };
            img.onerror = () => reject(new Error('Не вдалося завантажити зображення'));
            img.src = e.target.result;
        };
        reader.onerror = () => reject(new Error('Не вдалося прочитати файл'));
        reader.readAsDataURL(file);
    });
}


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
        const data = await safeParseResponse(response);

        if (!data.success) {
            container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div>Помилка: ${data.message || data.detail || 'Невідома'}</div>`;
            return;
        }

        if (!data.photos || data.photos.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div>Немає фото на модерацію</div>';
            return;
        }

        // Горизонтальний список карток (кожен рядок окремий div для ellipsis)
        container.innerHTML = `
            <div class="moderation-horizontal-list">
                ${data.photos.map(photo => {
                    // Екранування спецсимволів для безпечної вставки в HTML onclick
                    const escapedArticle = (photo.article || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const escapedName = (photo.product_name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const escapedUser = (photo.uploaded_by || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const escapedDate = (photo.uploaded_at || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    
                    return `
                    <div class="moderation-card" id="mod-${photo.id}" onclick="openModerationPopup(${photo.id}, '/static/${photo.file_path}', '${escapedArticle}', '${escapedName}', '${escapedUser}', '${escapedDate}', ${photo.file_size})">
                        <img src="/static/${photo.file_path}" 
                             alt="Фото ${escapedArticle}"
                             class="moderation-card-thumb"
                             loading="lazy"
                             onerror="this.src=''; this.alt='✖'">
                        <div class="moderation-card-info">
                            <div class="info-line"><strong>${photo.article}</strong></div>
                            <div class="info-line">${photo.product_name}</div>
                            <div class="info-line">👤 ${photo.uploaded_by}</div>
                            <div class="info-line">📅 ${photo.uploaded_at}</div>
                            <div class="info-line">💾 ${(photo.file_size / 1024).toFixed(0)} KB</div>
                        </div>
                    </div>
                `;
                }).join('')}
            </div>
        `;

    } catch (error) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div>Помилка: ${error.message}</div>`;
        console.error('❌ loadPhotoModeration error:', error);
    }
}

/**
 * Відкрити попап з повним фото + кнопки дій
 */
function openModerationPopup(photoId, src, article, name, uploadedBy, uploadedAt, fileSize) {
    currentModerationPhoto = photoId;
    
    // Створюємо або оновлюємо попап
    let modal = document.getElementById('moderationPopup');
    if (!modal) {
        const temp = document.createElement('div');
        temp.innerHTML = `
            <div id="moderationPopup" class="modal moderation-popup">
                <div class="moderation-popup-content">
                    <button class="close-btn" onclick="closeModerationPopup()">×</button>
                    <div class="moderation-popup-photo">
                        <img id="moderationPopupImage" src="" alt="Прев'ю" loading="lazy">
                    </div>
                    <div class="moderation-popup-info" id="moderationPopupInfo"></div>
                    <div class="moderation-popup-actions">
                        <button class="btn btn-success btn-large" onclick="moderatePhotoFromPopup('approved')">✅ Схвалити</button>
                        <button class="btn btn-danger btn-large" onclick="moderatePhotoFromPopup('rejected')">❌ Відхилити</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(temp.firstElementChild);
        modal = document.getElementById('moderationPopup');
    }
    
    document.getElementById('moderationPopupImage').src = src;
    document.getElementById('moderationPopupInfo').innerHTML = `
        <div style="font-size:15px; font-weight:700; margin-bottom:4px">${article}</div>
        <div style="font-size:13px; opacity:0.85; margin-bottom:8px">${name}</div>
        <div style="display:flex; gap:12px; font-size:12px; opacity:0.6; flex-wrap: wrap">
            <span>👤 ${uploadedBy}</span>
            <span>📅 ${uploadedAt}</span>
            <span>💾 ${(fileSize / 1024).toFixed(0)} KB</span>
        </div>
    `;
    
    modal.classList.add('active');
}

function closeModerationPopup() {
    const modal = document.getElementById('moderationPopup');
    if (modal) modal.classList.remove('active');
    currentModerationPhoto = null;
}

/**
 * Модерація фото з попапу
 */
async function moderatePhotoFromPopup(status) {
    if (!currentModerationPhoto) return;
    
    try {
        const formData = new FormData();
        formData.append('status', status);
        formData.append('user_id', typeof userId !== 'undefined' ? userId : 0);

        if (status === 'rejected') {
            const reasons = [
                'Розмите',
                'Дублікат',
                'Погана якість',
                'Не той товар',
                'Не читається',
                'Інше...'
            ];
            
            const choice = await new Promise((resolve) => {
                const reasonModal = document.createElement('div');
                reasonModal.className = 'modal active';
                reasonModal.innerHTML = `
                    <div class="modal-content reason-modal-content">
                        <h3>Причина відхилення</h3>
                        <div class="reason-buttons">
                            ${reasons.map((r, i) => `
                                <button class="btn btn-reason" 
                                        onclick="window.rejectReason='${r}'; this.closest('.modal').remove();">${r}</button>
                            `).join('')}
                        </div>
                        <button class="btn btn-outline" onclick="this.closest('.modal').remove()">Скасувати</button>
                    </div>
                `;
                document.body.appendChild(reasonModal);
                
                const checkInterval = setInterval(() => {
                    if (!document.body.contains(reasonModal)) {
                        clearInterval(checkInterval);
                        resolve(window.rejectReason || null);
                        delete window.rejectReason;
                    }
                }, 100);
            });
            
            if (!choice) return;
            
            let reason = choice;
            if (choice === 'Інше...') {
                reason = prompt('Вкажіть причину:');
                if (!reason) return;
            }
            
            formData.append('reason', reason);
        }

        const response = await fetch(`/api/photos/moderation/${currentModerationPhoto}`, {
            method: 'POST',
            body: formData
        });

        const data = await safeParseResponse(response);

        if (data.success) {
            closeModerationPopup();
            
            // Видаляємо картку з анімацією
            const card = document.getElementById(`mod-${currentModerationPhoto}`);
            if (card) {
                card.style.transition = 'opacity 0.3s, transform 0.3s';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    card.remove();
                    // Показати порожню статистику якщо більше нічого немає
                    const container = document.getElementById('photoModeration');
                    if (container && container.querySelectorAll('.moderation-card').length === 0) {
                        container.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div>Немає фото на модерацію</div>';
                    }
                }, 300);
            }

            if (typeof tg !== 'undefined' && tg.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
        } else {
            if (typeof tg !== 'undefined') tg.showAlert('❌ ' + (data.message || data.detail || 'Помилка'));
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
                 loading="lazy"
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

/**
 * Відкрити file picker для вибору фото
 * Android автоматично пропонує: Камера / Галерея / Файли
 */
async function openPhotoUpload(e) {
    e.stopPropagation();
    if (uploadingPhoto) {
        if (typeof tg !== 'undefined') tg.showAlert('⏳ Зачекайте, попереднє фото ще завантажується');
        return;
    }
    
    // Створюємо прихований file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*'; // Тільки зображення
    input.style.display = 'none';
    
    input.onchange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        // Валідація типу файлу
        if (!file.type.startsWith('image/')) {
            if (typeof tg !== 'undefined') {
                tg.showAlert('❌ Оберіть файл зображення (JPG, PNG, WebP)');
            } else {
                alert('❌ Оберіть файл зображення (JPG, PNG, WebP)');
            }
            return;
        }
        
        // Валідація розміру (макс 10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            if (typeof tg !== 'undefined') {
                tg.showAlert('❌ Файл занадто великий. Максимум 10 MB');
            } else {
                alert('❌ Файл занадто великий. Максимум 10 MB');
            }
            return;
        }
        
        await uploadPhoto(file);
        
        // Видаляємо input після використання
        input.remove();
    };
    
    // Додаємо input до DOM і клікаємо
    document.body.appendChild(input);
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
        // Стиснення фото перед upload
        const compressed = await compressImage(file);
        
        const formData = new FormData();
        formData.append('photo', compressed);
        formData.append('article', selectedProduct.article);
        formData.append('user_id', userId);

        const response = await fetch('/api/photos/upload', { method: 'POST', body: formData });
        const data = await safeParseResponse(response);

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
        console.error('❌ uploadPhoto error:', error);
    } finally {
        uploadingPhoto = false;
    }
}

async function loadProductPhotos(article) {
    try {
        const response = await fetch(`/api/photos/product/${article}`);
        const data = await safeParseResponse(response);
        if (data.success) {
            return data.photos.map(p => p.file_path.split('/').pop());
        }
    } catch (error) {
        console.error('❌ Error loading photos:', error);
    }
    return [];
}


// ============================================================
// Модерація для вкладки модератора
// ============================================================

/**
 * Завантажити фото на модерацію (вкладка модератора)
 */
async function loadModeratorPhotoModeration() {
    const container = document.getElementById('moderatorPhotoModeration');
    if (!container) return;

    container.innerHTML = '<div class="loader">Завантаження...</div>';

    try {
        const uid = typeof userId !== 'undefined' ? userId : 0;
        const response = await fetch(`/api/photos/moderation/pending?user_id=${uid}`);
        const data = await safeParseResponse(response);

        if (!data.success) {
            container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div>Помилка: ${data.message || data.detail || 'Невідома'}</div>`;
            return;
        }

        if (!data.photos || data.photos.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div>Немає фото на модерацію</div>';
            return;
        }

        container.innerHTML = `
            <div class="moderation-horizontal-list">
                ${data.photos.map(photo => {
                    const escapedArticle = (photo.article || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const escapedName = (photo.product_name || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const escapedUser = (photo.uploaded_by || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const escapedDate = (photo.uploaded_at || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    
                    return `
                    <div class="moderation-card" id="mod-${photo.id}" onclick="openModerationPopup(${photo.id}, '/static/${photo.file_path}', '${escapedArticle}', '${escapedName}', '${escapedUser}', '${escapedDate}', ${photo.file_size})">
                        <img src="/static/${photo.file_path}" 
                             alt="Фото ${escapedArticle}"
                             class="moderation-card-thumb"
                             loading="lazy"
                             onerror="this.src=''; this.alt='✖'">
                        <div class="moderation-card-info">
                            <div class="info-line"><strong>${photo.article}</strong></div>
                            <div class="info-line">${photo.product_name}</div>
                            <div class="info-line">👤 ${photo.uploaded_by}</div>
                            <div class="info-line">📅 ${photo.uploaded_at}</div>
                            <div class="info-line">💾 ${(photo.file_size / 1024).toFixed(0)} KB</div>
                        </div>
                    </div>
                `;
                }).join('')}
            </div>
        `;

    } catch (error) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div>Помилка: ${error.message}</div>`;
        console.error('❌ loadModeratorPhotoModeration error:', error);
    }
}
