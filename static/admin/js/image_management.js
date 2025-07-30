// Image Management JavaScript for HalalPlace Admin

document.addEventListener('DOMContentLoaded', function() {
    initializeImageManagement();
});

function initializeImageManagement() {
    // Enhance image preview grid in the admin form
    enhanceImagePreviewGrid();
    
    // Add drag-and-drop functionality to image URLs field
    enhanceImageUrlsField();
    
    // Add image validation
    addImageValidation();
    
    // Initialize image loading states
    initializeImageLoadingStates();
}

function enhanceImagePreviewGrid() {
    const imageGrid = document.querySelector('.field-image_preview_grid');
    if (!imageGrid) return;
    
    // Add image management buttons to each image
    const images = imageGrid.querySelectorAll('img');
    images.forEach((img, index) => {
        enhanceImagePreview(img, index);
    });
    
    // Add bulk image actions
    addBulkImageActions(imageGrid);
}

function enhanceImagePreview(img, index) {
    const container = img.parentElement;
    
    // Create wrapper with controls
    const wrapper = document.createElement('div');
    wrapper.className = 'image-preview-wrapper';
    wrapper.style.cssText = `
        position: relative;
        display: inline-block;
        margin: 5px;
        border-radius: 8px;
        overflow: hidden;
        transition: transform 0.2s ease;
    `;
    
    // Create controls overlay
    const controls = document.createElement('div');
    controls.className = 'image-controls';
    controls.style.cssText = `
        position: absolute;
        top: 0;
        right: 0;
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 4px;
        border-radius: 0 0 0 8px;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    
    // Add control buttons
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.innerHTML = '🗑️';
    deleteBtn.style.cssText = `
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 14px;
        padding: 2px 4px;
        border-radius: 3px;
        transition: background 0.2s ease;
    `;
    deleteBtn.title = 'Delete image';
    
    deleteBtn.addEventListener('click', function() {
        deleteImageFromPreview(img, index);
    });
    
    deleteBtn.addEventListener('mouseenter', function() {
        this.style.background = '#ef4444';
    });
    
    deleteBtn.addEventListener('mouseleave', function() {
        this.style.background = 'none';
    });
    
    controls.appendChild(deleteBtn);
    
    // Add move buttons for reordering
    const moveUpBtn = document.createElement('button');
    moveUpBtn.type = 'button';
    moveUpBtn.innerHTML = '⬆️';
    moveUpBtn.style.cssText = deleteBtn.style.cssText;
    moveUpBtn.title = 'Move up';
    moveUpBtn.addEventListener('click', function() {
        moveImageInPreview(img, index, -1);
    });
    
    const moveDownBtn = document.createElement('button');
    moveDownBtn.type = 'button';
    moveDownBtn.innerHTML = '⬇️';
    moveDownBtn.style.cssText = deleteBtn.style.cssText;
    moveDownBtn.title = 'Move down';
    moveDownBtn.addEventListener('click', function() {
        moveImageInPreview(img, index, 1);
    });
    
    if (index > 0) controls.appendChild(moveUpBtn);
    if (index < document.querySelectorAll('.field-image_preview_grid img').length - 1) {
        controls.appendChild(moveDownBtn);
    }
    
    // Add order number
    const orderNumber = document.createElement('div');
    orderNumber.textContent = index + 1;
    orderNumber.style.cssText = `
        position: absolute;
        top: 4px;
        left: 4px;
        background: rgba(0,0,0,0.8);
        color: white;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: bold;
    `;
    
    // Wrap image and add controls
    container.insertBefore(wrapper, img);
    wrapper.appendChild(img);
    wrapper.appendChild(controls);
    wrapper.appendChild(orderNumber);
    
    // Show controls on hover
    wrapper.addEventListener('mouseenter', function() {
        controls.style.opacity = '1';
    });
    
    wrapper.addEventListener('mouseleave', function() {
        controls.style.opacity = '0';
    });
    
    // Add hover effect
    wrapper.addEventListener('mouseenter', function() {
        this.style.transform = 'scale(1.05)';
    });
    
    wrapper.addEventListener('mouseleave', function() {
        this.style.transform = 'scale(1)';
    });
}

function deleteImageFromPreview(img, index) {
    if (!confirm('Remove this image? This will update the photo URLs field.')) return;
    
    const photoUrlsField = document.querySelector('textarea[name="photo_urls"]');
    if (!photoUrlsField) return;
    
    try {
        let urls = JSON.parse(photoUrlsField.value || '[]');
        urls.splice(index, 1);
        photoUrlsField.value = JSON.stringify(urls);
        
        // Remove from preview
        img.closest('.image-preview-wrapper').remove();
        
        // Update order numbers
        updateImageOrderNumbers();
        
        showImageMessage('Image removed successfully', 'success');
    } catch (error) {
        showImageMessage('Error removing image', 'error');
    }
}

function moveImageInPreview(img, currentIndex, direction) {
    const photoUrlsField = document.querySelector('textarea[name="photo_urls"]');
    if (!photoUrlsField) return;
    
    try {
        let urls = JSON.parse(photoUrlsField.value || '[]');
        const newIndex = currentIndex + direction;
        
        if (newIndex < 0 || newIndex >= urls.length) return;
        
        // Swap URLs
        [urls[currentIndex], urls[newIndex]] = [urls[newIndex], urls[currentIndex]];
        photoUrlsField.value = JSON.stringify(urls);
        
        // Update preview
        const wrapper = img.closest('.image-preview-wrapper');
        const targetWrapper = direction > 0 ? wrapper.nextElementSibling : wrapper.previousElementSibling;
        
        if (targetWrapper) {
            if (direction > 0) {
                targetWrapper.parentNode.insertBefore(wrapper, targetWrapper.nextSibling);
            } else {
                targetWrapper.parentNode.insertBefore(wrapper, targetWrapper);
            }
        }
        
        // Update order numbers
        updateImageOrderNumbers();
        
        showImageMessage('Image reordered successfully', 'success');
    } catch (error) {
        showImageMessage('Error reordering image', 'error');
    }
}

function updateImageOrderNumbers() {
    const orderNumbers = document.querySelectorAll('.field-image_preview_grid .image-preview-wrapper > div:last-child');
    orderNumbers.forEach((orderDiv, index) => {
        orderDiv.textContent = index + 1;
    });
}

function addBulkImageActions(imageGrid) {
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'bulk-image-actions';
    actionsDiv.style.cssText = `
        margin-top: 10px;
        padding: 10px;
        background: #f8fafc;
        border-radius: 6px;
        border: 1px solid #e2e8f0;
    `;
    
    const title = document.createElement('h4');
    title.textContent = 'Image Management';
    title.style.marginBottom = '10px';
    
    const addImageBtn = document.createElement('button');
    addImageBtn.type = 'button';
    addImageBtn.textContent = '➕ Add Image URL';
    addImageBtn.className = 'btn-enhanced btn-primary-enhanced';
    addImageBtn.addEventListener('click', showAddImageDialog);
    
    const validateBtn = document.createElement('button');
    validateBtn.type = 'button';
    validateBtn.textContent = '🔍 Validate Images';
    validateBtn.className = 'btn-enhanced btn-secondary-enhanced';
    validateBtn.style.marginLeft = '10px';
    validateBtn.addEventListener('click', validateAllImages);
    
    const optimizeBtn = document.createElement('button');
    optimizeBtn.type = 'button';
    optimizeBtn.textContent = '⚡ Optimize URLs';
    optimizeBtn.className = 'btn-enhanced btn-secondary-enhanced';
    optimizeBtn.style.marginLeft = '10px';
    optimizeBtn.addEventListener('click', optimizeImageUrls);
    
    actionsDiv.appendChild(title);
    actionsDiv.appendChild(addImageBtn);
    actionsDiv.appendChild(validateBtn);
    actionsDiv.appendChild(optimizeBtn);
    
    imageGrid.appendChild(actionsDiv);
}

function showAddImageDialog() {
    const url = prompt('Enter image URL:');
    if (!url) return;
    
    if (!isValidImageUrl(url)) {
        showImageMessage('Please enter a valid image URL', 'error');
        return;
    }
    
    const photoUrlsField = document.querySelector('textarea[name="photo_urls"]');
    if (!photoUrlsField) return;
    
    try {
        let urls = JSON.parse(photoUrlsField.value || '[]');
        urls.push(url);
        photoUrlsField.value = JSON.stringify(urls);
        
        // Refresh the preview (simple reload for now)
        showImageMessage('Image URL added. Save the form to see the preview.', 'success');
    } catch (error) {
        showImageMessage('Error adding image URL', 'error');
    }
}

function validateAllImages() {
    const photoUrlsField = document.querySelector('textarea[name="photo_urls"]');
    if (!photoUrlsField) return;
    
    try {
        let urls = JSON.parse(photoUrlsField.value || '[]');
        let validUrls = [];
        let invalidCount = 0;
        
        urls.forEach(url => {
            if (isValidImageUrl(url)) {
                validUrls.push(url);
            } else {
                invalidCount++;
            }
        });
        
        if (invalidCount > 0) {
            if (confirm(`Found ${invalidCount} invalid URL(s). Remove them?`)) {
                photoUrlsField.value = JSON.stringify(validUrls);
                showImageMessage(`Removed ${invalidCount} invalid URL(s)`, 'success');
            }
        } else {
            showImageMessage('All image URLs are valid', 'success');
        }
    } catch (error) {
        showImageMessage('Error validating images', 'error');
    }
}

function optimizeImageUrls() {
    const photoUrlsField = document.querySelector('textarea[name="photo_urls"]');
    if (!photoUrlsField) return;
    
    try {
        let urls = JSON.parse(photoUrlsField.value || '[]');
        let optimizedUrls = [];
        let optimizedCount = 0;
        
        urls.forEach(url => {
            let optimizedUrl = url;
            
            // Remove query parameters that might not be needed
            if (url.includes('?')) {
                const baseUrl = url.split('?')[0];
                if (baseUrl.match(/\.(jpg|jpeg|png|gif|webp)$/i)) {
                    optimizedUrl = baseUrl;
                    optimizedCount++;
                }
            }
            
            // Remove duplicate slashes
            optimizedUrl = optimizedUrl.replace(/([^:]\/)\/+/g, '$1');
            
            optimizedUrls.push(optimizedUrl);
        });
        
        // Remove duplicates
        const uniqueUrls = [...new Set(optimizedUrls)];
        const duplicatesRemoved = optimizedUrls.length - uniqueUrls.length;
        
        photoUrlsField.value = JSON.stringify(uniqueUrls);
        
        let message = 'URLs optimized';
        if (optimizedCount > 0) message += ` (cleaned ${optimizedCount} URLs)`;
        if (duplicatesRemoved > 0) message += ` (removed ${duplicatesRemoved} duplicates)`;
        
        showImageMessage(message, 'success');
    } catch (error) {
        showImageMessage('Error optimizing URLs', 'error');
    }
}

function enhanceImageUrlsField() {
    const photoUrlsField = document.querySelector('textarea[name="photo_urls"]');
    if (!photoUrlsField) return;
    
    // Add format validation on change
    photoUrlsField.addEventListener('change', function() {
        try {
            const urls = JSON.parse(this.value || '[]');
            if (!Array.isArray(urls)) {
                throw new Error('Must be an array');
            }
            
            // Validate each URL
            const invalidUrls = urls.filter(url => !isValidImageUrl(url));
            if (invalidUrls.length > 0) {
                showImageMessage(`Warning: ${invalidUrls.length} invalid URL(s) detected`, 'warning');
            }
            
            this.style.borderColor = '#10b981';
            this.style.backgroundColor = '#f0fdf4';
        } catch (error) {
            this.style.borderColor = '#ef4444';
            this.style.backgroundColor = '#fef2f2';
            showImageMessage('Invalid JSON format', 'error');
        }
    });
    
    // Add helpful placeholder
    if (!photoUrlsField.value || photoUrlsField.value.trim() === '') {
        photoUrlsField.placeholder = '["https://example.com/image1.jpg", "https://example.com/image2.jpg"]';
    }
    
    // Add format helper
    const helper = document.createElement('div');
    helper.style.cssText = `
        margin-top: 5px;
        font-size: 12px;
        color: #6b7280;
        line-height: 1.4;
    `;
    helper.innerHTML = `
        <strong>Format:</strong> JSON array of image URLs<br>
        <strong>Example:</strong> ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
    `;
    
    photoUrlsField.parentNode.appendChild(helper);
}

function addImageValidation() {
    // Add validation for image URLs in forms
    const imageInputs = document.querySelectorAll('input[type="url"][name*="image"], input[type="text"][name*="photo"]');
    
    imageInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !isValidImageUrl(this.value)) {
                this.style.borderColor = '#ef4444';
                this.style.backgroundColor = '#fef2f2';
                
                // Show validation message
                let errorMsg = this.parentNode.querySelector('.validation-error');
                if (!errorMsg) {
                    errorMsg = document.createElement('div');
                    errorMsg.className = 'validation-error';
                    errorMsg.style.cssText = `
                        color: #ef4444;
                        font-size: 12px;
                        margin-top: 3px;
                    `;
                    this.parentNode.appendChild(errorMsg);
                }
                errorMsg.textContent = 'Please enter a valid image URL';
            } else {
                this.style.borderColor = '';
                this.style.backgroundColor = '';
                
                const errorMsg = this.parentNode.querySelector('.validation-error');
                if (errorMsg) {
                    errorMsg.remove();
                }
            }
        });
    });
}

function initializeImageLoadingStates() {
    // Add loading states for images
    const images = document.querySelectorAll('.field-image_preview_grid img');
    
    images.forEach(img => {
        // Add loading indicator
        const loader = document.createElement('div');
        loader.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 20px;
            height: 20px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        `;
        
        // Show loader while image loads
        if (!img.complete) {
            const wrapper = img.parentElement;
            if (wrapper) {
                wrapper.style.position = 'relative';
                wrapper.appendChild(loader);
            }
        }
        
        img.addEventListener('load', function() {
            if (loader.parentNode) {
                loader.remove();
            }
        });
        
        img.addEventListener('error', function() {
            if (loader.parentNode) {
                loader.remove();
            }
            
            // Add error indicator
            const errorDiv = document.createElement('div');
            errorDiv.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(239, 68, 68, 0.9);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                text-align: center;
            `;
            errorDiv.innerHTML = '⚠️<br>Failed to load';
            
            const wrapper = this.parentElement;
            if (wrapper) {
                wrapper.style.position = 'relative';
                wrapper.appendChild(errorDiv);
            }
        });
    });
}

// Utility functions
function isValidImageUrl(url) {
    if (!url || typeof url !== 'string') return false;
    
    // Check if it's a valid URL format
    try {
        new URL(url);
    } catch {
        // Allow relative URLs starting with /
        if (!url.startsWith('/')) return false;
    }
    
    // Check if it looks like an image URL
    const imageExtensions = /\.(jpg|jpeg|png|gif|webp|svg|bmp|tiff)(\?.*)?$/i;
    return imageExtensions.test(url) || url.includes('image') || url.includes('photo');
}

function showImageMessage(message, type = 'info') {
    // Remove existing messages
    const existingMessage = document.querySelector('.image-message');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'image-message';
    messageDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 16px;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        z-index: 9999;
        max-width: 300px;
        font-size: 14px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateX(100%)';
        setTimeout(() => messageDiv.remove(), 300);
    }, 3000);
}

// Add CSS animations
if (!document.querySelector('#image-management-styles')) {
    const styles = document.createElement('style');
    styles.id = 'image-management-styles';
    styles.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .image-preview-wrapper {
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .image-preview-wrapper:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .image-message {
            transition: opacity 0.3s ease, transform 0.3s ease;
        }
    `;
    document.head.appendChild(styles);
}

// Export functions for external use
window.imageManagement = {
    isValidImageUrl,
    showImageMessage,
    validateAllImages,
    optimizeImageUrls
};