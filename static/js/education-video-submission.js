// Video Submission Form Handler
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('add-video-form');
    const errorDiv = document.getElementById('error-message');
    const successDiv = document.getElementById('success-message');
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.textContent;

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // Clear previous messages
        errorDiv.classList.add('hidden');
        successDiv.classList.add('hidden');
        errorDiv.textContent = '';
        successDiv.textContent = '';

        // Show loading state
        submitButton.disabled = true;
        submitButton.textContent = 'Processing...';

        const formData = new FormData(form);

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                successDiv.textContent = data.message;
                successDiv.classList.remove('hidden', 'text-red-500');
                successDiv.classList.add('text-green-600', 'p-4', 'bg-green-50', 'border', 'border-green-200', 'rounded-md');
                form.reset();
            } else {
                // Show error message
                errorDiv.textContent = data.message;
                errorDiv.classList.remove('hidden');
                errorDiv.classList.add('text-red-500', 'p-4', 'bg-red-50', 'border', 'border-red-200', 'rounded-md');
            }
        })
        .catch(error => {
            errorDiv.textContent = 'An error occurred while processing your request. Please try again.';
            errorDiv.classList.remove('hidden');
            errorDiv.classList.add('text-red-500', 'p-4', 'bg-red-50', 'border', 'border-red-200', 'rounded-md');
        })
        .finally(() => {
            // Reset button state
            submitButton.disabled = false;
            submitButton.textContent = originalButtonText;
        });
    });
});
