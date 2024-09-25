document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('signin-form');
    const errorMessageDiv = document.getElementById('error-message');

    form.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData(form);
        const xhr = new XMLHttpRequest();
        xhr.open('POST', form.action, true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.onload = function() {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                if (response.success) {
                    window.location.href = response.redirect_url;
                } else {
                    errorMessageDiv.textContent = response.message;
                }
            } else {
                errorMessageDiv.textContent = 'An error occurred. Please try again.';
            }
        };

        xhr.send(formData);
    });
});
