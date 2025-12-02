document.addEventListener("DOMContentLoaded", function () {
    // Handle resend confirmation email click
    const resendLink = document.getElementById("resend-confirmation");
    if (resendLink) {
        const subscriberEmail = resendLink.getAttribute("data-email");
        const resendUrl = resendLink.getAttribute("data-resend-url");

        resendLink.addEventListener("click", function (e) {
            e.preventDefault();

            // Show loading state
            const originalText = resendLink.textContent;
            resendLink.textContent = "Sending...";
            resendLink.style.pointerEvents = "none";

            // Get CSRF token from cookie or meta tag
            const csrfToken =
                document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
                document.querySelector('meta[name="csrf-token"]')?.content;

            // Make AJAX request to resend confirmation
            fetch(resendUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email: subscriberEmail,
                }),
            })
                .then((response) => response.json())
                .then((data) => {
                    if (data.success) {
                        window.createMessage("Confirmation email has been sent.", "success");
                    } else {
                        window.createMessage("Failed to send confirmation email. Please try again.", "error");
                    }
                })
                .catch(() => {
                    window.createMessage("An error occurred. Please try again.", "error");
                })
                .finally(() => {
                    // Reset button state
                    resendLink.textContent = originalText;
                    resendLink.style.pointerEvents = "auto";
                });
        });
    }
});
