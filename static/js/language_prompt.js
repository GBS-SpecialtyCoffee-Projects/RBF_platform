// First-visit language prompt on the sign-in page. Drives the same `googtrans`
// cookie the navbar's Google Translate dropdown uses, then reloads so the
// translation is applied. Remembers the choice in localStorage so returning
// users aren't prompted again (they can still switch via the navbar dropdown).
document.addEventListener('DOMContentLoaded', function () {
    var modalEl = document.getElementById('languagePromptModal');
    if (!modalEl) {
        return;
    }

    var STORAGE_KEY = 'cc_language_chosen';

    function hide() {
        modalEl.style.display = 'none';
    }

    // Mark that the user made a real choice, so we stop prompting.
    function markChosen() {
        localStorage.setItem(STORAGE_KEY, '1');
    }

    // Only prompt users who haven't picked a language yet.
    if (!localStorage.getItem(STORAGE_KEY)) {
        modalEl.style.display = 'block';
    }

    // Close WITHOUT choosing (the X or the dark backdrop): just hide it.
    // We intentionally don't mark it chosen, so it prompts again next visit.
    var closeBtn = modalEl.querySelector('.lang-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', hide);
    }
    modalEl.addEventListener('click', function (event) {
        if (event.target === modalEl) {
            hide();
        }
    });

    modalEl.querySelectorAll('.lang-choice').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var lang = btn.getAttribute('data-lang');
            if (lang === 'en') {
                // English is the default — a real choice, so stop prompting,
                // but nothing to translate: just close.
                markChosen();
                hide();
                return;
            }
            document.cookie = 'googtrans=/en/' + lang + '; path=/';
            markChosen();
            // Reload so Google Translate picks up the cookie on init.
            window.location.reload();
        });
    });
});
