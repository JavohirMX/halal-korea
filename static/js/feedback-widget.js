/**
 * Feedback Widget - Floating feedback collection system
 * Displays after user has been on site for a configurable time
 * Collects ratings, comments, and behavioral data
 */

class FeedbackWidget {
    constructor(config = {}) {
        // Configuration
        this.showDelay = config.showDelay || 150000; // 2.5 minutes in milliseconds
        this.checkInterval = 1000; // Check every second
        this.pulseInterval = 3000; // Pulse animation every 3 seconds
        
        // State tracking
        this.timeOnSite = 0;
        this.timeOnPage = 0;
        this.startTime = Date.now();
        this.pageStartTime = Date.now();
        this.hasInteracted = false;
        this.isVisible = false;
        this.isExpanded = false;
        this.selectedRating = 0;
        
        // Session tracking
        this.sessionId = this.getOrCreateSessionId();
        this.pagesVisited = this.incrementPageVisit();
        
        // Scroll tracking
        this.maxScrollDepth = 0;
        
        // DOM elements (will be created)
        this.widget = null;
        this.container = null;
        
        // Initialize
        this.init();
    }
    
    init() {
        // Check if should be disabled
        if (this.shouldDisable()) {
            return;
        }
        
        // Create widget DOM
        this.createWidget();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Start tracking
        this.startTracking();
    }
    
    shouldDisable() {
        // Check if permanently disabled
        if (localStorage.getItem('feedback_disabled') === 'true') {
            return true;
        }
        
        // Check if recently submitted (within 7 days)
        const lastSubmitted = localStorage.getItem('feedback_last_submitted');
        if (lastSubmitted) {
            const daysSince = (Date.now() - new Date(lastSubmitted)) / (1000 * 60 * 60 * 24);
            if (daysSince < 7) {
                return true;
            }
        }
        
        // Check if recently dismissed (within 24 hours)
        const lastDismissed = localStorage.getItem('feedback_last_dismissed');
        if (lastDismissed) {
            const hoursSince = (Date.now() - new Date(lastDismissed)) / (1000 * 60 * 60);
            if (hoursSince < 24) {
                return true;
            }
        }
        
        return false;
    }
    
    getOrCreateSessionId() {
        let sessionId = sessionStorage.getItem('feedback_session_id');
        if (!sessionId) {
            sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('feedback_session_id', sessionId);
        }
        return sessionId;
    }
    
    incrementPageVisit() {
        const count = parseInt(sessionStorage.getItem('feedback_pages_visited') || '0') + 1;
        sessionStorage.setItem('feedback_pages_visited', count);
        return count;
    }
    
