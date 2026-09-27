// Dashboard onboarding tour, built on Driver.js (loaded in partials/tour.html).
// Step content comes from base/onboarding_tour.py via the #tour-steps JSON.
(function () {
    var config = document.getElementById('tour-config');
    var stepsData = document.getElementById('tour-steps');
    if (!config || !stepsData || !window.driver) return;

    var allSteps = JSON.parse(stepsData.textContent);
    var needsSaving = config.dataset.autostart === 'true';

    function isVisible(selector) {
        var el = document.querySelector(selector);
        return el !== null && el.getClientRects().length > 0;
    }

    function markComplete() {
        if (!needsSaving) return;
        needsSaving = false;
        fetch(config.dataset.completeUrl, {
            method: 'POST',
            headers: {'X-CSRFToken': config.dataset.csrfToken},
            credentials: 'same-origin',
        });
    }

    function run() {
        // Steps without an element are centred popovers; keep them.
        var steps = allSteps.filter(function (step) {
            return !step.element || isVisible(step.element);
        });
        window.driver.js.driver({
            showProgress: true,
            steps: steps,
            onDestroyed: markComplete,
        }).drive();
    }

    // On small screens the navbar links sit inside a collapsed menu, so open
    // it first; otherwise the navbar steps would be skipped.
    function start() {
        var nav = document.getElementById('appNav');
        var toggler = document.querySelector('[data-bs-target="#appNav"]');
        var collapsed = nav && toggler && toggler.getClientRects().length > 0
            && !nav.classList.contains('show');
        if (!collapsed) {
            run();
            return;
        }
        nav.addEventListener('shown.bs.collapse', run, {once: true});
        bootstrap.Collapse.getOrCreateInstance(nav, {toggle: false}).show();
    }

    var button = document.getElementById('start-tour');
    if (button) button.addEventListener('click', start);
    if (needsSaving) start();
})();
