/**
 * theme.js
 * ApexMotion Dark Mode & Light Mode Theme Switcher.
 * Persists user preference via localStorage and updates document element.
 */

(function () {
  const THEME_KEY = "apexmotion_theme";

  // Check saved theme or default to system preference (or light)
  const savedTheme = localStorage.getItem(THEME_KEY);
  const systemPrefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initialTheme = savedTheme || (systemPrefersDark ? "dark" : "light");

  document.documentElement.setAttribute("data-theme", initialTheme);

  document.addEventListener("DOMContentLoaded", () => {
    const themeBtn = document.getElementById("btn-theme-toggle");
    if (!themeBtn) return;

    updateThemeButton(themeBtn, initialTheme);

    themeBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const next = current === "light" ? "dark" : "light";

      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem(THEME_KEY, next);
      updateThemeButton(themeBtn, next);
    });
  });

  function updateThemeButton(btn, theme) {
    if (theme === "dark") {
      btn.innerHTML = `&#9728; <span class="theme-label">Light</span>`;
      btn.title = "Switch to Light Mode";
    } else {
      btn.innerHTML = `&#9790; <span class="theme-label">Dark</span>`;
      btn.title = "Switch to Dark Mode";
    }
  }
})();
