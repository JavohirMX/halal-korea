// Enhanced Admin JavaScript for HalalPlace

document.addEventListener('DOMContentLoaded', function() {
    // Initialize enhanced admin features
    initializeEnhancedAdmin();
});

function initializeEnhancedAdmin() {
    // Add loading states to action buttons
    enhanceActionButtons();
    
    // Enhance the changelist table
    enhanceChangelistTable();
    
    // Add confirmation dialogs for destructive actions
    addConfirmationDialogs();
    
    // Enhance search functionality
    enhanceSearch();
    
    // Add keyboard shortcuts
    addKeyboardShortcuts();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Enhance form submissions
    enhanceFormSubmissions();
}

function enhanceActionButtons() {
    const actionButtons = document.querySelectorAll('input[type="submit"], button[type="submit"]');
    
    actionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (this.classList.contains('loading')) {
                e.preventDefault();
                return;
            }
            
            // Add loading state
            this.classList.add('loading');
            
            // Store original text
            const originalText = this.value || this.textContent;
            this.dataset.originalText = originalText;
            
            // Set loading text
            if (this.tagName === 'INPUT') {
                this.value = 'Processing...';
            } else {
                this.textContent = 'Processing...';
            }
            
            // Remove loading state after 10 seconds (safety net)
            setTimeout(() => {
                this.classList.remove('loading');
                if (this.tagName === 'INPUT') {
                    this.value = this.dataset.originalText;
                } else {
                    this.textContent = this.dataset.originalText;
                }
            }, 10000);
        });
    });
}

function enhanceChangelistTable() {
    const table = document.querySelector('.changelist-results table');
    if (!table) return;
    
    // Add enhanced class
    table.classList.add('admin-list-table');
    
    // Add hover effects to rows
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8fafc';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
    
    // Enhance status badges
    enhanceStatusBadges();
    
    // Add click-to-edit functionality for editable fields
    enhanceInlineEditing();
}

function enhanceStatusBadges() {
    const statusCells = document.querySelectorAll('td:has(select[name*="status"])');
    
    statusCells.forEach(cell => {
        const select = cell.querySelector('select');
        if (!select) return;
        
        const selectedValue = select.value;
        
        // Create visual badge
        const badge = document.createElement('span');
        badge.className = `status-badge status-${selectedValue}`;
        badge.textContent = select.options[select.selectedIndex].text;
        
        // Hide select and show badge
        select.style.display = 'none';
        cell.appendChild(badge);
        
        // Add click handler to show select
        badge.addEventListener('click', function() {
            badge.style.display = 'none';
            select.style.display = 'inline-block';
            select.focus();
        });
        
        // Handle select change
        select.addEventListener('change', function() {
            badge.className = `status-badge status-${this.value}`;
            badge.textContent = this.options[this.selectedIndex].text;
            badge.style.display = 'inline-block';
            this.style.display = 'none';
            
            // Auto-save if possible
            autoSaveInlineEdit(this);
        });
        
        // Handle blur to hide select
        select.addEventListener('blur', function() {
            badge.style.display = 'inline-block';
            this.style.display = 'none';
        });
    });
}

function enhanceInlineEditing() {
    const editableCells = document.querySelectorAll('td:has(input), td:has(select)');
    
    editableCells.forEach(cell => {
        const input = cell.querySelector('input, select');
        if (!input || input.type === 'checkbox') return;
        
        // Add change handler for auto-save
        input.addEventListener('change', function() {
            autoSaveInlineEdit(this);
        });
        
        // Add visual indicator for unsaved changes
        input.addEventListener('input', function() {
            this.style.backgroundColor = '#fef3c7';
            this.style.borderColor = '#f59e0b';
        });
    });
}

function autoSaveInlineEdit(element) {
    // Add visual feedback
    element.style.backgroundColor = '#dcfce7';
    element.style.borderColor = '#16a34a';
    
    // Reset styles after a delay
    setTimeout(() => {
        element.style.backgroundColor = '';
        element.style.borderColor = '';
    }, 1000);
    
    // Here you could add AJAX save functionality if needed
    console.log('Auto-saving field:', element.name, 'with value:', element.value);
}

function addConfirmationDialogs() {
    // Add confirmation to destructive actions
    const destructiveActions = [
        'delete_selected',
        'bulk_reject',
        'bulk_archive'
    ];
    
    const actionSelect = document.querySelector('select[name="action"]');
    if (actionSelect) {
        const goButton = document.querySelector('button[type="submit"]:has-text("Go")') || 
                        document.querySelector('input[type="submit"][value="Go"]');
        
        if (goButton) {
            goButton.addEventListener('click', function(e) {
                const selectedAction = actionSelect.value;
                const selectedItems = document.querySelectorAll('input[name="_selected_action"]:checked');
                
                if (destructiveActions.includes(selectedAction) && selectedItems.length > 0) {
                    const actionText = actionSelect.options[actionSelect.selectedIndex].text;
                    const count = selectedItems.length;
                    
                    if (!confirm(`Are you sure you want to ${actionText.toLowerCase()} ${count} item(s)? This action cannot be undone.`)) {
                        e.preventDefault();
                    }
                }
            });
        }
    }
}

function enhanceSearch() {
    const searchInput = document.querySelector('input[name="q"]');
    if (!searchInput) return;
    
    // Add search suggestions (if you have data)
    addSearchSuggestions(searchInput);
    
    // Add search history
    addSearchHistory(searchInput);
    
    // Add clear button
    addSearchClearButton(searchInput);
}