    createWidget() {
        // Create main container
        this.container = document.createElement('div');
        this.container.id = 'feedback-widget-container';
        this.container.className = 'feedback-widget-container hidden';
        this.container.innerHTML = `
            <!-- Floating Button -->
            <div id="feedback-button" class="feedback-button">
                <i class="fas fa-comment-dots"></i>
                <span class="feedback-button-text">Feedback</span>
            </div>
            
            <!-- Expanded Form -->
            <div id="feedback-form" class="feedback-form hidden">
                <div class="feedback-form-header">
                    <h3 class="feedback-form-title"><span id="feedback-message">How's your experience?</span></h3>
                    <button id="feedback-close" class="feedback-close-btn" aria-label="Close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                
                <div class="feedback-form-body">
                    <!-- Star Rating -->
                    <div class="feedback-rating">
                        <div class="star-rating" id="star-rating">
                            <i class="far fa-star star" data-rating="1"></i>
                            <i class="far fa-star star" data-rating="2"></i>
                            <i class="far fa-star star" data-rating="3"></i>
                            <i class="far fa-star star" data-rating="4"></i>
                            <i class="far fa-star star" data-rating="5"></i>
                        </div>
                        <p class="rating-label" id="rating-label">Click to rate</p>
                    </div>
                    
                    <!-- Comment -->
                    <div class="feedback-comment">
                        <label for="feedback-comment-text" class="feedback-label">
                            💭 Tell us more (optional)
                        </label>
                        <textarea 
                            id="feedback-comment-text" 
                            class="feedback-textarea"
                            placeholder="What can we improve?"
                            maxlength="500"
                            rows="3"
                        ></textarea>
                        <span class="char-count" id="char-count">0/500</span>
                    </div>
                    
                    <!-- Actions -->
                    <div class="feedback-actions">
                        <button id="feedback-submit" class="feedback-submit-btn" disabled>
                            <i class="fas fa-paper-plane"></i> Send Feedback
                        </button>
                        <button id="feedback-later" class="feedback-later-btn">
                            Maybe Later
                        </button>
                    </div>
                    
                    <button id="feedback-disable" class="feedback-disable-link">
                        Don't show this again
                    </button>
                </div>
                
                <!-- Loading State -->
                <div id="feedback-loading" class="feedback-loading hidden">
                    <div class="spinner"></div>
                    <p>Submitting...</p>
                </div>
                
                <!-- Success State -->
                <div id="feedback-success" class="feedback-success hidden">
                    <div class="success-icon">✓</div>
                    <h3>Thank you!</h3>
                    <p>Your feedback helps us improve.</p>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.container);
        
        // Cache DOM references
        this.button = document.getElementById('feedback-button');
        this.form = document.getElementById('feedback-form');
        this.stars = document.querySelectorAll('.star');
        this.submitBtn = document.getElementById('feedback-submit');
        this.textarea = document.getElementById('feedback-comment-text');
    }
    
    setupEventListeners() {
        // Button click - expand form
        this.button?.addEventListener('click', () => this.expand());
        
        // Close button
        document.getElementById('feedback-close')?.addEventListener('click', () => this.collapse());
        
        // Star rating
        this.stars.forEach(star => {
            star.addEventListener('click', () => this.setRating(parseInt(star.dataset.rating)));
            star.addEventListener('mouseenter', () => this.hoverRating(parseInt(star.dataset.rating)));
        });
        
        document.getElementById('star-rating')?.addEventListener('mouseleave', () => {
            this.hoverRating(this.selectedRating);
        });
        
        // Character count
        this.textarea?.addEventListener('input', (e) => {
            const count = e.target.value.length;
            document.getElementById('char-count').textContent = `${count}/500`;
        });
        
        // Submit button
        this.submitBtn?.addEventListener('click', () => this.submit());
        
        // Later button
        document.getElementById('feedback-later')?.addEventListener('click', () => {
            this.dismiss();
        });
        
        // Disable button
        document.getElementById('feedback-disable')?.addEventListener('click', () => {
            if (confirm('Are you sure you don\'t want to see this feedback widget again?')) {
                this.disablePermanently();
            }
        });
        
        // Track user interaction
        ['click', 'scroll', 'keydown', 'mousemove'].forEach(event => {
            document.addEventListener(event, () => {
                if (!this.hasInteracted) {
                    this.hasInteracted = true;
                }
            }, { once: true, passive: true });
        });
        
        // Track scroll depth
        window.addEventListener('scroll', () => this.trackScrollDepth(), { passive: true });
    }
    
    startTracking() {
        // Start time tracking
        this.trackingInterval = setInterval(() => {
            this.timeOnSite += this.checkInterval;
            this.timeOnPage += this.checkInterval;
            
            // Check if should show
            if (this.shouldShow()) {
                this.show();
            }
        }, this.checkInterval);
    }
    
    shouldShow() {
        return (
            !this.isVisible &&
            this.hasInteracted &&
            this.timeOnSite >= this.showDelay
        );
    }
    
    show() {
        if (this.isVisible) return;
        
        
        // Update contextual message
        this.updateContextualMessage();
        
        // Show container
        this.container.classList.remove('hidden');
        
        // Animate in
        setTimeout(() => {
            this.container.classList.add('feedback-widget-visible');
        }, 10);
        
        this.isVisible = true;
        
        // Start pulse animation
        this.startPulse();
    }
    
    expand() {
        this.button.classList.add('hidden');
        this.form.classList.remove('hidden');
        this.isExpanded = true;
    }
    
    collapse() {
        this.form.classList.add('hidden');
        this.button.classList.remove('hidden');
        this.isExpanded = false;
    }
    
    dismiss() {
        localStorage.setItem('feedback_last_dismissed', new Date().toISOString());
        this.hide();
    }
    
    disablePermanently() {
        localStorage.setItem('feedback_disabled', 'true');
        this.hide();
    }
    
    hide() {
        this.container.classList.remove('feedback-widget-visible');
        setTimeout(() => {
            this.container.classList.add('hidden');
        }, 300);
        this.isVisible = false;
        
        if (this.trackingInterval) {
            clearInterval(this.trackingInterval);
        }
        if (this.pulseIntervalId) {
            clearInterval(this.pulseIntervalId);
        }
    }
    
    startPulse() {
        this.pulseIntervalId = setInterval(() => {
            if (!this.isExpanded && this.isVisible) {
                this.button?.classList.add('pulse');
                setTimeout(() => {
                    this.button?.classList.remove('pulse');
                }, 1000);
            }
        }, this.pulseInterval);
    }
    
    setRating(rating) {
        this.selectedRating = rating;
        this.updateStars(rating);
        this.submitBtn.disabled = false;
        
        // Update label
        const labels = ['Poor', 'Fair', 'Good', 'Very Good', 'Excellent'];
        document.getElementById('rating-label').textContent = labels[rating - 1];
    }
    
    hoverRating(rating) {
        this.updateStars(rating);
    }
    
    updateStars(rating) {
        this.stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.remove('far');
                star.classList.add('fas');
            } else {
                star.classList.remove('fas');
                star.classList.add('far');
            }
        });
    }
    
    trackScrollDepth() {
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollDepth = Math.round(((scrollTop + windowHeight) / documentHeight) * 100);
        
        if (scrollDepth > this.maxScrollDepth) {
            this.maxScrollDepth = Math.min(scrollDepth, 100);
        }
    }
    
    updateContextualMessage() {
        const pageType = this.detectPageType();
        const messages = {
            'home': 'How\'s your experience with Halal Korea?',
            'explore': 'Is the map helping you find places?',
            'place_detail': 'Is this place information helpful?',
            'prayer_times': 'Are the prayer times accurate for you?',
            'blog': 'Is our content helpful?',
            'submit': 'Is the submission form easy to use?',
            'other': 'How can we improve?'
        };
        
        const message = messages[pageType] || messages['other'];
        document.getElementById('feedback-message').textContent = message;
    }
    
    detectPageType() {
        const path = window.location.pathname;
        if (path === '/' || /^\/(en|ko|uz)\/?$/.test(path)) return 'home';
        if (path.includes('/explore')) return 'explore';
        if (path.includes('/place/')) return 'place_detail';
        if (path.includes('/prayer')) return 'prayer_times';
        if (path.includes('/blog')) return 'blog';
        if (path.includes('/submit')) return 'submit';
        return 'other';
    }
    
    detectDeviceType() {
        const width = window.innerWidth;
        if (width < 768) return 'mobile';
        if (width < 1024) return 'tablet';
        return 'desktop';
    }
    
    detectBrowser() {
        const ua = navigator.userAgent;
        if (ua.includes('Firefox')) return 'Firefox';
        if (ua.includes('Chrome')) return 'Chrome';
        if (ua.includes('Safari')) return 'Safari';
        if (ua.includes('Edge')) return 'Edge';
        return 'Other';
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
    }
    
    async submit() {
        if (!this.selectedRating) {
            alert('Please select a rating');
            return;
        }
        
        
        // Show loading state
        document.querySelector('.feedback-form-body').classList.add('hidden');
        document.getElementById('feedback-loading').classList.remove('hidden');
        
        const data = {
            rating: this.selectedRating,
            comment: this.textarea.value.trim(),
            page_url: window.location.href,
            page_type: this.detectPageType(),
            page_title: document.title,
            time_on_site: Math.floor(this.timeOnSite / 1000),
            time_on_page: Math.floor(this.timeOnPage / 1000),
            pages_visited: this.pagesVisited,
            scroll_depth: this.maxScrollDepth,
            language: document.documentElement.lang || 'en',
            device_type: this.detectDeviceType(),
            browser: this.detectBrowser(),
            screen_resolution: `${window.screen.width}x${window.screen.height}`,
            referrer: document.referrer,
            session_id: this.sessionId,
        };
        
        try {
            const response = await fetch('/feedback/submit/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showSuccess();
                localStorage.setItem('feedback_last_submitted', new Date().toISOString());
            } else {
                throw new Error(result.error || 'Submission failed');
            }
        } catch (error) {
            console.error('[Feedback] Submission error:', error);
            
            // Hide loading
            document.getElementById('feedback-loading').classList.add('hidden');
            document.querySelector('.feedback-form-body').classList.remove('hidden');
            
            alert(error.message || 'Failed to submit feedback. Please try again.');
        }
    }
    
    showSuccess() {
        document.getElementById('feedback-loading').classList.add('hidden');
        document.getElementById('feedback-success').classList.remove('hidden');
        
        // Hide after 3 seconds
        setTimeout(() => {
            this.hide();
        }, 3000);
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.feedbackWidget = new FeedbackWidget();
    });
} else {
    window.feedbackWidget = new FeedbackWidget();
}
