(function () {
    "use strict";

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
        return btn.parentElement
            ? btn.parentElement.querySelector("[data-copy-prompt-source]")
            : null;
    }

    function handleCopyClick(btn) {
        var source = resolveSource(btn);
        var text = source ? source.value : "";
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(function () {
                showCopySuccess(btn);
            }).catch(showCopyError);
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
