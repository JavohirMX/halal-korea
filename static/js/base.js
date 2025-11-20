/**
 * Base JavaScript - Extracted from base.html
 * Handles theme toggling, message notifications, and email verification notices
 */

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    initializeMessages();
    initializeEmailVerificationNotice();
});

/**
 * Initialize message handling and auto-dismissal
 */
function initializeMessages() {
    const messages = document.querySelectorAll('.message');
    
    // Auto-dismiss messages after 5 seconds
    messages.forEach(message => {
        setTimeout(() => {
            dismissMessage(message);
        }, 5000);
    });

    // Handle manual dismissal
    document.querySelectorAll('.close-message').forEach(button => {
        button.addEventListener('click', () => {
            const message = button.closest('.message');
            dismissMessage(message);
        });
    });
}

/**
 * Dismiss a message with fade animation
 * @param {HTMLElement} message - The message element to dismiss
 */
function dismissMessage(message) {
    if (!message) return;
    
    message.style.opacity = '0';
    setTimeout(() => {
        message.remove();
    }, 300);
}

/**
 * Initialize email verification notice dismissal
 */
function initializeEmailVerificationNotice() {
    document.querySelectorAll('.close-verification-notice').forEach(button => {
        button.addEventListener('click', () => {
            const notice = button.closest('div[class*="bg-yellow-50"]');
            if (notice) {
                notice.style.opacity = '0';
                setTimeout(() => {
                    notice.remove();
                }, 300);
            }
        });
    });
}

/**
 * Toggle between light and dark theme
 * Saves preference to localStorage and reloads page if map is present
 */
window.toggleTheme = function() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.theme = isDark ? 'dark' : 'light';
    
    // Check if there's a map on the page
    const hasMap = typeof map !== 'undefined' || 
                   typeof desktopMap !== 'undefined' || 
                   typeof mobileMap !== 'undefined';
    
    // If map exists, reload the page to apply new theme to map
    if (hasMap) {
        location.reload();
    }
    
    // Animate icon
    const icon = document.querySelector('.theme-toggle-icon');
    if (icon) {
        icon.classList.add('rotate');
        setTimeout(() => icon.classList.remove('rotate'), 500);
    }
}

/**
 * Utility function to detect current theme and return appropriate ColorScheme
 * Used by Google Maps initialization
 * @returns {string} - 'DARK' or 'LIGHT' color scheme for Google Maps
 */
window.getMapColorScheme = function() {
    if (typeof google === 'undefined' || !google.maps || !google.maps.ColorScheme) {
        return null;
    }
    
    const isDark = document.documentElement.classList.contains('dark');
    return isDark ? google.maps.ColorScheme.DARK : google.maps.ColorScheme.LIGHT;
}