function addSearchSuggestions(searchInput) {
    // This could be enhanced with actual data from your backend
    const suggestions = [
        'status:pending',
        'category:restaurant',
        'category:mosque',
        'has:images',
        'no:images',
        'has:suggestions'
    ];
    
    searchInput.addEventListener('input', function() {
        const value = this.value.toLowerCase();
        if (value.length < 2) return;
        
        const matchingSuggestions = suggestions.filter(s => s.includes(value));
        showSearchSuggestions(this, matchingSuggestions);
    });
}

function showSearchSuggestions(input, suggestions) {
    // Remove existing suggestions
    const existingSuggestions = document.querySelector('.search-suggestions');
    if (existingSuggestions) {
        existingSuggestions.remove();
    }
    
    if (suggestions.length === 0) return;
    
    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'search-suggestions';
    suggestionsDiv.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 0 0 6px 6px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 1000;
        max-height: 200px;
        overflow-y: auto;
    `;
    
    suggestions.forEach(suggestion => {
        const item = document.createElement('div');
        item.textContent = suggestion;
        item.style.cssText = `
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #f0f0f0;
        `;
        
        item.addEventListener('click', function() {
            input.value = suggestion;
            suggestionsDiv.remove();
            input.form.submit();
        });
        
        item.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8fafc';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
        
        suggestionsDiv.appendChild(item);
    });
    
    // Position relative to input
    input.parentNode.style.position = 'relative';
    input.parentNode.appendChild(suggestionsDiv);
    
    // Close suggestions when clicking outside
    document.addEventListener('click', function closesuggestions(e) {
        if (!input.contains(e.target) && !suggestionsDiv.contains(e.target)) {
            suggestionsDiv.remove();
            document.removeEventListener('click', closeSuggestions);
        }
    });
}

function addSearchHistory(searchInput) {
    const historyKey = 'admin_search_history';
    const maxHistory = 10;
    
    // Load history from localStorage
    let history = JSON.parse(localStorage.getItem(historyKey) || '[]');
    
    // Save search on form submit
    searchInput.form.addEventListener('submit', function() {
        const searchTerm = searchInput.value.trim();
        if (searchTerm && !history.includes(searchTerm)) {
            history.unshift(searchTerm);
            history = history.slice(0, maxHistory);
            localStorage.setItem(historyKey, JSON.stringify(history));
        }
    });
    
    // Show history on focus (if empty)
    searchInput.addEventListener('focus', function() {
        if (!this.value && history.length > 0) {
            showSearchSuggestions(this, history);
        }
    });
}

function addSearchClearButton(searchInput) {
    if (!searchInput.value) return;
    
    const clearButton = document.createElement('button');
    clearButton.type = 'button';
    clearButton.innerHTML = '×';
    clearButton.style.cssText = `
        position: absolute;
        right: 8px;
        top: 50%;
        transform: translateY(-50%);
        background: none;
        border: none;
        font-size: 18px;
        color: #6b7280;
        cursor: pointer;
        padding: 0;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
    `;
    
    clearButton.addEventListener('click', function() {
        searchInput.value = '';
        searchInput.form.submit();
    });
    
    searchInput.parentNode.style.position = 'relative';
    searchInput.parentNode.appendChild(clearButton);
}

function addKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + / for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Escape to clear search
        if (e.key === 'Escape') {
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput && document.activeElement === searchInput) {
                searchInput.value = '';
            }
            
            // Close any open suggestions
            const suggestions = document.querySelector('.search-suggestions');
            if (suggestions) {
                suggestions.remove();
            }
        }
        
        // Ctrl/Cmd + A to select all checkboxes
        if ((e.ctrlKey || e.metaKey) && e.key === 'a' && e.target.tagName !== 'INPUT') {
            const selectAllCheckbox = document.querySelector('#action-toggle');
            if (selectAllCheckbox) {
                e.preventDefault();
                selectAllCheckbox.click();
            }
        }
    });
}

function initializeTooltips() {
    // Add tooltips to various elements
    const elementsWithTooltips = [
        { selector: '.status-badge', attribute: 'title', text: 'Click to edit status' },
        { selector: '.image-count-display', attribute: 'title', text: 'Number of images for this place' },
        { selector: '.suggestion-count', attribute: 'title', text: 'Pending/approved suggestions' }
    ];
    
    elementsWithTooltips.forEach(({ selector, attribute, text }) => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(element => {
            if (!element.getAttribute(attribute)) {
                element.setAttribute(attribute, text);
            }
        });
    });
}

function enhanceFormSubmissions() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            // Disable submit buttons to prevent double submission
            const submitButtons = form.querySelectorAll('input[type="submit"], button[type="submit"]');
            submitButtons.forEach(button => {
                button.disabled = true;
                button.classList.add('loading');
            });
            
            // Re-enable after 5 seconds (safety net)
            setTimeout(() => {
                submitButtons.forEach(button => {
                    button.disabled = false;
                    button.classList.remove('loading');
                });
            }, 5000);
        });
    });
}

// Utility functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        font-weight: 500;
        max-width: 300px;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Export functions for use in other scripts
window.adminEnhancements = {
    showNotification,
    autoSaveInlineEdit,
    enhanceStatusBadges
};