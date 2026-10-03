/**
 * Shared Cloudflare Turnstile helpers (explicit render mode).
 * Requires turnstile api.js with ?render=explicit and window.TURNSTILE_SITEKEY.
 *
 * Readiness contract
 * ------------------
 * api.js is loaded with `async defer`, so `window.turnstile` (and
 * `turnstile.ready`) can exist while the script is still bootstrapping.
 * Cloudflare throws from `turnstile.ready()` in that window, so we must never
 * treat "turnstile.ready exists" as "turnstile is ready". We instead trust the
 * script tag's own `load` event, which flips window.__turnstileApiLoaded.
 *
 * `render()` never rejects: callers all discard the promise, so a rejection
 * becomes an unhandled rejection and the widget silently never appears.
 */
(function (window) {
    'use strict';

    var READY_POLL_MS = 100;
    var READY_TIMEOUT_ATTEMPTS = 100; // ~10s before we give up

    function resolveContainer(container) {
        if (!container) {
            return null;
        }
        if (typeof container === 'string') {
            return document.querySelector(container);
        }
        return container;
    }

    function getSitekey(el) {
        if (el && el.dataset && el.dataset.sitekey) {
            return el.dataset.sitekey;
        }
        return window.TURNSTILE_SITEKEY || '';
    }

    function apiIsLoaded() {
        return window.__turnstileApiLoaded === true;
    }

    function whenReady(callback) {
        var fired = false;

        function fire() {
            if (fired) {
                return;
            }
            fired = true;
            callback();
        }

        // api.js is fully loaded: now — and only now — is ready() safe to call.
        if (apiIsLoaded() && window.turnstile && typeof window.turnstile.ready === 'function') {
            try {
                window.turnstile.ready(fire);
            } catch (err) {
                // Belt and braces: ready() can still throw on odd load orders.
                fire();
            }
            return;
        }

        var attempts = 0;
        var timer = setInterval(function () {
            attempts += 1;

            if (apiIsLoaded() && window.turnstile && typeof window.turnstile.render === 'function') {
                clearInterval(timer);
                try {
                    window.turnstile.ready(fire);
                } catch (err) {
                    fire();
                }
                return;
            }

            if (attempts >= READY_TIMEOUT_ATTEMPTS) {
                clearInterval(timer);
                console.warn('HalalTurnstile: turnstile API failed to load');
                fire();
            }
        }, READY_POLL_MS);
    }

    /**
     * Make a visible-noise-free notice in place of a widget that never rendered.
     * A silently missing CAPTCHA just looks like a form that rejects for no reason.
     */
    function showUnavailable(el) {
        if (!el || !el.parentNode) {
            return;
        }
        var host = el.parentNode;
        if (host.querySelector('.turnstile-unavailable')) {
            return;
        }
        var notice = document.createElement('p');
        notice.className = 'turnstile-unavailable';
        notice.setAttribute('role', 'alert');
        notice.textContent =
            'Security check could not load. Please refresh the page or try again shortly.';
        host.insertBefore(notice, el);
    }

    function hideUnavailable(el) {
        if (!el || !el.parentNode) {
            return;
        }
        var existing = el.parentNode.querySelector('.turnstile-unavailable');
        if (existing) {
            existing.remove();
        }
    }

    window.HalalTurnstile = {
        /**
         * Render an explicit Turnstile widget into a container.
         * Resolves with the widget id, or null if the widget could not be shown.
         * Never rejects.
         * @param {string|HTMLElement} container
         * @param {{action?: string, callback?: Function, errorCallback?: Function,
         *          expiredCallback?: Function, onUnavailable?: Function}} [options]
         * @returns {Promise<string|null>} widget id
         */
        render: function (container, options) {
            options = options || {};

            return new Promise(function (resolve) {
                var settled = false;

                function finish(widgetId) {
                    if (settled) {
                        return;
                    }
                    settled = true;
                    resolve(widgetId === undefined ? null : widgetId);
                }

                function fail(message) {
                    console.warn('HalalTurnstile:', message);
                    if (typeof options.onUnavailable === 'function') {
                        options.onUnavailable(message);
                    } else {
                        showUnavailable(el);
                    }
                    finish(null);
                }

                var el = resolveContainer(container);
                if (!el) {
                    console.warn('HalalTurnstile.render: container not found');
                    return finish(null);
                }

                var sitekey = getSitekey(el);
                if (!sitekey) {
                    return fail('missing sitekey');
                }

                var action = options.action || el.dataset.action || undefined;

                try {
                    whenReady(function () {
                        if (!window.turnstile || typeof window.turnstile.render !== 'function') {
                            return fail('turnstile API unavailable');
                        }
                        try {
                            hideUnavailable(el);

                            // Avoid double-render on the same node.
                            if (el.dataset.turnstileWidgetId) {
                                window.turnstile.reset(el.dataset.turnstileWidgetId);
                                return finish(el.dataset.turnstileWidgetId);
                            }

                            var widgetId = window.turnstile.render(el, {
                                sitekey: sitekey,
                                action: action,
                                callback: options.callback,
                                'error-callback': options.errorCallback,
                                'expired-callback': options.expiredCallback,
                            });
                            el.dataset.turnstileWidgetId = widgetId;
                            finish(widgetId);
                        } catch (err) {
                            fail('render failed: ' + err);
                        }
                    });
                } catch (err) {
                    // whenReady() itself must never turn into a rejected promise.
                    fail('readiness check failed: ' + err);
                }
            });
        },

        /**
         * Reset a widget so a fresh token can be issued.
         * @param {string|HTMLElement} widgetIdOrContainer
         */
        reset: function (widgetIdOrContainer) {
            if (!window.turnstile || typeof window.turnstile.reset !== 'function') {
                return;
            }

            var widgetId = widgetIdOrContainer;
            if (widgetIdOrContainer && typeof widgetIdOrContainer !== 'string') {
                var el = resolveContainer(widgetIdOrContainer);
                widgetId = el && el.dataset ? el.dataset.turnstileWidgetId : null;
            } else if (typeof widgetIdOrContainer === 'string' && widgetIdOrContainer.charAt(0) === '#') {
                var node = resolveContainer(widgetIdOrContainer);
                widgetId = node && node.dataset ? node.dataset.turnstileWidgetId : widgetIdOrContainer;
            }

            if (widgetId) {
                try {
                    window.turnstile.reset(widgetId);
                } catch (err) {
                    console.warn('HalalTurnstile.reset failed:', err);
                }
            }
        },
    };
})(window);