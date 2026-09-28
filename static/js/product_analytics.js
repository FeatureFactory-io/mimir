(function initializeProductAnalytics() {
    "use strict";

    var CONSENT_KEY = "ff_analytics_consent_v1";
    var OBSERVER_THRESHOLD = 0.5;
    var analyticsAllowed = false;
    var analyticsStarted = false;
    var body = document.body;
    if (!body || body.dataset.analyticsEnabled !== "true") return;

    var context = Object.freeze({
        product_id: body.dataset.analyticsProductId,
        experiment_id: body.dataset.analyticsExperimentId,
        hypothesis_id: body.dataset.analyticsHypothesisId,
        variant_id: body.dataset.analyticsVariantId,
        synthetic: false
    });
    var measurementId = body.dataset.analyticsMeasurementId;

    function readConsent() {
        try { return window.localStorage.getItem(CONSENT_KEY); } catch (error) { return null; }
    }

    function writeConsent(value) {
        try { window.localStorage.setItem(CONSENT_KEY, value); } catch (error) { /* Session-only fallback. */ }
    }

    function pageParameters() {
        var pageUrl = new URL(window.location.href);
        return {
            page_location: pageUrl.origin + pageUrl.pathname,
            page_path: pageUrl.pathname,
            page_title: document.title
        };
    }

    function sendEvent(name, parameters) {
        if (!analyticsAllowed || typeof window.gtag !== "function") return;
        window.gtag("event", name, Object.assign({}, context, parameters || {}));
    }

    function loadGoogleTag() {
        if (!measurementId || document.querySelector("[data-ga-measurement]")) return;
        window.dataLayer = window.dataLayer || [];
        window.gtag = function gtag() { window.dataLayer.push(arguments); };
        window.gtag("consent", "default", { ad_storage: "denied", analytics_storage: "granted" });
        window.gtag("js", new Date());
        window.gtag("config", measurementId, {
            allow_ad_personalization_signals: false,
            allow_google_signals: false,
            send_page_view: false
        });
        var script = document.createElement("script");
        script.async = true;
        script.dataset.gaMeasurement = measurementId;
        script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(measurementId);
        document.head.appendChild(script);
    }

    function observeFeatures() {
        if (!("IntersectionObserver" in window)) return;
        var viewed = new Set();
        var observer = new IntersectionObserver(function (entries) {
            entries.filter(function (entry) { return entry.isIntersecting; }).forEach(function (entry) {
                var featureId = entry.target.dataset.analyticsFeature;
                if (!featureId || viewed.has(featureId)) return;
                viewed.add(featureId);
                sendEvent("feature_view", { feature_id: featureId });
                observer.unobserve(entry.target);
            });
        }, { threshold: OBSERVER_THRESHOLD });
        document.querySelectorAll("[data-analytics-feature]").forEach(function (element) { observer.observe(element); });
    }

    function bindJourneyEvents() {
        document.querySelectorAll("[data-analytics-event]").forEach(function (element) {
            element.addEventListener("click", function () {
                sendEvent(element.dataset.analyticsEvent, {
                    cta_location: element.dataset.analyticsCta || "unknown",
                    cta_target: element.dataset.analyticsTarget || "unknown"
                });
            });
        });
        var registration = document.querySelector("[data-analytics-registration]");
        if (registration) registration.addEventListener("submit", function () {
            sendEvent("registration_start", { registration_type: registration.dataset.analyticsRegistration });
        });
        if (document.querySelector(".analytics-sign-up")) sendEvent("sign_up", { method: "account_form" });
        observeFeatures();
    }

    function startAnalytics() {
        analyticsAllowed = true;
        window["ga-disable-" + measurementId] = false;
        if (analyticsStarted) {
            window.gtag("consent", "update", { analytics_storage: "granted" });
            return;
        }
        analyticsStarted = true;
        loadGoogleTag();
        bindJourneyEvents();
        sendEvent("page_view", pageParameters());
        console.info("[analytics] started", { product_id: context.product_id });
    }

    function revokeAnalytics() {
        analyticsAllowed = false;
        window["ga-disable-" + measurementId] = true;
        if (typeof window.gtag === "function") {
            window.gtag("consent", "update", { analytics_storage: "denied" });
        }
        document.cookie = "_ga=; Max-Age=0; path=/; SameSite=Lax";
        document.cookie = "_ga_" + measurementId.replace("G-", "") + "=; Max-Age=0; path=/; SameSite=Lax";
    }

    function initializeConsent() {
        var panel = document.querySelector("[data-analytics-consent]");
        if (!panel) return;
        document.querySelector("[data-analytics-settings]").addEventListener("click", function () {
            panel.hidden = false;
        });
        var consent = readConsent();
        if (consent === "allow") return startAnalytics();
        if (consent === "deny") return;
        panel.hidden = false;
        panel.querySelector("[data-analytics-allow]").addEventListener("click", function () {
            writeConsent("allow");
            panel.hidden = true;
            startAnalytics();
        });
        panel.querySelector("[data-analytics-deny]").addEventListener("click", function () {
            writeConsent("deny");
            revokeAnalytics();
            panel.hidden = true;
        });
    }

    initializeConsent();
}());
