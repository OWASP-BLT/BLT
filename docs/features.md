# OWASP BLT — Features (Up to Date)

OWASP BLT is a gamified crowd-sourced QA testing and vulnerability disclosure platform for websites, apps, git repositories, projects, and more. The platform helps coders and security researchers discover organizations, repositories, and projects to test and report to. Our team has created dozens of open-source tools to assist in our main vision, including tools specific to the OWASP foundation. We embrace the AI revolution and have developed AI-powered tools and processes for efficient coding in harmony between humans and AI.

This document summarizes BLT features implemented or surfaced in the current codebase. Use website/templates/features.html as the UI source-of-truth and the referenced code files for implementation details.

Core
- Backend: Django (project root blt/) with views, management commands, REST endpoints.
- Frontend: Django templates + Tailwind CSS. Static JS lives under website/static/.
- Real-time: Django Channels + Redis used for WebSocket consumers.
- Data: PostgreSQL for primary data; Redis for cache/queues.

Authentication & Access
- Local accounts and OAuth providers supported.
- Teams, Organizations, Projects, and Repository membership modeled and surfaced in UI.

QA Testing & Vulnerability Disclosure
- Gamified crowd-sourced testing across websites, apps, git repositories, and projects.
- Helps coders and security researchers discover organizations, repositories, and projects to test and report to.
- Bug discovery, reporting, and issue tracking UIs implemented.
- Repository discovery and basic scanning logic implemented in website/management/commands/fetch_os_repos.py.

Automation & Bots
- BLT Slack Bot and related setup documented (docs/bot-setup.md) and has UI pages.
- Some automation features (GitHub integration, GitHub Actions links) are surfaced in the UI.

Gamification & Rewards
- BACON token / rewards system present (templates and pages).
- Points, badges, leaderboards, and streak systems are implemented or surfaced.

AI & Advanced Tools (evolving)
- Chat Bot, AI Issue Generator, PR Review, Similarity-scan, AI-Assisted Coder appear as UI cards. Many are in-progress or have partial backend support; treat them as feature-flagged or experimental until code is audited.

Time Tracking & Productivity
- Sizzle (time tracking) templates and pages exist.

Analytics & Dashboards
- Stats Dashboard and Website Stats pages are present.

Developer Tools & Templates
- Template List and developer API/Swagger surfaced.
- Trademark Search and other utilities are available as UI cards.

Seeded Content & Educational Features
- Seeded "adventures" and tasks are created via website/management/commands/seed_adventures.py.

Docs & Contribution
- Contribution guide enforces Poetry, pre-commit, Black/isort/ruff, djLint, and JS console rule. Follow CONTRIBUTING.md for development workflow and CI rules.

How to verify implementation
- UI cards: website/templates/features.html
- Seeded adventures: website/management/commands/seed_adventures.py
- Repo discovery: website/management/commands/fetch_os_repos.py
- Roadmap/feature metadata: website/views/core.py (RoadmapView)
- Slack Bot docs: docs/bot-setup.md
- Contribution rules and linters: CONTRIBUTING.md

Notes
- Many AI features are UI-first. Before enabling in production, audit the backend and any external services they depend on.
- Keep this doc updated when adding new feature cards or exposing experimental features in the UI.