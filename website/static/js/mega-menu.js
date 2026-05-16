(function (window, document) {
    "use strict";

    const DEFAULT_LINK_GROUPS = [
        {
            title: "Organizations",
            links: [
                { label: "Organizations", href: "https://blt.owasp.org/organizations/", icon: "fa-building" },
                { label: "Register Organization", href: "https://blt.owasp.org/organization/register/", icon: "fa-plus" },
                { label: "Domains", href: "https://blt.owasp.org/domains/", icon: "fa-globe" },
                { label: "Map", href: "https://blt.owasp.org/map/", icon: "fa-map-marker-alt" },
                { label: "Bugs", href: "https://blt.owasp.org/issue/", icon: "fa-bug" },
                { label: "Bounties", href: "https://blt.owasp.org/hunt/", icon: "fa-search" },
            ],
        },
        {
            title: "Projects",
            links: [
                { label: "Projects", href: "https://blt.owasp.org/project/", icon: "fa-box" },
                { label: "Repositories", href: "https://blt.owasp.org/repo/", icon: "fa-code-branch" },
                { label: "Bid on Issues", href: "https://blt.owasp.org/bidding/", icon: "fa-money-bill-wave" },
                { label: "Funding", href: "https://blt.owasp.org/tomato/", icon: "fa-seedling" },
                { label: "GSOC PR Reports", href: "https://blt.owasp.org/gsoc/pr-report/", icon: "fa-code-pull-request" },
            ],
        },
        {
            title: "Community",
            links: [
                { label: "Users", href: "https://blt.owasp.org/users/", icon: "fa-user-friends" },
                { label: "Rooms", href: "https://blt.owasp.org/rooms/", icon: "fa-door-open" },
                { label: "Video Call", href: "https://blt.owasp.org/video-call/", icon: "fa-video" },
                { label: "Leaderboard", href: "https://blt.owasp.org/leaderboard/", icon: "fa-ranking-star" },
                { label: "Activity", href: "https://blt.owasp.org/activity/", icon: "fa-chart-line" },
            ],
        },
        {
            title: "Resources",
            links: [
                { label: "Search", href: "https://blt.owasp.org/search/", icon: "fa-magnifying-glass" },
                { label: "Report a Bug", href: "https://blt.owasp.org/report/", icon: "fa-flag" },
                { label: "Status", href: "https://blt.owasp.org/status/", icon: "fa-signal" },
                { label: "Roadmap", href: "https://blt.owasp.org/roadmap/", icon: "fa-map" },
                { label: "OWASP", href: "https://owasp.org/", icon: "fa-shield-halved" },
            ],
        },
    ];

    const DEFAULT_OPTIONS = {
        buttonId: "mega-menu-button",
        menuId: "mega-menu",
        buttonLabel: "Open mega menu",
        closeOnScrollDelta: 10,
        autoInit: true,
    };

    function ready(callback) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback);
        } else {
            callback();
        }
    }

    function mergeConfig(config) {
        return Object.assign({}, DEFAULT_OPTIONS, config || {});
    }

    function injectStyles() {
        if (document.getElementById("blt-mega-menu-styles")) {
            return;
        }

        const styles = document.createElement("style");
        styles.id = "blt-mega-menu-styles";
        styles.textContent = `
            .blt-mega-menu-button {
                align-items: center;
                background: #fff;
                border: 2px solid #e74c3c;
                border-radius: 8px;
                color: #e74c3c;
                cursor: pointer;
                display: inline-flex;
                font: inherit;
                gap: 8px;
                justify-content: center;
                min-height: 42px;
                min-width: 42px;
                padding: 8px 10px;
                position: relative;
                z-index: 10101;
            }

            .blt-mega-menu-button:hover,
            .blt-mega-menu-button:focus-visible {
                background: #e74c3c;
                color: #fff;
                outline: none;
            }

            .blt-mega-menu {
                background: #fff;
                border-bottom: 1px solid #e5e7eb;
                box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
                color: #1f2937;
                left: 0;
                max-height: 80vh;
                overflow-y: auto;
                position: fixed;
                right: 0;
                top: 80px;
                z-index: 10100;
            }

            .blt-mega-menu.hidden {
                display: none !important;
            }

            .blt-mega-menu__inner {
                display: grid;
                gap: 28px;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                margin: 0 auto;
                max-width: 1180px;
                padding: 24px;
            }

            .blt-mega-menu__heading {
                color: #e74c3c;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.04em;
                margin: 0 0 12px;
                text-transform: uppercase;
            }

            .blt-mega-menu__list {
                display: grid;
                gap: 6px;
                list-style: none;
                margin: 0;
                padding: 0;
            }

            .blt-mega-menu__link {
                align-items: center;
                border-radius: 6px;
                color: #374151;
                display: flex;
                gap: 10px;
                min-height: 36px;
                padding: 8px;
                text-decoration: none;
            }

            .blt-mega-menu__link:hover,
            .blt-mega-menu__link:focus-visible {
                background: #feeae9;
                color: #e74c3c;
                outline: none;
            }

            .blt-mega-menu__icon {
                color: #6b7280;
                text-align: center;
                width: 20px;
            }

            .blt-mega-menu__link:hover .blt-mega-menu__icon,
            .blt-mega-menu__link:focus-visible .blt-mega-menu__icon {
                color: #e74c3c;
            }

            .dark .blt-mega-menu,
            html.dark .blt-mega-menu {
                background: #111827;
                border-color: #374151;
                color: #f9fafb;
            }

            .dark .blt-mega-menu__link,
            html.dark .blt-mega-menu__link {
                color: #e5e7eb;
            }

            .dark .blt-mega-menu__link:hover,
            .dark .blt-mega-menu__link:focus-visible,
            html.dark .blt-mega-menu__link:hover,
            html.dark .blt-mega-menu__link:focus-visible {
                background: rgba(127, 29, 29, 0.3);
                color: #f87171;
            }

            @media (max-width: 767px) {
                .blt-mega-menu {
                    top: 64px;
                }

                .blt-mega-menu__inner {
                    grid-template-columns: 1fr;
                    padding: 18px;
                }
            }
        `;
        document.head.appendChild(styles);
    }

    function createIcon(iconName) {
        const icon = document.createElement("i");
        icon.setAttribute("aria-hidden", "true");
        icon.className = "blt-mega-menu__icon fas " + (iconName || "fa-circle");
        return icon;
    }

    function createMenu(config) {
        const menu = document.createElement("div");
        menu.id = config.menuId;
        menu.className = "blt-mega-menu hidden";
        menu.setAttribute("aria-hidden", "true");

        const inner = document.createElement("div");
        inner.className = "blt-mega-menu__inner";

        (config.groups || DEFAULT_LINK_GROUPS).forEach(function (group) {
            const section = document.createElement("section");
            const heading = document.createElement("h2");
            const list = document.createElement("ul");

            heading.className = "blt-mega-menu__heading";
            heading.textContent = group.title;
            list.className = "blt-mega-menu__list";

            (group.links || []).forEach(function (link) {
                const item = document.createElement("li");
                const anchor = document.createElement("a");

                anchor.className = "blt-mega-menu__link";
                anchor.href = link.href;
                anchor.appendChild(createIcon(link.icon));
                anchor.appendChild(document.createTextNode(link.label));

                if (link.external) {
                    anchor.target = "_blank";
                    anchor.rel = "noopener noreferrer";
                }

                item.appendChild(anchor);
                list.appendChild(item);
            });

            section.appendChild(heading);
            section.appendChild(list);
            inner.appendChild(section);
        });

        menu.appendChild(inner);
        document.body.appendChild(menu);
        return menu;
    }

    function createButton(config) {
        const button = document.createElement("button");
        const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        const firstSquare = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        const secondSquare = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        const thirdSquare = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        const fourthSquare = document.createElementNS("http://www.w3.org/2000/svg", "rect");

        button.id = config.buttonId;
        button.type = "button";
        button.className = "blt-mega-menu-button";
        button.setAttribute("aria-controls", config.menuId);
        button.setAttribute("aria-expanded", "false");
        button.setAttribute("aria-label", config.buttonLabel);

        icon.setAttribute("viewBox", "0 0 24 24");
        icon.setAttribute("width", "22");
        icon.setAttribute("height", "22");
        icon.setAttribute("aria-hidden", "true");
        [firstSquare, secondSquare, thirdSquare, fourthSquare].forEach(function (square, index) {
            const x = index % 2 === 0 ? "4" : "14";
            const y = index < 2 ? "4" : "14";
            square.setAttribute("x", x);
            square.setAttribute("y", y);
            square.setAttribute("width", "6");
            square.setAttribute("height", "6");
            square.setAttribute("rx", "1");
            square.setAttribute("fill", "currentColor");
            icon.appendChild(square);
        });
        button.appendChild(icon);

        const hamburger = document.getElementById("hamburger-button");
        if (hamburger && hamburger.parentElement) {
            hamburger.insertAdjacentElement("afterend", button);
            return button;
        }

        const nav = document.querySelector("nav");
        if (nav) {
            nav.insertAdjacentElement("afterbegin", button);
            return button;
        }

        document.body.insertAdjacentElement("afterbegin", button);
        return button;
    }

    function getButton(config) {
        const existing = document.getElementById(config.buttonId);
        if (existing) {
            existing.setAttribute("aria-controls", config.menuId);
            existing.setAttribute("aria-expanded", existing.getAttribute("aria-expanded") || "false");
            existing.setAttribute("aria-label", existing.getAttribute("aria-label") || config.buttonLabel);
            return existing;
        }
        return createButton(config);
    }

    function getMenu(config) {
        return document.getElementById(config.menuId) || document.querySelector(".mega-menu") || createMenu(config);
    }

    function setOpen(button, menu, isOpen) {
        menu.classList.toggle("hidden", !isOpen);
        menu.setAttribute("aria-hidden", String(!isOpen));
        button.setAttribute("aria-expanded", String(isOpen));
    }

    function init(userConfig) {
        const config = mergeConfig(userConfig || window.OWASPBLTMegaMenu);
        injectStyles();

        const button = getButton(config);
        const menu = getMenu(config);

        if (!button || !menu || button.dataset.bltMegaMenuReady === "true") {
            return;
        }

        button.dataset.bltMegaMenuReady = "true";
        setOpen(button, menu, false);

        let lastScrollPosition = window.pageYOffset;

        button.addEventListener("click", function (event) {
            event.stopPropagation();
            const isOpen = button.getAttribute("aria-expanded") === "true";
            setOpen(button, menu, !isOpen);
        });

        document.addEventListener("click", function (event) {
            const isOpen = button.getAttribute("aria-expanded") === "true";
            if (isOpen && !menu.contains(event.target) && !button.contains(event.target)) {
                setOpen(button, menu, false);
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && button.getAttribute("aria-expanded") === "true") {
                setOpen(button, menu, false);
                button.focus();
            }
        });

        window.addEventListener("scroll", function () {
            const currentScrollPosition = window.pageYOffset;
            const moved = Math.abs(currentScrollPosition - lastScrollPosition);
            if (button.getAttribute("aria-expanded") === "true" && moved > config.closeOnScrollDelta) {
                setOpen(button, menu, false);
            }
            lastScrollPosition = currentScrollPosition;
        });
    }

    window.BltMegaMenu = {
        init: init,
    };

    ready(function () {
        const config = mergeConfig(window.OWASPBLTMegaMenu);
        if (config.autoInit !== false) {
            init(config);
        }
    });
})(window, document);
