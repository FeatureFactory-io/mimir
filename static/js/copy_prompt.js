(function () {
    "use strict";

    var COPY_RECEIPT_MAX_ATTEMPTS = 2;
    var HTTP_REQUEST_TIMEOUT = 408;
    var HTTP_SERVER_ERROR = 500;

    function getToasts() {
        var successEl = document.getElementById("copy-prompt-toast");
        var errorEl = document.getElementById("copy-prompt-error-toast");
        return {
            success: successEl ? bootstrap.Toast.getOrCreateInstance(successEl) : null,
            error: errorEl ? bootstrap.Toast.getOrCreateInstance(errorEl) : null,
        };
    }

    function showCopySuccess(btn) {
        var toasts = getToasts();
        if (toasts.success) {
            toasts.success.show();
        }
        var iconWrap = btn.querySelector("[data-copy-prompt-icon-wrap]");
        if (!iconWrap) {
            return;
        }
        var cursorImg = iconWrap.querySelector("[data-copy-prompt-cursor-icon]");
        var check = iconWrap.querySelector(".mm-copy-prompt-success-icon");
        if (!cursorImg || !check) {
            return;
        }
        cursorImg.classList.add("d-none");
        check.classList.remove("d-none");
        setTimeout(function () {
            cursorImg.classList.remove("d-none");
            check.classList.add("d-none");
        }, 1500);
    }

    function showCopyError(err) {
        var toasts = getToasts();
        if (toasts.error) {
            toasts.error.show();
        }
        if (typeof console !== "undefined" && console.warn) {
            console.warn("[copy-prompt] clipboard failed", err);
        }
    }

    function resolveSource(btn) {
        var sourceId = btn.getAttribute("data-copy-prompt-for");
        if (sourceId) {
            var byId = document.getElementById(sourceId);
            if (byId) {
                return byId;
            }
        }
        var cell = btn.closest("td");
        if (cell) {
            var inCell = cell.querySelector("[data-copy-prompt-source]");
            if (inCell) {
                return inCell;
            }
        }
        var toolbar = btn.closest('[role="toolbar"]');
        if (toolbar) {
            var inToolbar = toolbar.querySelector("[data-copy-prompt-source]");
            if (inToolbar) {
                return inToolbar;
            }
        }
        var control = btn.closest(".mm-copy-prompt-control");
        if (control) {
            var inControl = control.querySelector("[data-copy-prompt-source]");
            if (inControl) {
                return inControl;
            }
        }
        return btn.parentElement
            ? btn.parentElement.querySelector("[data-copy-prompt-source]")
            : null;
    }

    /**
     * Allocate one identity per successful copy.
     * @returns {string} UUID reused only for receipt retries.
     */
    function createCopyActionIdentity() {
        return window.crypto.randomUUID();
    }

    /**
     * Read the explicit server-rendered entity metadata.
     * @param {HTMLButtonElement} btn Existing copy control.
     * @returns {{entity_type: string, entity_id: number}|null} Eligible report target.
     */
    function readCopyReceiptTarget(btn) {
        var entityType = btn.dataset.copyReceiptEntityType;
        var entityId = Number(btn.dataset.copyReceiptEntityId);
        if (!entityType || !Number.isSafeInteger(entityId) || entityId < 1) {
            return null;
        }
        return { entity_type: entityType, entity_id: entityId };
    }

    /**
     * Read the server-rendered CSRF token for this control.
     * @param {HTMLButtonElement} btn Existing copy control.
     * @returns {string} CSRF token or an empty string when absent.
     */
    function readCopyReceiptCsrf(btn) {
        var csrfToken = btn.dataset.copyReceiptCsrf;
        return csrfToken && csrfToken !== "NOTPROVIDED" ? csrfToken : "";
    }

    /**
     * Report an already completed clipboard write.
     * @param {HTMLButtonElement} btn Existing successful copy control.
     * @param {string} eventIdentity UUID allocated for this clipboard action.
     * @returns {Promise<void>} Receipt completion independent of clipboard feedback.
     */
    async function reportSuccessfulCopy(btn, eventIdentity) {
        var target = readCopyReceiptTarget(btn);
        var csrfToken = readCopyReceiptCsrf(btn);
        if (!target || !csrfToken) {
            return;
        }
        var payload = {
            entity_type: target.entity_type,
            entity_id: target.entity_id,
            event_identity: eventIdentity,
        };
        await sendCopyReceipt(btn.dataset.copyReceiptUrl, payload, csrfToken, 1);
    }

    /**
     * Retry transient receipt delivery failures with exactly the same action.
     * @param {string} endpoint Same-origin receipt endpoint.
     * @param {{entity_type: string, entity_id: number, event_identity: string}} payload Report.
     * @param {string} csrfToken Token from the rendered control.
     * @param {number} attempt Current delivery attempt, starting at one.
     * @returns {Promise<void>} Receipt completion, or rejection if delivery fails.
     */
    async function sendCopyReceipt(endpoint, payload, csrfToken, attempt) {
        var response;
        try {
            response = await fetch(endpoint, {
                method: "POST",
                mode: "same-origin",
                credentials: "same-origin",
                redirect: "error",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
                body: JSON.stringify(payload),
            });
        } catch {
            response = null;
        }
        if (response && response.ok) {
            return;
        }
        var transient = !response || response.status === HTTP_REQUEST_TIMEOUT ||
            response.status >= HTTP_SERVER_ERROR;
        if (transient && attempt < COPY_RECEIPT_MAX_ATTEMPTS) {
            return sendCopyReceipt(endpoint, payload, csrfToken, attempt + 1);
        }
        throw new Error("Copy receipt delivery failed");
    }

    function handleCopyClick(btn) {
        var source = resolveSource(btn);
        var text = source ? source.value : "";
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(async function () {
                showCopySuccess(btn);
                if (!btn.dataset.copyReceiptUrl) {
                    return;
                }
                try {
                    await reportSuccessfulCopy(btn, createCopyActionIdentity());
                } catch {
                    console.warn("[copy-prompt] receipt delivery failed");
                }
            }, showCopyError);
            return;
        }
        showCopyError(new Error("Clipboard API unavailable"));
    }

    document.addEventListener("click", function (event) {
        var btn = event.target.closest("[data-copy-prompt-trigger]");
        if (!btn) {
            return;
        }
        event.preventDefault();
        handleCopyClick(btn);
    });
})();
