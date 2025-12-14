/*
 * Organization list page behaviors.
 *
 * This file exists so templates can safely reference
 * `{% static 'js/organization_list.js' %}` when using
 * ManifestStaticFilesStorage.
 */

(() => {
    "use strict";

    const LOGIN_URL = "/accounts/login/";

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return null;
    }

    function redirectToLogin() {
        const next = window.location.pathname + window.location.search;
        window.location.href = `${LOGIN_URL}?next=${encodeURIComponent(next)}`;
    }

    async function refreshOrganization(button) {
        const orgId = button.dataset.orgId;
        if (!orgId) {
            return;
        }

        const icon = button.querySelector("i");
        const originalHtml = button.innerHTML;
        const originalTitle = button.title;

        if (icon) {
            icon.classList.add("fa-spin");
        }
        button.disabled = true;
        button.title = "Refreshing...";

        const csrfToken = getCookie("csrftoken");

        try {
            const response = await fetch(`/api/organization/${orgId}/refresh/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken || "",
                },
                credentials: "same-origin",
            });

            if (response.status === 401 || response.redirected) {
                redirectToLogin();
                return;
            }

            const data = await response.json();
            if (!data || !data.success) {
                const message = (data && data.error) || "Refresh failed.";
                throw new Error(message);
            }

            button.title = "Refreshed successfully!";
            button.innerHTML = '<i class="fas fa-check text-base"></i><span class="ml-2">Refreshed</span>';

            setTimeout(() => {
                button.disabled = false;
                button.title = originalTitle;
                button.innerHTML = originalHtml;
            }, 1500);
        } catch (err) {
            if (icon) {
                icon.classList.remove("fa-spin");
            }
            button.disabled = false;
            button.title = originalTitle;
            button.innerHTML = originalHtml;
            alert(err && err.message ? err.message : "Failed to refresh organization.");
        }
    }

    document.addEventListener("click", (event) => {
        const card = event.target.closest(".js-org-card");
        if (card) {
            const clickedInteractive = event.target.closest(
                'a, button, input, select, textarea, label, [role="button"], [data-ignore-card-click]'
            );
            if (!clickedInteractive) {
                const href = card.dataset.href;
                if (href) {
                    window.location.href = href;
                    return;
                }
            }
        }

        const button = event.target.closest(".js-org-refresh");
        if (!button) {
            return;
        }
        event.preventDefault();
        refreshOrganization(button);
    });
})();
