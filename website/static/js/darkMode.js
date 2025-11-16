document.addEventListener("DOMContentLoaded", () => {
  const htmlElement = document.documentElement;
  
  // Initialize theme from localStorage on page load
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme === "dark") {
    htmlElement.classList.add("dark");
  }

  // Use event delegation to handle clicks on the theme toggle button
  document.addEventListener("click", (event) => {
    const toggleButton = event.target.closest("#theme-toggle");
    if (toggleButton) {
        const isDark = htmlElement.classList.toggle("dark");
        const newTheme = isDark ? "dark" : "light";
        
        // Save user preference
        localStorage.setItem("theme", newTheme);

        // Send theme preference to server if CSRF token is available
        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
        if (csrfToken) {
          fetch("/set-theme/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({ theme: newTheme }),
          }).catch(error => console.error("Error saving theme preference:", error));
        }
    }
  });
});
