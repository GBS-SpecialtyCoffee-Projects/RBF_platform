// Custom confirmation for "Reject" buttons. One shared modal submits whichever
// form triggered it, so it works for lists of connection requests too.
document.addEventListener('DOMContentLoaded', function () {
    var modalEl = document.getElementById('rejectConfirmModal');
    if (!modalEl) {
        return;
    }

    var targetForm = null;

    modalEl.addEventListener('show.bs.modal', function (event) {
        var trigger = event.relatedTarget;
        targetForm = trigger ? trigger.closest('form') : null;
    });

    var confirmBtn = modalEl.querySelector('#rejectConfirmBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function () {
            if (targetForm) {
                targetForm.submit();
            }
        });
    }
});
