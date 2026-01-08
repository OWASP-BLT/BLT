document.addEventListener("DOMContentLoaded", () => {
  const htmlElement = document.documentElement;

  // Use event delegation to handle clicks on the theme toggle button
  document.addEventListener("click", (event) => {
    const toggleButton = event.target.closest("#theme-toggle");
    if (toggleButton) {
        const isDark = htmlElement.classList.toggle("dark");
        const newTheme = isDark ? "dark" : "light";
        
        // Save user preference
        localStorage.setItem("theme", newTheme);

        // Send theme preference to server if CSRF token is available
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (csrfToken) {
          fetch("/set-theme/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({ theme: newTheme }),
          }).catch(() => {
            // Silently handle errors - theme preference is saved in localStorage
          });
        }
    }
  });
});
