// Theme toggle (light/dark), persisted in localStorage under 'logpyre-theme'.
// base.html's inline <head> script already set data-theme/data-ag-theme-mode
// on <html> before first paint — this file only wires up the toggle button
// and keeps both attributes plus the button icon in sync afterwards.
// No bundler in this project, so this merges into the shared window.Logpyre
// namespace rather than exporting an ES module.
window.Logpyre = window.Logpyre || {};

(function (ns) {
    var STORAGE_KEY = "logpyre-theme";

    var ICONS = {
        // Moon — shown while light mode is active; click switches to dark.
        light: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M20.354 15.354A9 9 0 0 1 8.646 3.646 9.003 9.003 0 1 0 20.354 15.354z"/></svg>',
        // Sun — shown while dark mode is active; click switches to light.
        dark: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><circle cx="12" cy="12" r="5" fill="currentColor"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></g></svg>',
    };

    function currentTheme() {
        return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    }

    // AG Grid's Theming API reads data-ag-theme-mode reactively (no grid API
    // call needed), so setting both attributes here is enough to keep the
    // grid in sync with the rest of the page — see gridTheme in index.js.
    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        document.documentElement.setAttribute("data-ag-theme-mode", theme);

        var btn = document.getElementById("theme-toggle");
        var icon = document.getElementById("theme-toggle-icon");
        if (!btn || !icon) return;

        icon.innerHTML = ICONS[theme];
        var nextTheme = theme === "dark" ? "light" : "dark";
        var label = "Switch to " + nextTheme + " mode";
        btn.setAttribute("aria-label", label);
        btn.setAttribute("title", label);
    }

    function toggleTheme() {
        var next = currentTheme() === "dark" ? "light" : "dark";
        localStorage.setItem(STORAGE_KEY, next);
        applyTheme(next);
    }

    function initTheme() {
        applyTheme(currentTheme());
        var btn = document.getElementById("theme-toggle");
        if (btn) btn.addEventListener("click", toggleTheme);
    }

    ns.toggleTheme = toggleTheme;
    ns.initTheme = initTheme;

    document.addEventListener("DOMContentLoaded", initTheme);
})(window.Logpyre);
