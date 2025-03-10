// Dark mode functionality for BLT
document.addEventListener("DOMContentLoaded", function () {
  // Check for saved theme preference or use the system preference
  const isDarkMode =
    localStorage.getItem("darkMode") === "true" ||
    (localStorage.getItem("darkMode") === null &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  // Set initial theme
  if (isDarkMode) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }

  // Update toggle button state
  updateToggleButton(isDarkMode);

  // Toggle dark mode
  window.toggleDarkMode = function () {
    const isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("darkMode", isDark);
    updateToggleButton(isDark);
  };

  // Update toggle button appearance
  function updateToggleButton(isDark) {
    const toggleButtons = document.querySelectorAll(".dark-mode-toggle");
    toggleButtons.forEach((button) => {
      const sunIcon = button.querySelector(".sun-icon");
      const moonIcon = button.querySelector(".moon-icon");

      if (isDark) {
        sunIcon.classList.remove("hidden");
        moonIcon.classList.add("hidden");
      } else {
        sunIcon.classList.add("hidden");
        moonIcon.classList.remove("hidden");
      }
    });
  }

  // Listen for system preference changes
  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", (e) => {
      if (localStorage.getItem("darkMode") === null) {
        const isDark = e.matches;
        document.documentElement.classList.toggle("dark", isDark);
        updateToggleButton(isDark);
      }
    });
});
