/**
 * Light / night chrome.
 *
 * Always sets html data-theme to light or dark before app.css paints
 * (load in <head> with no defer). Light colors live on :root; dark on
 * html[data-theme=dark]. data-theme=light exists so the no-JS media
 * query (html without data-theme) does not apply. First visit follows
 * prefers-color-scheme and does not write storage. A click writes
 * analysis_web.theme. Quota / private-mode failures are ignored
 * (same as runs.js).
 */
(function () {
  "use strict";

  var STORAGE_KEY = "analysis_web.theme";
  var root = document.documentElement;

  function stored() {
    try {
      var v = localStorage.getItem(STORAGE_KEY);
      if (v === "light" || v === "dark") return v;
    } catch (err) {
      /* private mode / quota */
    }
    return null;
  }

  function systemDark() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    );
  }

  function current() {
    return stored() || (systemDark() ? "dark" : "light");
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    var night = theme === "dark";
    btn.setAttribute("aria-pressed", night ? "true" : "false");
    btn.textContent = night ? "Light" : "Night";
    btn.setAttribute(
      "aria-label",
      night ? "Switch to light theme" : "Switch to night theme"
    );
  }

  apply(current());

  function bind() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    apply(current());
    btn.addEventListener("click", function () {
      var next =
        root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch (err2) {
        /* private mode / quota */
      }
      apply(next);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
