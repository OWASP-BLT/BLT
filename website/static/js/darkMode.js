document.addEventListener("DOMContentLoaded", () => {
  // Get references to DOM elements
  const toggleButton = document.getElementById("theme-toggle");
  const sunIcon = document.getElementById("sun-icon");
  const moonIcon = document.getElementById("moon-icon");
  const htmlElement = document.documentElement;

  /**
   * Updates the UI to reflect the current theme state
   * @param {boolean} isDark - Whether dark mode is active
   */
  const updateThemeUI = (isDark) => {
    // Update icon visibility - only one should be visible at a time
    sunIcon.style.display = isDark ? "block" : "none";
    moonIcon.style.display = isDark ? "none" : "block";
    
    // Add subtle animation when changing themes
    toggleButton.classList.add("animate-pulse");
    setTimeout(() => toggleButton.classList.remove("animate-pulse"), 500);
  };

  // Check for system preference if no saved preference exists
  const prefersDark = window.matchMedia && 
                      window.matchMedia('(prefers-color-scheme: dark)').matches;
  const savedTheme = localStorage.getItem("theme");
  
  // Apply theme based on preference hierarchy: saved > system > default(light)
  const initialTheme = savedTheme || (prefersDark ? "dark" : "light");
  const isDark = initialTheme === "dark";
  
  // Set the theme on page load
  if (isDark) {
    htmlElement.classList.add("dark");
  } else {
    htmlElement.classList.remove("dark");
  }
  
  // Initialize UI on page load
  updateThemeUI(isDark);

  // Toggle theme when button is clicked
  toggleButton.addEventListener("click", () => {
    const isDark = htmlElement.classList.toggle("dark");
    const newTheme = isDark ? "dark" : "light";
    
    // Save user preference
    localStorage.setItem("theme", newTheme);
    
    // Update UI to reflect new theme
    updateThemeUI(isDark);

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
  });

  // Listen for system theme changes
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  mediaQuery.addEventListener('change', event => {
    // Only update if user hasn't set a preference manually
    if (!localStorage.getItem("theme")) {
      const newIsDark = event.matches;
      htmlElement.classList.toggle("dark", newIsDark);
      updateThemeUI(newIsDark);
    }
  });
});