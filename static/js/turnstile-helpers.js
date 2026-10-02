/**
 * Shared Cloudflare Turnstile helpers (explicit render mode).
 * Requires turnstile api.js with ?render=explicit and window.TURNSTILE_SITEKEY.
 */
(function (window) {
    'use strict';

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

    function whenReady(callback) {
        if (window.turnstile && typeof window.turnstile.ready === 'function') {
            window.turnstile.ready(callback);
            return;
        }
        // api.js may still be loading; retry briefly.
        var attempts = 0;
        var timer = setInterval(function () {
            attempts += 1;
            if (window.turnstile && typeof window.turnstile.render === 'function') {
                clearInterval(timer);
                callback();
            } else if (attempts >= 50) {
                clearInterval(timer);
                console.warn('HalalTurnstile: turnstile API failed to load');
            }
        }, 100);
    }

    window.HalalTurnstile = {
        /**
         * Render an explicit Turnstile widget into a container.
         * @param {string|HTMLElement} container
         * @param {{action?: string, callback?: Function, errorCallback?: Function, expiredCallback?: Function}} [options]
         * @returns {Promise<string|null>} widget id
         */
        render: function (container, options) {
            options = options || {};
            var el = resolveContainer(container);
            if (!el) {
                console.warn('HalalTurnstile.render: container not found');
                return Promise.resolve(null);
            }

            var sitekey = getSitekey(el);
            if (!sitekey) {
                console.warn('HalalTurnstile.render: missing sitekey');
                return Promise.resolve(null);
            }

            var action = options.action || el.dataset.action || undefined;

            return new Promise(function (resolve) {
                whenReady(function () {
                    try {
                        // Avoid double-render on the same node.
                        if (el.dataset.turnstileWidgetId) {
                            window.turnstile.reset(el.dataset.turnstileWidgetId);
                            resolve(el.dataset.turnstileWidgetId);
                            return;
                        }

                        var widgetId = window.turnstile.render(el, {
                            sitekey: sitekey,
                            action: action,
                            callback: options.callback,
                            'error-callback': options.errorCallback,
                            'expired-callback': options.expiredCallback,
                        });
                        el.dataset.turnstileWidgetId = widgetId;
                        resolve(widgetId);
                    } catch (err) {
                        console.warn('HalalTurnstile.render failed:', err);
                        resolve(null);
                    }
                });
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
