// Reject oversized images in the browser so the upload never starts.
// The limit comes from data-max-size on each file input (set server-side in
// base/validators.py), so it can never drift from what the server enforces.
(function () {
    'use strict';

    function readableSize(bytes) {
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // One reusable error node per input, inserted directly after it.
    function errorNodeFor(input) {
        var existing = input.parentNode.querySelector('.image-upload-error');
        if (existing) {
            return existing;
        }
        var node = document.createElement('div');
        node.className = 'image-upload-error text-danger small mt-1';
        input.parentNode.insertBefore(node, input.nextSibling);
        return node;
    }

    function check(input) {
        var limit = parseInt(input.getAttribute('data-max-size'), 10);
        var error = errorNodeFor(input);
        error.textContent = '';

        if (!limit || !input.files || input.files.length === 0) {
            return;
        }

        var file = input.files[0];
        if (file.size > limit) {
            error.textContent =
                'That image is ' + readableSize(file.size) + '. Please choose an ' +
                'image of ' + readableSize(limit) + ' or less.';
            // Clearing the input is what actually blocks the submission.
            input.value = '';
        }
    }

    // Capture phase, so the input is already cleared by the time a page's own
    // change handler (e.g. the "chosen filename" label) reads it.
    document.addEventListener('change', function (event) {
        var input = event.target;
        if (input && input.matches && input.matches('input[type="file"][data-max-size]')) {
            check(input);
        }
    }, true);
})();
