(function () {
  "use strict";

  // Pairs with the inline <head> script that sets data-theme before paint
  // (see index.html / fdp/index.html) - this just wires up the toggle
  // button and persists the choice. Keep the two theme names in sync with
  // css/tailwind.css's `@plugin "daisyui" { themes: ... }` line.
  const LIGHT = "corporate";
  const DARK = "business";

  function current() {
    return document.documentElement.getAttribute("data-theme") === DARK ? DARK : LIGHT;
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("nhse-theme", theme);
    document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
      btn.setAttribute("aria-pressed", String(theme === DARK));
      btn.textContent = theme === DARK ? "☀️ Light" : "🌙 Dark";
    });
  }

  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => apply(current() === DARK ? LIGHT : DARK));
  });

  apply(current());
})();
