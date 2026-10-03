// Admin email compose — audience picker, user chips, live preview, formatting toolbar, and safety checks.
//
// The picker is the single source of truth for the payload: only the active
// audience panel's fields are serialised, so what the admin sees is what the
// server resolves.

(function () {
    'use strict';

    var DEBOUNCE_MS = 350;
    var SEARCH_DEBOUNCE_MS = 250;
    var DRAFT_STORAGE_KEY = 'halal_korea_email_compose_local_draft';

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
        var confirmIcon = root.querySelector('#confirm-match-icon');
        var addressesRow = root.querySelector('#addresses-row');
        var addressesLabelText = root.querySelector('#addresses-label-text');
        var addressesHelp = root.querySelector('#addresses-help');
        var allModeNote = root.querySelector('#all-mode-note');
        var chipsEl = root.querySelector('#user-chips');
        var searchInput = root.querySelector('#user-search-input');
        var resultsEl = root.querySelector('#user-search-results');
        var btnClearChips = root.querySelector('#btn-clear-user-chips');
        var selectedIds = root.querySelector('#id_selected_user_ids');
        var userIdField = root.querySelector('#id_user_id');

        // Single user elements
        var singlePickerWrap = root.querySelector('#single-user-picker-wrap');
        var singleSearchInput = root.querySelector('#single-user-search-input');
        var singleResultsEl = root.querySelector('#single-user-search-results');
        var singleChipsEl = root.querySelector('#single-user-chips');

        // Subject & Message elements
        var subjectInput = root.querySelector('#id_subject');
        var subjectCharCounter = root.querySelector('#subject-char-counter');
        var messageInput = root.querySelector('#id_message');
        var messageWordCounter = root.querySelector('#message-word-counter');
        var sendAsHtmlCheckbox = root.querySelector('#id_send_as_html');
        var autosaveStatus = root.querySelector('#autosave-status');

        // Modals
        var previewModal = root.querySelector('#email-preview-modal');
        var previewIframe = root.querySelector('#email-preview-iframe');
        var previewSubjectText = root.querySelector('#preview-modal-subject');
        var previewFrameContainer = root.querySelector('#preview-frame-container');
        var btnOpenPreview = root.querySelector('#btn-open-preview');
        var btnActionsPreview = root.querySelector('#btn-actions-preview');
        var btnClosePreview = root.querySelector('#btn-close-preview');
        var btnViewportDesktop = root.querySelector('#viewport-desktop');
        var btnViewportMobile = root.querySelector('#viewport-mobile');

        var testSendModal = root.querySelector('#test-send-modal');
        var btnOpenTestSend = root.querySelector('#btn-open-test-send');
        var btnCloseTestSend = root.querySelector('#btn-close-test-send');
        var btnCancelTestSend = root.querySelector('#btn-cancel-test-send');
        var btnDoTestSend = root.querySelector('#btn-do-test-send');
        var testEmailInput = root.querySelector('#test-send-email-input');
        var testStatusBox = root.querySelector('#test-send-status');

        var btnSubmitSend = root.querySelector('#btn-submit-send');

        var previewSeq = 0;
        var searchSeq = 0;
        var singleSearchSeq = 0;
        var lastTotal = null;
        var isFormSubmitted = false;

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

            var isManual = mode === 'manual';
            var addresses = root.querySelector('#id_additional_emails');
            if (addresses) {
                addresses.required = isManual;
                addresses.setAttribute('aria-required', isManual ? 'true' : 'false');
            }
            if (addressesRow) {
                addressesRow.classList.toggle('is-required', isManual);
            }
            if (addressesLabelText) {
                addressesLabelText.textContent = isManual
                    ? 'Recipient addresses *'
                    : 'Additional addresses (optional)';
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

            updateUserChipsVisibility();
            schedulePreview();
        }

        modeInputs().forEach(function (input) {
            input.addEventListener('change', syncMode);
        });

        // ---- Live preview --------------------------------------------------

        function buildPayload() {
            var payload = new FormData();
            payload.append('audience_mode', activeMode());
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

        function checkConfirmMatch() {
            if (!confirmInput || !confirmIcon) {
                return;
            }
            if (!confirmCard || confirmCard.hidden) {
                confirmIcon.textContent = '';
                confirmIcon.className = 'confirm-status-icon';
                return;
            }
            var val = (confirmInput.value || '').trim();
            if (!val) {
                confirmIcon.textContent = '';
                confirmIcon.className = 'confirm-status-icon';
                confirmInput.classList.remove('is-valid', 'is-invalid');
                return;
            }
            if (val === String(lastTotal)) {
                confirmIcon.innerHTML = '&#10004; Matches ' + lastTotal;
                confirmIcon.className = 'confirm-status-icon match-success';
                confirmInput.classList.add('is-valid');
                confirmInput.classList.remove('is-invalid');
            } else {
                confirmIcon.innerHTML = '&#10008; Type ' + lastTotal;
                confirmIcon.className = 'confirm-status-icon match-error';
                confirmInput.classList.add('is-invalid');
                confirmInput.classList.remove('is-valid');
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
            if (visible && total !== lastTotal && confirmInput) {
                confirmInput.value = '';
            }
            lastTotal = total;
            checkConfirmMatch();
        }

        if (confirmInput) {
            confirmInput.addEventListener('input', checkConfirmMatch);
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
                    // Retain server-rendered count on network error
                })
                .then(function () {
                    if (seq === previewSeq && loadingEl) {
                        loadingEl.hidden = true;
                    }
                });
        }

        var schedulePreview = debounce(runPreview, DEBOUNCE_MS);

        // ---- User chips & typeahead keyboard nav ----------------------------

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

        function updateUserChipsVisibility() {
            var count = selectedIdList().length;
            if (btnClearChips) {
                btnClearChips.style.display = count > 1 ? 'inline-block' : 'none';
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

            updateUserChipsVisibility();
            schedulePreview();
        }

        // Setup combobox typeahead with keyboard navigation
        function setupTypeahead(inputEl, resultsContainer, onSelect) {
            var activeIndex = -1;

            function close() {
                resultsContainer.hidden = true;
                resultsContainer.innerHTML = '';
                inputEl.setAttribute('aria-expanded', 'false');
                activeIndex = -1;
            }

            function updateActiveItem(items) {
                items.forEach(function (el, idx) {
                    el.classList.toggle('is-selected', idx === activeIndex);
                    if (idx === activeIndex) {
                        el.scrollIntoView({ block: 'nearest' });
                    }
                });
            }

            function render(results) {
                resultsContainer.innerHTML = '';
                activeIndex = -1;

                if (!results.length) {
                    var empty = document.createElement('li');
                    empty.className = 'typeahead-empty';
                    empty.textContent = 'No matching users';
                    resultsContainer.appendChild(empty);
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
                            onSelect(user);
                            close();
                            inputEl.value = '';
                            inputEl.focus();
                        });

                        resultsContainer.appendChild(li);
                    });
                }

                resultsContainer.hidden = false;
                inputEl.setAttribute('aria-expanded', 'true');
            }

            inputEl.addEventListener('keydown', function (event) {
                var items = resultsContainer.querySelectorAll('.typeahead-item');
                if (event.key === 'Escape') {
                    close();
                } else if (event.key === 'ArrowDown') {
                    if (items.length) {
                        event.preventDefault();
                        activeIndex = (activeIndex + 1) % items.length;
                        updateActiveItem(items);
                    }
                } else if (event.key === 'ArrowUp') {
                    if (items.length) {
                        event.preventDefault();
                        activeIndex = activeIndex <= 0 ? items.length - 1 : activeIndex - 1;
                        updateActiveItem(items);
                    }
                } else if (event.key === 'Enter') {
                    if (activeIndex >= 0 && items[activeIndex]) {
                        event.preventDefault();
                        items[activeIndex].dispatchEvent(new MouseEvent('mousedown'));
                    }
                }
            });

            inputEl.addEventListener('blur', function () {
                window.setTimeout(close, 200);
            });

            return {
                render: render,
                close: close
            };
        }

        // Specific users search setup
        if (searchInput && resultsEl) {
            var multiTypeahead = setupTypeahead(searchInput, resultsEl, function (user) {
                addChip(user);
            });

            var scheduleSearch = debounce(function (term) {
                var seq = ++searchSeq;
                window.fetch(config.searchUrl + '?q=' + encodeURIComponent(term), {
                    credentials: 'same-origin'
                })
                    .then(function (res) {
                        if (!res.ok) {
                            throw new Error('Search failed');
                        }
                        return res.json();
                    })
                    .then(function (data) {
                        if (seq === searchSeq) {
                            multiTypeahead.render(data.results || []);
                        }
                    })
                    .catch(function () {
                        multiTypeahead.close();
                    });
            }, SEARCH_DEBOUNCE_MS);

            searchInput.addEventListener('input', function () {
                var term = searchInput.value.trim();
                if (term.length < 2) {
                    multiTypeahead.close();
                    return;
                }
                scheduleSearch(term);
            });
        }

        // Single user search & chip setup
        function renderSingleUserChip(user) {
            if (!singleChipsEl) {
                return;
            }
            singleChipsEl.innerHTML = '';
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

            var changeBtn = document.createElement('button');
            changeBtn.type = 'button';
            changeBtn.className = 'chip-remove';
            changeBtn.id = 'btn-change-single-user';
            changeBtn.setAttribute('aria-label', 'Change user');
            changeBtn.innerHTML = '&times;';

            li.appendChild(label);
            li.appendChild(email);
            li.appendChild(changeBtn);
            singleChipsEl.appendChild(li);

            if (userIdField) {
                userIdField.value = user.id;
            }
            if (singlePickerWrap) {
                singlePickerWrap.style.display = 'none';
            }
            schedulePreview();
        }

        function clearSingleUser() {
            if (userIdField) {
                userIdField.value = '';
            }
            if (singleChipsEl) {
                singleChipsEl.innerHTML =
                    '<li class="chip chip-warning chip-empty-single" data-has-email="0">' +
                    '<span class="chip-label">No user selected</span>' +
                    '<span class="chip-email">search above or open from a user\'s change form</span>' +
                    '</li>';
            }
            if (singlePickerWrap) {
                singlePickerWrap.style.display = 'block';
            }
            if (singleSearchInput) {
                singleSearchInput.value = '';
                singleSearchInput.focus();
            }
            schedulePreview();
        }

        if (singleSearchInput && singleResultsEl) {
            var singleTypeahead = setupTypeahead(singleSearchInput, singleResultsEl, function (user) {
                renderSingleUserChip(user);
            });

            var scheduleSingleSearch = debounce(function (term) {
                var seq = ++singleSearchSeq;
                window.fetch(config.searchUrl + '?q=' + encodeURIComponent(term), {
                    credentials: 'same-origin'
                })
                    .then(function (res) {
                        if (!res.ok) {
                            throw new Error('Search failed');
                        }
                        return res.json();
                    })
                    .then(function (data) {
                        if (seq === singleSearchSeq) {
                            singleTypeahead.render(data.results || []);
                        }
                    })
                    .catch(function () {
                        singleTypeahead.close();
                    });
            }, SEARCH_DEBOUNCE_MS);

            singleSearchInput.addEventListener('input', function () {
                var term = singleSearchInput.value.trim();
                if (term.length < 2) {
                    singleTypeahead.close();
                    return;
                }
                scheduleSingleSearch(term);
            });
        }

        if (singleChipsEl) {
            singleChipsEl.addEventListener('click', function (event) {
                if (event.target.closest('#btn-change-single-user') || event.target.closest('.chip-remove')) {
                    clearSingleUser();
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
                updateUserChipsVisibility();
                schedulePreview();
            });
        }

        if (btnClearChips) {
            btnClearChips.addEventListener('click', function () {
                if (chipsEl) {
                    chipsEl.innerHTML = '';
                }
                if (selectedIds) {
                    selectedIds.value = '';
                }
                updateUserChipsVisibility();
                schedulePreview();
            });
        }

        // ---- Text Formatting Toolbar & Counters -----------------------------

        function updateCounters() {
            if (subjectInput && subjectCharCounter) {
                var subLen = (subjectInput.value || '').length;
                subjectCharCounter.textContent = subLen + ' / 200';
                subjectCharCounter.classList.toggle('text-danger', subLen > 200);
            }
            if (messageInput && messageWordCounter) {
                var text = (messageInput.value || '').trim();
                var words = text ? text.split(/\s+/).length : 0;
                var chars = text.length;
                messageWordCounter.textContent = words + ' words, ' + chars + ' chars';
            }
        }

        if (subjectInput) {
            subjectInput.addEventListener('input', updateCounters);
        }
        if (messageInput) {
            messageInput.addEventListener('input', updateCounters);
        }

        // Toolbar formatting
        root.querySelectorAll('.format-toolbar button[data-format]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (!messageInput) {
                    return;
                }
                var format = btn.getAttribute('data-format');
                var start = messageInput.selectionStart;
                var end = messageInput.selectionEnd;
                var text = messageInput.value;
                var selection = text.substring(start, end);

                var before = '';
                var after = '';

                switch (format) {
                    case 'b':
                        before = '<strong>';
                        after = '</strong>';
                        break;
                    case 'i':
                        before = '<em>';
                        after = '</em>';
                        break;
                    case 'h3':
                        before = '<h3>';
                        after = '</h3>';
                        break;
                    case 'p':
                        before = '<p>';
                        after = '</p>';
                        break;
                    case 'ul':
                        before = '<ul>\n  <li>';
                        after = '</li>\n</ul>';
                        break;
                    case 'blockquote':
                        before = '<blockquote>';
                        after = '</blockquote>';
                        break;
                    case 'a':
                        var url = window.prompt('Enter target URL (e.g. https://...):', 'https://');
                        if (!url) {
                            return;
                        }
                        before = '<a href="' + url + '">';
                        after = '</a>';
                        break;
                }

                var replacement = before + (selection || 'text') + after;
                messageInput.value = text.substring(0, start) + replacement + text.substring(end);
                messageInput.focus();
                messageInput.selectionStart = start + before.length;
                messageInput.selectionEnd = start + before.length + (selection || 'text').length;

                if (sendAsHtmlCheckbox && !sendAsHtmlCheckbox.checked) {
                    sendAsHtmlCheckbox.checked = true;
                }

                updateCounters();
                saveLocalDraft();
            });
        });

        // ---- Local Autosave & Navigation Protection -------------------------

        function saveLocalDraft() {
            if (!subjectInput && !messageInput) {
                return;
            }
            try {
                var draft = {
                    subject: subjectInput ? subjectInput.value : '',
                    message: messageInput ? messageInput.value : '',
                    html: sendAsHtmlCheckbox ? sendAsHtmlCheckbox.checked : false,
                    savedAt: Date.now()
                };
                window.sessionStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
                if (autosaveStatus) {
                    autosaveStatus.textContent = 'Draft autosaved';
                }
            } catch (err) {
                // Ignore storage limits
            }
        }

        var scheduleAutosave = debounce(saveLocalDraft, 500);

        if (subjectInput) {
            subjectInput.addEventListener('input', scheduleAutosave);
        }
        if (messageInput) {
            messageInput.addEventListener('input', scheduleAutosave);
        }

        // Restore local draft if server values are empty
        try {
            var rawDraft = window.sessionStorage.getItem(DRAFT_STORAGE_KEY);
            if (rawDraft) {
                var savedDraft = JSON.parse(rawDraft);
                if (subjectInput && !subjectInput.value && savedDraft.subject) {
                    subjectInput.value = savedDraft.subject;
                }
                if (messageInput && !messageInput.value && savedDraft.message) {
                    messageInput.value = savedDraft.message;
                }
                if (sendAsHtmlCheckbox && savedDraft.html) {
                    sendAsHtmlCheckbox.checked = true;
                }
            }
        } catch (err) {}

        window.addEventListener('beforeunload', function (e) {
            if (isFormSubmitted) {
                return;
            }
            var hasContent = (subjectInput && subjectInput.value.trim()) ||
                             (messageInput && messageInput.value.trim());
            if (hasContent) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        var discardLink = root.querySelector('#discard-draft');
        if (discardLink) {
            discardLink.addEventListener('click', function () {
                try {
                    window.sessionStorage.removeItem(DRAFT_STORAGE_KEY);
                } catch (err) {}
            });
        }

        // ---- Live Branded Email Preview Modal -------------------------------

        function openPreviewModal() {
            if (!previewModal || !config.renderPreviewUrl) {
                return;
            }
            var subject = subjectInput ? (subjectInput.value || 'Subject Preview') : '';
            var message = messageInput ? (messageInput.value || 'Your message…') : '';
            var isHtml = sendAsHtmlCheckbox ? sendAsHtmlCheckbox.checked : false;

            if (previewSubjectText) {
                previewSubjectText.textContent = subject;
            }

            var formData = new FormData();
            formData.append('subject', subject);
            formData.append('message', message);
            if (isHtml) {
                formData.append('send_as_html', 'on');
            }

            if (previewIframe) {
                previewIframe.srcdoc = '<p style="font-family:sans-serif;padding:20px;color:#666;">Rendering preview…</p>';
            }
            previewModal.hidden = false;

            window.fetch(config.renderPreviewUrl, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
                credentials: 'same-origin'
            })
                .then(function (res) {
                    return res.json();
                })
                .then(function (data) {
                    if (previewIframe && data.html) {
                        previewIframe.srcdoc = data.html;
                    }
                })
                .catch(function () {
                    if (previewIframe) {
                        previewIframe.srcdoc = '<p style="color:red;padding:20px;">Failed to render email preview.</p>';
                    }
                });
        }

        function closePreviewModal() {
            if (previewModal) {
                previewModal.hidden = true;
            }
        }

        if (btnOpenPreview) {
            btnOpenPreview.addEventListener('click', openPreviewModal);
        }
        if (btnActionsPreview) {
            btnActionsPreview.addEventListener('click', openPreviewModal);
        }
        if (btnClosePreview) {
            btnClosePreview.addEventListener('click', closePreviewModal);
        }
        if (btnViewportDesktop && btnViewportMobile && previewFrameContainer) {
            btnViewportDesktop.addEventListener('click', function () {
                btnViewportDesktop.classList.add('active');
                btnViewportMobile.classList.remove('active');
                previewFrameContainer.className = 'modal-body preview-frame-container desktop';
            });
            btnViewportMobile.addEventListener('click', function () {
                btnViewportMobile.classList.add('active');
                btnViewportDesktop.classList.remove('active');
                previewFrameContainer.className = 'modal-body preview-frame-container mobile';
            });
        }

        // ---- Send Test Email Modal ------------------------------------------

        function openTestSendModal() {
            if (!testSendModal) {
                return;
            }
            if (testEmailInput && !testEmailInput.value && config.userEmail) {
                testEmailInput.value = config.userEmail;
            }
            if (testStatusBox) {
                testStatusBox.hidden = true;
                testStatusBox.textContent = '';
            }
            testSendModal.hidden = false;
        }

        function closeTestSendModal() {
            if (testSendModal) {
                testSendModal.hidden = true;
            }
        }

        function doTestSend() {
            if (!config.testSendUrl || !btnDoTestSend) {
                return;
            }
            var email = testEmailInput ? testEmailInput.value.trim() : '';
            if (!email) {
                alert('Please enter an email address.');
                return;
            }

            var subject = subjectInput ? subjectInput.value : '';
            var message = messageInput ? messageInput.value : '';
            var isHtml = sendAsHtmlCheckbox ? sendAsHtmlCheckbox.checked : false;

            var formData = new FormData();
            formData.append('test_email', email);
            formData.append('subject', subject);
            formData.append('message', message);
            if (isHtml) {
                formData.append('send_as_html', 'on');
            }

            btnDoTestSend.disabled = true;
            btnDoTestSend.textContent = 'Sending test…';

            window.fetch(config.testSendUrl, {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
                credentials: 'same-origin'
            })
                .then(function (res) {
                    return res.json().then(function (data) {
                        return { ok: res.ok, data: data };
                    });
                })
                .then(function (result) {
                    if (testStatusBox) {
                        testStatusBox.hidden = false;
                        if (result.ok) {
                            testStatusBox.className = 'test-status-box alert alert-success';
                            testStatusBox.textContent = 'Test email successfully queued to ' + result.data.email + '!';
                        } else {
                            testStatusBox.className = 'test-status-box alert alert-danger';
                            testStatusBox.textContent = result.data.error || 'Failed to send test email.';
                        }
                    }
                })
                .catch(function () {
                    if (testStatusBox) {
                        testStatusBox.hidden = false;
                        testStatusBox.className = 'test-status-box alert alert-danger';
                        testStatusBox.textContent = 'Network error sending test email.';
                    }
                })
                .then(function () {
                    btnDoTestSend.disabled = false;
                    btnDoTestSend.textContent = 'Send test now';
                });
        }

        if (btnOpenTestSend) {
            btnOpenTestSend.addEventListener('click', openTestSendModal);
        }
        if (btnCloseTestSend) {
            btnCloseTestSend.addEventListener('click', closeTestSendModal);
        }
        if (btnCancelTestSend) {
            btnCancelTestSend.addEventListener('click', closeTestSendModal);
        }
        if (btnDoTestSend) {
            btnDoTestSend.addEventListener('click', doTestSend);
        }

        // Close modals on Escape key
        window.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closePreviewModal();
                closeTestSendModal();
            }
        });

        // Close modals when clicking backdrop
        [previewModal, testSendModal].forEach(function (modal) {
            if (modal) {
                modal.addEventListener('click', function (e) {
                    if (e.target === modal) {
                        modal.hidden = true;
                    }
                });
            }
        });

        // ---- Form submission & safety ---------------------------------------

        if (form) {
            form.addEventListener('submit', function (e) {
                // If large send requires confirmation, check before submission
                if (confirmCard && !confirmCard.hidden && confirmInput) {
                    var val = (confirmInput.value || '').trim();
                    if (val !== String(lastTotal)) {
                        e.preventDefault();
                        alert('Please type the exact recipient count (' + lastTotal + ') in the confirmation box to confirm this send.');
                        confirmInput.focus();
                        return;
                    }
                }

                isFormSubmitted = true;
                try {
                    window.sessionStorage.removeItem(DRAFT_STORAGE_KEY);
                } catch (err) {}

                if (btnSubmitSend) {
                    btnSubmitSend.disabled = true;
                    btnSubmitSend.value = 'Queuing email delivery…';
                }
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

        window.addEventListener('pageshow', function (event) {
            if (event.persisted) {
                syncMode();
            }
        });

        updateCounters();
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