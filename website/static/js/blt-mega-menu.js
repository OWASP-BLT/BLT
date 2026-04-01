/**
 * BLT Mega Menu - Drop-in Script
 *
 * Adds the OWASP BLT mega menu and icon to any site by dropping in this script.
 *
 * Usage:
 *   <script src="https://blt.owasp.org/static/js/blt-mega-menu.js"></script>
 *
 * The script auto-injects the mega menu bar at the top of <body>.
 * It is fully self-contained — no external dependencies required.
 */

(function () {
  "use strict";

  /* -------------------------------------------------------------------------
   * Config
   * ---------------------------------------------------------------------- */
  var BLT_BASE_URL = "https://blt.owasp.org";
  var BLT_LOGO_URL = BLT_BASE_URL + "/static/img/owasp-blt-logo.svg";

  var MENU_ITEMS = [
    {
      label: "Platform",
      icon: "🛡️",
      children: [
        { label: "Report a Bug",       url: BLT_BASE_URL + "/report/",          icon: "🐛" },
        { label: "Bug Bounties",        url: BLT_BASE_URL + "/hunts/",           icon: "💰" },
        { label: "Leaderboard",         url: BLT_BASE_URL + "/leaderboard/",     icon: "🏆" },
        { label: "Security Adventures", url: BLT_BASE_URL + "/adventures/",      icon: "🗺️" },
      ],
    },
    {
      label: "Community",
      icon: "👥",
      children: [
        { label: "Contributors",   url: BLT_BASE_URL + "/contributors/",  icon: "🤝" },
        { label: "Organizations",  url: BLT_BASE_URL + "/organizations/", icon: "🏢" },
        { label: "Social Feed",    url: BLT_BASE_URL + "/social/",        icon: "📣" },
        { label: "Education",      url: BLT_BASE_URL + "/education/",     icon: "📚" },
      ],
    },
    {
      label: "Developers",
      icon: "💻",
      children: [
        { label: "GitHub",           url: "https://github.com/OWASP-BLT/BLT", icon: "🐙" },
        { label: "API Docs",         url: BLT_BASE_URL + "/api/",              icon: "📡" },
        { label: "Chrome Extension", url: "https://chrome.google.com/webstore/detail/blt/", icon: "🔌" },
        { label: "Contributing",     url: "https://github.com/OWASP-BLT/BLT/blob/main/CONTRIBUTING.md", icon: "📝" },
      ],
    },
    {
      label: "Rewards",
      icon: "🥓",
      children: [
        { label: "Bacon Points",  url: BLT_BASE_URL + "/bacon/",       icon: "🪙" },
        { label: "Start a Hunt",  url: BLT_BASE_URL + "/start-hunt/",  icon: "🎯" },
        { label: "Prizes",        url: BLT_BASE_URL + "/prizes/",      icon: "🎁" },
        { label: "Sponsors",      url: BLT_BASE_URL + "/sponsors/",    icon: "❤️" },
      ],
    },
  ];

  /* -------------------------------------------------------------------------
   * CSS — injected into <head> once
   * ---------------------------------------------------------------------- */
  var CSS = [
    "#blt-mega-menu-bar{",
    "  all:initial;",
    "  display:block;",
    "  width:100%;",
    "  background:#fff;",
    "  border-bottom:2px solid #ef4444;",
    "  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;",
    "  font-size:14px;",
    "  z-index:2147483647;",
    "  position:relative;",
    "  box-sizing:border-box;",
    "}",
    "#blt-mega-menu-inner{",
    "  display:flex;",
    "  align-items:center;",
    "  max-width:1280px;",
    "  margin:0 auto;",
    "  padding:0 16px;",
    "  height:52px;",
    "  gap:4px;",
    "}",
    "#blt-mega-menu-logo{",
    "  display:flex;",
    "  align-items:center;",
    "  gap:8px;",
    "  text-decoration:none !important;",
    "  margin-right:16px;",
    "  flex-shrink:0;",
    "}",
    "#blt-mega-menu-logo img{",
    "  height:32px;",
    "  width:auto;",
    "}",
    "#blt-mega-menu-logo span{",
    "  font-size:13px;",
    "  font-weight:700;",
    "  color:#ef4444;",
    "  white-space:nowrap;",
    "}",
    ".blt-menu-item{",
    "  position:relative;",
    "}",
    ".blt-menu-btn{",
    "  display:flex;",
    "  align-items:center;",
    "  gap:4px;",
    "  padding:6px 12px;",
    "  background:none;",
    "  border:none;",
    "  cursor:pointer;",
    "  font-size:13px;",
    "  font-weight:600;",
    "  color:#374151;",
    "  border-radius:6px;",
    "  transition:background 0.15s,color 0.15s;",
    "  white-space:nowrap;",
    "}",
    ".blt-menu-btn:hover{",
    "  background:#fef2f2;",
    "  color:#ef4444;",
    "}",
    ".blt-menu-btn .blt-caret{",
    "  font-size:9px;",
    "  transition:transform 0.2s;",
    "  display:inline-block;",
    "}",
    ".blt-menu-item.open .blt-caret{",
    "  transform:rotate(180deg);",
    "}",
    ".blt-dropdown{",
    "  display:none;",
    "  position:absolute;",
    "  top:calc(100% + 6px);",
    "  left:0;",
    "  background:#fff;",
    "  border:1px solid #e5e7eb;",
    "  border-radius:10px;",
    "  box-shadow:0 10px 30px rgba(0,0,0,0.12);",
    "  min-width:220px;",
    "  padding:8px;",
    "  z-index:2147483647;",
    "}",
    ".blt-menu-item.open .blt-dropdown{",
    "  display:block;",
    "  animation:blt-fade-in 0.15s ease;",
    "}",
    "@keyframes blt-fade-in{",
    "  from{opacity:0;transform:translateY(-6px);}",
    "  to{opacity:1;transform:translateY(0);}",
    "}",
    ".blt-dropdown a{",
    "  display:flex !important;",
    "  align-items:center;",
    "  gap:10px;",
    "  padding:9px 12px;",
    "  border-radius:7px;",
    "  text-decoration:none !important;",
    "  color:#374151 !important;",
    "  font-size:13px;",
    "  font-weight:500;",
    "  transition:background 0.12s,color 0.12s;",
    "}",
    ".blt-dropdown a:hover{",
    "  background:#fef2f2;",
    "  color:#ef4444 !important;",
    "}",
    ".blt-dropdown a .blt-icon{",
    "  font-size:16px;",
    "  width:22px;",
    "  text-align:center;",
    "  flex-shrink:0;",
    "}",
    "#blt-mega-menu-cta{",
    "  margin-left:auto;",
    "  display:flex;",
    "  align-items:center;",
    "  gap:8px;",
    "  flex-shrink:0;",
    "}",
    "#blt-mega-menu-cta a{",
    "  padding:6px 16px;",
    "  border-radius:6px;",
    "  font-size:13px;",
    "  font-weight:700;",
    "  text-decoration:none !important;",
    "  transition:background 0.15s,color 0.15s;",
    "  white-space:nowrap;",
    "}",
    "#blt-mega-menu-cta .blt-btn-primary{",
    "  background:#ef4444;",
    "  color:#fff !important;",
    "}",
    "#blt-mega-menu-cta .blt-btn-primary:hover{",
    "  background:#dc2626;",
    "}",
    "#blt-mega-menu-cta .blt-btn-secondary{",
    "  background:#f3f4f6;",
    "  color:#374151 !important;",
    "}",
    "#blt-mega-menu-cta .blt-btn-secondary:hover{",
    "  background:#e5e7eb;",
    "}",
    /* Mobile hamburger */
    "#blt-hamburger{",
    "  display:none;",
    "  background:none;",
    "  border:none;",
    "  cursor:pointer;",
    "  padding:6px;",
    "  margin-left:auto;",
    "  font-size:20px;",
    "  color:#374151;",
    "}",
    "#blt-mobile-menu{",
    "  display:none;",
    "  flex-direction:column;",
    "  background:#fff;",
    "  border-top:1px solid #e5e7eb;",
    "  padding:8px 16px 16px;",
    "}",
    "#blt-mobile-menu.open{ display:flex; }",
    ".blt-mobile-section-title{",
    "  font-size:11px;",
    "  font-weight:700;",
    "  text-transform:uppercase;",
    "  letter-spacing:0.08em;",
    "  color:#9ca3af;",
    "  padding:12px 0 4px;",
    "}",
    ".blt-mobile-link{",
    "  display:flex !important;",
    "  align-items:center;",
    "  gap:10px;",
    "  padding:9px 4px;",
    "  text-decoration:none !important;",
    "  color:#374151 !important;",
    "  font-size:14px;",
    "  border-bottom:1px solid #f3f4f6;",
    "}",
    ".blt-mobile-link:hover{ color:#ef4444 !important; }",
    "@media(max-width:768px){",
    "  .blt-menu-item{ display:none; }",
    "  #blt-mega-menu-cta{ display:none; }",
    "  #blt-hamburger{ display:block; }",
    "}",
  ].join("\n");

  /* -------------------------------------------------------------------------
   * Build HTML
   * ---------------------------------------------------------------------- */
  function buildMenu() {
    var menuItemsHTML = MENU_ITEMS.map(function (section) {
      var childrenHTML = section.children
        .map(function (child) {
          return (
            '<a href="' + child.url + '" target="_blank" rel="noopener noreferrer">' +
            '<span class="blt-icon">' + child.icon + "</span>" +
            "<span>" + child.label + "</span>" +
            "</a>"
          );
        })
        .join("");

      return (
        '<div class="blt-menu-item">' +
        '<button class="blt-menu-btn">' +
        '<span>' + section.icon + " " + section.label + "</span>" +
        '<span class="blt-caret">▾</span>' +
        "</button>" +
        '<div class="blt-dropdown">' + childrenHTML + "</div>" +
        "</div>"
      );
    }).join("");

    // Mobile menu — flat list grouped by section
    var mobileHTML = MENU_ITEMS.map(function (section) {
      var linksHTML = section.children
        .map(function (child) {
          return (
            '<a class="blt-mobile-link" href="' + child.url + '" target="_blank" rel="noopener noreferrer">' +
            '<span>' + child.icon + "</span>" +
            "<span>" + child.label + "</span>" +
            "</a>"
          );
        })
        .join("");
      return (
        '<div class="blt-mobile-section-title">' + section.icon + " " + section.label + "</div>" +
        linksHTML
      );
    }).join("");

    return (
      '<div id="blt-mega-menu-bar">' +
        '<div id="blt-mega-menu-inner">' +
          '<a id="blt-mega-menu-logo" href="' + BLT_BASE_URL + '" target="_blank" rel="noopener noreferrer">' +
            '<img src="' + BLT_LOGO_URL + '" alt="OWASP BLT" />' +
            "<span>OWASP BLT</span>" +
          "</a>" +
          menuItemsHTML +
          '<div id="blt-mega-menu-cta">' +
            '<a class="blt-btn-secondary" href="' + BLT_BASE_URL + '/report/" target="_blank" rel="noopener noreferrer">🐛 Report Bug</a>' +
            '<a class="blt-btn-primary" href="' + BLT_BASE_URL + '/accounts/signup/" target="_blank" rel="noopener noreferrer">Join BLT</a>' +
          "</div>" +
          '<button id="blt-hamburger" aria-label="Open BLT menu">☰</button>' +
        "</div>" +
        '<div id="blt-mobile-menu">' + mobileHTML + "</div>" +
      "</div>"
    );
  }

  /* -------------------------------------------------------------------------
   * Init
   * ---------------------------------------------------------------------- */
  function init() {
    // Inject CSS
    var style = document.createElement("style");
    style.id = "blt-mega-menu-styles";
    style.textContent = CSS;
    document.head.appendChild(style);

    // Inject HTML at top of body
    var wrapper = document.createElement("div");
    wrapper.innerHTML = buildMenu();
    var menuEl = wrapper.firstChild;
    document.body.insertBefore(menuEl, document.body.firstChild);

    // Dropdown toggle — desktop
    var items = menuEl.querySelectorAll(".blt-menu-item");
    items.forEach(function (item) {
      var btn = item.querySelector(".blt-menu-btn");
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var isOpen = item.classList.contains("open");
        // Close all first
        items.forEach(function (i) { i.classList.remove("open"); });
        if (!isOpen) item.classList.add("open");
      });
    });

    // Close dropdowns on outside click
    document.addEventListener("click", function () {
      items.forEach(function (i) { i.classList.remove("open"); });
    });

    // Mobile hamburger toggle
    var hamburger = menuEl.querySelector("#blt-hamburger");
    var mobileMenu = menuEl.querySelector("#blt-mobile-menu");
    if (hamburger && mobileMenu) {
      hamburger.addEventListener("click", function (e) {
        e.stopPropagation();
        mobileMenu.classList.toggle("open");
        hamburger.textContent = mobileMenu.classList.contains("open") ? "✕" : "☰";
      });
    }
  }

  // Run after DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
