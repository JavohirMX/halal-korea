/**
 * Feedback Widget - Floating feedback collection system
 * Displays after user has been on site for a configurable time
 * Collects ratings, comments, and behavioral data
 */

class FeedbackWidget {
    constructor(config = {}) {
        this.showDelay = config.showDelay || 150000;
        this.checkInterval = 1000;

        this.timeOnSite = 0;
        this.timeOnPage = 0;
        this.startTime = Date.now();
        this.pageStartTime = Date.now();
        this.hasInteracted = false;
        this.isVisible = false;
        this.isExpanded = false;
        this.selectedRating = 0;

        this.sessionId = this.getOrCreateSessionId();
        this.pagesVisited = this.incrementPageVisit();

        this.maxScrollDepth = 0;

        this.widget = null;
        this.container = null;

        this.init();
    }

    init() {
        if (this.shouldDisable()) {
            return;
        }
        this.createWidget();
        this.setupEventListeners();
        this.startTracking();
    }

    shouldDisable() {
        if (localStorage.getItem('feedback_disabled') === 'true') {
            return true;
        }
        const lastSubmitted = localStorage.getItem('feedback_last_submitted');
        if (lastSubmitted) {
            const daysSince = (Date.now() - new Date(lastSubmitted)) / (1000 * 60 * 60 * 24);
            if (daysSince < 7) {
                return true;
            }
        }
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
        this.container = document.createElement('div');
        this.container.id = 'feedback-widget-container';
        this.container.className = 'feedback-widget-container hidden';
        this.container.innerHTML = `
            <div id="feedback-button" class="feedback-button" role="button" aria-label="Send feedback" tabindex="0">
                <i class="fas fa-comment-dots"></i>
            </div>

            <div id="feedback-form" class="feedback-form hidden">
                <div class="feedback-form-header">
                    <h3 class="feedback-form-title" id="feedback-message">How's your experience?</h3>
                    <button id="feedback-close" class="feedback-close-btn" aria-label="Close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <div class="feedback-form-body" id="feedback-form-body">
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

                    <div class="feedback-comment">
                        <label for="feedback-comment-text" class="feedback-label">
                            Tell us more (optional)
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

                    <button id="feedback-submit" class="feedback-submit-btn" disabled>
                        <i class="fas fa-paper-plane"></i>
                        <span id="feedback-submit-text">Send Feedback</span>
                    </button>

                    <div id="feedback-error" class="feedback-error hidden"></div>

                    <div class="feedback-secondary-actions" id="feedback-secondary-actions">
                        <button id="feedback-later" class="feedback-text-link">Maybe later</button>
                        <button id="feedback-disable" class="feedback-text-link">Don't show again</button>
                    </div>

                    <div id="feedback-disable-confirm" class="feedback-secondary-actions hidden">
                        <span class="feedback-confirm-inline">
                            Are you sure?
                            <button id="feedback-disable-yes" class="feedback-confirm-yes">Yes</button>
                            <button id="feedback-disable-no" class="feedback-confirm-no">Cancel</button>
                        </span>
                    </div>
                </div>

                <div id="feedback-success" class="feedback-success hidden">
                    <div class="success-icon">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <h3>Thank you!</h3>
                    <p>Your feedback helps us improve.</p>
                </div>
            </div>
        `;

        document.body.appendChild(this.container);

        this.button = document.getElementById('feedback-button');
        this.form = document.getElementById('feedback-form');
        this.stars = document.querySelectorAll('.star');
        this.submitBtn = document.getElementById('feedback-submit');
        this.submitText = document.getElementById('feedback-submit-text');
        this.textarea = document.getElementById('feedback-comment-text');
        this.errorEl = document.getElementById('feedback-error');
    }

    setupEventListeners() {
        this.button?.addEventListener('click', () => this.expand());
        this.button?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.expand();
            }
        });

        document.getElementById('feedback-close')?.addEventListener('click', () => this.collapse());

        this.stars.forEach(star => {
            star.addEventListener('click', () => this.setRating(parseInt(star.dataset.rating)));
            star.addEventListener('mouseenter', () => this.hoverRating(parseInt(star.dataset.rating)));
        });

        document.getElementById('star-rating')?.addEventListener('mouseleave', () => {
            this.hoverRating(this.selectedRating);
        });

        this.textarea?.addEventListener('input', (e) => {
            const count = e.target.value.length;
            document.getElementById('char-count').textContent = `${count}/500`;
        });

        this.submitBtn?.addEventListener('click', () => this.submit());

        document.getElementById('feedback-later')?.addEventListener('click', () => {
            this.dismiss();
        });

        document.getElementById('feedback-disable')?.addEventListener('click', () => {
            this.showDisableConfirm();
        });

        document.getElementById('feedback-disable-yes')?.addEventListener('click', () => {
            this.disablePermanently();
        });

        document.getElementById('feedback-disable-no')?.addEventListener('click', () => {
            this.hideDisableConfirm();
        });

        ['click', 'scroll', 'keydown', 'mousemove'].forEach(event => {
            document.addEventListener(event, () => {
                if (!this.hasInteracted) {
                    this.hasInteracted = true;
                }
            }, { once: true, passive: true });
        });

        window.addEventListener('scroll', () => this.trackScrollDepth(), { passive: true });
    }

    showDisableConfirm() {
        document.getElementById('feedback-secondary-actions').classList.add('hidden');
        document.getElementById('feedback-disable-confirm').classList.remove('hidden');
    }

    hideDisableConfirm() {
        document.getElementById('feedback-disable-confirm').classList.add('hidden');
        document.getElementById('feedback-secondary-actions').classList.remove('hidden');
    }

    startTracking() {
        this.trackingInterval = setInterval(() => {
            this.timeOnSite += this.checkInterval;
            this.timeOnPage += this.checkInterval;

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

        this.updateContextualMessage();

        this.container.classList.remove('hidden');

        setTimeout(() => {
            this.container.classList.add('feedback-widget-visible');
        }, 10);

        this.isVisible = true;
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
    }

    setRating(rating) {
        this.selectedRating = rating;
        this.updateStars(rating);
        this.submitBtn.disabled = false;

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

    showError(message) {
        this.errorEl.textContent = message;
        this.errorEl.classList.remove('hidden');
    }

    hideError() {
        this.errorEl.classList.add('hidden');
    }

    setSubmitLoading(loading) {
        this.submitBtn.disabled = loading;
        if (loading) {
            this.submitText.textContent = 'Sending...';
            this.submitBtn.querySelector('i')?.classList.add('hidden');
            const spinner = document.createElement('span');
            spinner.className = 'btn-spinner';
            spinner.id = 'submit-spinner';
            this.submitBtn.insertBefore(spinner, this.submitBtn.firstChild);
        } else {
            this.submitText.textContent = 'Send Feedback';
            this.submitBtn.querySelector('i')?.classList.remove('hidden');
            document.getElementById('submit-spinner')?.remove();
        }
    }

    async submit() {
        if (!this.selectedRating) {
            this.showError('Please select a rating.');
            return;
        }

        this.hideError();
        this.setSubmitLoading(true);

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
            this.setSubmitLoading(false);
            this.showError(error.message || 'Failed to submit. Please try again.');
        }
    }

    showSuccess() {
        document.getElementById('feedback-form-body').classList.add('hidden');
        document.getElementById('feedback-success').classList.remove('hidden');

        setTimeout(() => {
            this.hide();
        }, 2500);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.feedbackWidget = new FeedbackWidget();
    });
} else {
    window.feedbackWidget = new FeedbackWidget();
}
