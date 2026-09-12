(function () {
  "use strict";

  function showScenario(root, scen) {
    root.querySelectorAll(".forecast-panel").forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-scenario") !== scen;
    });
    root.querySelectorAll(".forecast-fallback").forEach(function (details) {
      var match = details.getAttribute("data-scenario") === scen;
      details.hidden = !match;
      details.open = match;
    });
    root.querySelectorAll(".forecast-chips button").forEach(function (btn) {
      btn.setAttribute(
        "aria-pressed",
        btn.getAttribute("data-scenario") === scen ? "true" : "false"
      );
    });
  }

  document.querySelectorAll("[data-forecast]").forEach(function (root) {
    root.classList.add("has-js");
    root.querySelectorAll(".forecast-chips button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        showScenario(root, btn.getAttribute("data-scenario") || "base");
      });
    });
    showScenario(root, "base");
  });

  var article = document.querySelector(".reading-article");
  var rail = document.querySelector(".reading-rail");
  var chips = document.querySelector(".reading-chips");
  if (!article) {
    return;
  }

  var sections = Array.prototype.slice.call(
    article.querySelectorAll("section[id], .report-body h2[id]")
  );
  if (!sections.length) {
    return;
  }

  function chapterOf(id) {
    var node = document.getElementById(id);
    if (!node) {
      return "";
    }
    if (node.matches("section[id]")) {
      return node.id;
    }
    var parent = node.closest("section[id]");
    return parent ? parent.id : "";
  }

  function setCurrent(id) {
    var chapter = chapterOf(id) || id;
    document.querySelectorAll(".reading-rail a, .reading-chips a").forEach(function (a) {
      var href = (a.getAttribute("href") || "").replace("#", "");
      var on = href === id || href === chapter;
      if (on) {
        a.setAttribute("aria-current", href === id ? "location" : "true");
      } else {
        a.removeAttribute("aria-current");
      }
    });
    if (rail) {
      rail.querySelectorAll(".reading-rail-h2").forEach(function (ul) {
        var parent = ul.getAttribute("data-parent");
        ul.hidden = parent !== chapter;
      });
    }
    if (chips) {
      chips.querySelectorAll("a").forEach(function (a) {
        var href = (a.getAttribute("href") || "").replace("#", "");
        a.setAttribute("aria-pressed", href === chapter ? "true" : "false");
      });
    }
  }

  if (rail) {
    rail.querySelectorAll(".reading-rail-h2").forEach(function (ul) {
      ul.hidden = true;
    });
  }

  if ("IntersectionObserver" in window) {
    var visible = [];
    var obs = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          var id = entry.target.id;
          var idx = visible.indexOf(id);
          if (entry.isIntersecting && idx < 0) {
            visible.push(id);
          } else if (!entry.isIntersecting && idx >= 0) {
            visible.splice(idx, 1);
          }
        });
        if (visible.length) {
          setCurrent(visible[0]);
        }
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: 0 }
    );
    sections.forEach(function (sec) {
      obs.observe(sec);
    });
  }

  if (location.hash) {
    setCurrent(location.hash.slice(1));
  } else if (sections[0]) {
    setCurrent(sections[0].id);
  }
})();
