// Auto-open the sourcing-preferences modal until the roaster has filled it.
document.addEventListener('DOMContentLoaded', function () {
    var modalEl = document.getElementById('sourcingPrefsModal');
    if (modalEl && modalEl.dataset.showOnLoad === 'true') {
        var modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
});
