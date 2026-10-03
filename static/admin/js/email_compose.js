// Admin email compose — audience picker, user chips, and live recipient preview.
//
// The picker is the single source of truth for the payload: only the active
// audience panel's fields are serialised, so what the admin sees is what the
// server resolves. The preview endpoint shares _resolve_recipients() with the
// send path, so the number shown here is the number that gets sent.

(function () {
    'use strict';

    var DEBOUNCE_MS = 350;
    var SEARCH_DEBOUNCE_MS = 250;

    var MODE_LABELS = {
        all: 'All users',
        segment: 'Segment',
        users: 'Specific users',
        single: 'Single user',
        manual: 'Manual addresses'
    };

    function readConfig() {
        var node = document.getElementById('email-compose-config');
        if (!node) {
            return null;
        }
        try {
            return JSON.parse(node.textContent);
        } catch (err) {
            return null;
        }
    }

    function debounce(fn, wait) {
        var timer = null;
        return function () {
            var args = arguments;
            var self = this;
            window.clearTimeout(timer);
            timer = window.setTimeout(function () {
                fn.apply(self, args);
            }, wait);
        };
    }

    function getCookie(name) {
        var value = null;
        document.cookie.split(';').forEach(function (chunk) {
            var parts = chunk.trim().split('=');
            if (parts[0] === name) {
                value = decodeURIComponent(parts.slice(1).join('='));
            }
        });
        return value;
    }

    function initCompose(root, config) {
        var form = root.querySelector('#email-compose-form');
        var countEl = root.querySelector('#recipient-count');
        var metaEl = root.querySelector('#recipient-meta');
        var loadingEl = root.querySelector('#preview-loading');
        var previewEl = root.querySelector('#preview-recipients');
        var moreEl = root.querySelector('#preview-more');
        var confirmCard = root.querySelector('#confirm-card');
        var confirmWarning = root.querySelector('#confirm-warning');
        var confirmInput = root.querySelector('#id_confirm_send_count');
        var addressesRow = root.querySelector('#addresses-row');
        var addressesHelp = root.querySelector('#addresses-help');
        var allModeNote = root.querySelector('#all-mode-note');
        var chipsEl = root.querySelector('#user-chips');
        var searchInput = root.querySelector('#user-search-input');
        var resultsEl = root.querySelector('#user-search-results');
        var selectedIds = root.querySelector('#id_selected_user_ids');

        var previewSeq = 0;
        var searchSeq = 0;
        var lastTotal = null;

        // ---- Audience mode -------------------------------------------------

        function activeMode() {
            var checked = root.querySelector('input[name="audience_mode"]:checked');
            return checked ? checked.value : config.defaultMode;
        }

        function modeInputs() {
            return Array.prototype.slice.call(root.querySelectorAll('input[name="audience_mode"]'));
        }

        function syncMode() {
            var mode = activeMode();

            root.querySelectorAll('[data-audience-panel]').forEach(function (panel) {
                panel.hidden = panel.getAttribute('data-audience-panel') !== mode;
            });

            if (allModeNote) {
                allModeNote.hidden = mode !== 'all';
            }

            // Addresses are additive everywhere except manual, where they are the
            // only recipient source — so they are required there.
            var isManual = mode === 'manual';
            var addresses = root.querySelector('#id_additional_emails');
            if (addresses) {
                addresses.required = isManual;
                addresses.setAttribute('aria-required', isManual ? 'true' : 'false');
            }
            if (addressesRow) {
                addressesRow.classList.toggle('is-required', isManual);
            }
            if (addressesHelp) {
                addressesHelp.textContent = isManual
                    ? 'Required in this mode. Comma- or newline-separated; they do not need to be registered users.'
                    : 'Optional. Comma- or newline-separated; they do not need to be registered users.';
            }

            var modeEl = root.querySelector('#recipient-mode');
            if (modeEl && MODE_LABELS[mode]) {
                modeEl.textContent = MODE_LABELS[mode];
            }

            schedulePreview();
        }

        modeInputs().forEach(function (input) {
            input.addEventListener('change', syncMode);
        });

        // ---- Live preview --------------------------------------------------

        function buildPayload() {
            var payload = new FormData();

            // Only the checked radio. Appending all five would make the server's
            // QueryDict.get() return the last choice ('manual') instead of the
            // admin's actual selection.
            payload.append('audience_mode', activeMode());

            var userIdField = root.querySelector('#id_user_id');
            payload.append('user_id', userIdField ? userIdField.value : '');
            payload.append('selected_user_ids', selectedIds ? selectedIds.value : '');

            var mode = activeMode();
            if (mode === 'segment') {
                ['filter_is_active', 'filter_email_verified', 'filter_preferred_language'].forEach(function (name) {
                    var el = root.querySelector('[name="' + name + '"]');
                    if (el) {
                        payload.append(name, el.value);
                    }
                });
                var staff = root.querySelector('[name="include_staff"]');
                if (staff && staff.checked) {
                    payload.append('include_staff', 'on');
                }
            }

            var addresses = root.querySelector('#id_additional_emails');
            if (addresses && addresses.value.trim()) {
                payload.append('additional_emails', addresses.value);
            }

            return payload;
        }

        function renderSample(sample) {
            if (!previewEl) {
                return;
            }
            previewEl.innerHTML = '';
            sample.forEach(function (row) {
                var li = document.createElement('li');
                li.textContent = row.name ? row.email + ' (' + row.name + ')' : row.email;
                previewEl.appendChild(li);
            });
        }

        function renderMeta(data) {
            if (!metaEl) {
                return;
            }
            metaEl.querySelectorAll('.summary-chip').forEach(function (chip) {
                chip.remove();
            });

            function addMetaChip(text) {
                var span = document.createElement('span');
                span.className = 'summary-chip';
                span.textContent = text;
                metaEl.appendChild(span);
            }

            if (data.skipped) {
                addMetaChip(data.skipped === 1 ? '1 user skipped (no email)' : data.skipped + ' users skipped (no email)');
            }
            if (data.adhoc_count) {
                addMetaChip(
                    data.adhoc_count === 1
                        ? '1 additional address'
                        : data.adhoc_count + ' additional addresses'
                );
            }
        }

        function setConfirmVisible(visible, total) {
            if (!confirmCard) {
                return;
            }
            confirmCard.hidden = !visible;
            if (visible && confirmWarning) {
                confirmWarning.textContent =
                    'This reaches ' + total + ' recipients. Type the number below to confirm.';
            }
            // Invalidate a typed confirmation only when the target size actually
            // changes — a no-op preview refresh should not wipe what was typed.
            if (visible && total !== lastTotal && confirmInput) {
                confirmInput.value = '';
            }
            lastTotal = total;
        }

        function applyPreview(data) {
            if (countEl) {
                countEl.textContent = data.count;
            }
            renderSample(data.sample || []);
            renderMeta(data);

            if (moreEl) {
                var overflow = data.count > (data.sample || []).length;
                moreEl.hidden = !overflow;
                if (overflow) {
                    moreEl.textContent = 'and more (' + data.count + ' total)';
                }
            }

            setConfirmVisible(!!data.needs_confirmation, data.count);

            // Reflect the server's resolved label (it normalises legacy payloads),
            // but never re-trigger a preview from here — that would loop.
            var modeEl = root.querySelector('#recipient-mode');
            if (modeEl && data.audience_mode !== activeMode() && MODE_LABELS[data.audience_mode]) {
                modeEl.textContent = MODE_LABELS[data.audience_mode];
            }
        }

        function runPreview() {
            var seq = ++previewSeq;
            if (loadingEl) {
                loadingEl.hidden = false;
            }

            window.fetch(config.previewUrl, {
                method: 'POST',
                body: buildPayload(),
                headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
                credentials: 'same-origin'
            })
                .then(function (response) {
                    return response.json().then(function (payload) {
                        return { ok: response.ok, payload: payload };
                    });
                })
                .then(function (result) {
                    if (seq !== previewSeq) {
                        return;
                    }
                    if (result.ok) {
                        applyPreview(result.payload);
                    } else {
                        applyPreview({
                            audience_mode: activeMode(),
                            count: 0,
                            skipped: 0,
                            adhoc_count: 0,
                            needs_confirmation: false,
                            sample: []
                        });
                    }
                })
                .catch(function () {
                    // Leave the server-rendered count in place on network failure.
                })
                .then(function () {
                    if (seq === previewSeq && loadingEl) {
                        loadingEl.hidden = true;
                    }
                });
        }

        var schedulePreview = debounce(runPreview, DEBOUNCE_MS);

        // ---- User chips ----------------------------------------------------

        function selectedIdList() {
            if (!selectedIds) {
                return [];
            }
            return selectedIds.value
                .split(',')
                .map(function (item) {
                    return item.trim();
                })
                .filter(Boolean);
        }

        function writeSelectedIds() {
            if (selectedIds) {
                selectedIds.value = selectedIdList().join(',');
            }
        }

        function addChip(user) {
            if (!chipsEl || !selectedIds) {
                return;
            }
            var ids = selectedIdList();
            if (ids.indexOf(String(user.id)) !== -1) {
                return;
            }
            ids.push(String(user.id));
            selectedIds.value = ids.join(',');

            var li = document.createElement('li');
            li.className = 'chip';
            li.setAttribute('data-user-id', user.id);
            if (!user.email) {
                li.setAttribute('data-has-email', '0');
            }

            var label = document.createElement('span');
            label.className = 'chip-label';
            label.textContent = user.name || user.username;

            var email = document.createElement('span');
            email.className = 'chip-email';
            email.textContent = user.email || 'no email — will be skipped';

            var remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'chip-remove';
            remove.setAttribute('aria-label', 'Remove');
            remove.innerHTML = '&times;';

            li.appendChild(label);
            li.appendChild(email);
            li.appendChild(remove);
            chipsEl.appendChild(li);

            schedulePreview();
        }

        function closeResults() {
            if (!resultsEl) {
                return;
            }
            resultsEl.hidden = true;
            resultsEl.innerHTML = '';
            if (searchInput) {
                searchInput.setAttribute('aria-expanded', 'false');
            }
        }

        function renderResults(results) {
            if (!resultsEl) {
                return;
            }
            resultsEl.innerHTML = '';

            if (!results.length) {
                var empty = document.createElement('li');
                empty.className = 'typeahead-empty';
                empty.textContent = 'No matching users';
                resultsEl.appendChild(empty);
            } else {
                results.forEach(function (user) {
                    var li = document.createElement('li');
                    li.className = 'typeahead-item';
                    li.setAttribute('role', 'option');

                    var name = document.createElement('span');
                    name.className = 'typeahead-name';
                    name.textContent = user.name || user.username;

                    var email = document.createElement('span');
                    email.className = 'typeahead-email';
                    email.textContent = user.email || 'no email address';

                    li.appendChild(name);
                    li.appendChild(email);

                    if (!user.email) {
                        var warn = document.createElement('span');
                        warn.className = 'typeahead-warn';
                        warn.textContent = 'skipped';
                        li.appendChild(warn);
                    }

                    li.addEventListener('mousedown', function (event) {
                        event.preventDefault();
                        addChip(user);
                        closeResults();
                        if (searchInput) {
                            searchInput.value = '';
                        }
                        searchInput.focus();
                    });

                    resultsEl.appendChild(li);
                });
            }

            resultsEl.hidden = false;
            if (searchInput) {
                searchInput.setAttribute('aria-expanded', 'true');
            }
        }

        function runSearch(term) {
            var seq = ++searchSeq;
            window
                .fetch(config.searchUrl + '?q=' + encodeURIComponent(term), {
                    credentials: 'same-origin'
                })
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    if (seq !== searchSeq) {
                        return;
                    }
                    renderResults(data.results || []);
                })
                .catch(function () {
                    closeResults();
                });
        }

        var scheduleSearch = debounce(runSearch, SEARCH_DEBOUNCE_MS);

        if (searchInput) {
            searchInput.addEventListener('input', function () {
                var term = searchInput.value.trim();
                if (term.length < 2) {
                    closeResults();
                    return;
                }
                scheduleSearch(term);
            });

            searchInput.addEventListener('blur', function () {
                window.setTimeout(closeResults, 150);
            });

            searchInput.addEventListener('keydown', function (event) {
                if (event.key === 'Escape') {
                    closeResults();
                }
            });
        }

        if (chipsEl) {
            chipsEl.addEventListener('click', function (event) {
                var button = event.target.closest('.chip-remove');
                if (!button) {
                    return;
                }
                var chip = button.closest('.chip');
                if (!chip) {
                    return;
                }
                var id = chip.getAttribute('data-user-id');
                chipsEl.querySelectorAll('.chip[data-user-id="' + id + '"]').forEach(function (node) {
                    node.remove();
                });
                selectedIds.value = selectedIdList()
                    .filter(function (value) {
                        return value !== id;
                    })
                    .join(',');
                schedulePreview();
            });
        }

        // ---- Audience-affecting inputs -------------------------------------

        [
            'filter_is_active',
            'filter_email_verified',
            'filter_preferred_language',
            'include_staff'
        ].forEach(function (name) {
            var el = root.querySelector('[name="' + name + '"]');
            if (el) {
                el.addEventListener('change', schedulePreview);
            }
        });

        var addressesEl = root.querySelector('#id_additional_emails');
        if (addressesEl) {
            addressesEl.addEventListener('input', schedulePreview);
        }

        // Keep in sync on back/forward navigation.
        window.addEventListener('pageshow', function (event) {
            if (event.persisted) {
                syncMode();
            }
        });

        syncMode();
    }

    document.addEventListener('DOMContentLoaded', function () {
        var config = readConfig();
        var root = document.querySelector('.email-compose');
        if (!config || !root) {
            return;
        }
        initCompose(root, config);
    });
})();