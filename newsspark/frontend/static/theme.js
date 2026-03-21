/**
 * theme.js – NewsSpark dark/light theme toggle.
 * Auto-detects system preference on first load.
 * Persists user preference to localStorage.
 */

(function () {
  const STORAGE_KEY = 'newsspark_theme';

  function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    // Update all toggle button icons
    document.querySelectorAll('.theme-toggle').forEach(btn => {
      btn.textContent = theme === 'dark' ? '☀️' : '🌙';
      btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    });
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  }

  // Initialise on load
  function init() {
    const saved = localStorage.getItem(STORAGE_KEY);
    applyTheme(saved || getSystemTheme());

    // Wire up all toggle buttons (including ones added after DOMContentLoaded)
    document.addEventListener('click', function (e) {
      if (e.target.closest('.theme-toggle')) {
        toggleTheme();
      }
    });

    // React to system theme changes (only if user hasn't overridden)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      if (!localStorage.getItem(STORAGE_KEY)) {
        applyTheme(e.matches ? 'dark' : 'light');
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
