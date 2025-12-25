# Feature Checklist — OWASP BLT

This checklist maps feature cards (website/templates/features.html) to implementation files and current backend status. Status legend:

- Implemented — backend + UI present
- Partial — some backend pieces exist (services/consumers/commands) but needs audit/tests
- UI-only — only template/card present (no backend)
- Needs Audit — claims exist but require verification before enabling

- Chat Bot
  - Status: Partial
  - Location: website/templates/features.html, website/consumers.py, website/services/chatbot/* (audit consumers/services)

- BLT Slack Bot
  - Status: Implemented
  - Location: docs/bot-setup.md, website/templates/slack.html, website/services/slack/*

- Similarity-scan
  - Status: Partial
  - Location: website/templates/features.html, website/consumers.py (verify worker/queue code)

- AI Issue Generator
  - Status: Partial
  - Location: website/templates/features.html, website/services/ai_issue_generator.py (if present) — audit

- Automated PR Review
  - Status: Partial
  - Location: website/templates/features.html, website/services/pr_review/* — audit

- BACON (token / rewards)
  - Status: Implemented
  - Location: website/templates/bacon.html, website/templates/features.html (confirm smart-contract links and services)

- Sizzle (time tracking)
  - Status: Implemented
  - Location: website/templates/sizzle/, website/templates/features.html

- Template List
  - Status: Implemented
  - Location: website/templates/features.html, website/views/templates.py (or related views)

- Stats Dashboard / Website Stats
  - Status: Implemented
  - Location: website/templates/features.html, website/views/stats.py (or related views)

- Trademark Search
  - Status: Partial
  - Location: website/templates/features.html, website/services/trademark_search/* — verify external integration

- Teams / Organizations / Projects / Repositories
  - Status: Implemented
  - Location: website/models.py, website/views/*, website/templates/*

- Open Source Sorting Hat
  - Status: UI-only / Partial
  - Location: website/templates/features.html — verify backend service

- AI-Assisted Coder
  - Status: UI-only / Partial
  - Location: website/templates/features.html, website/services/* — audit

- Developer API & Swagger
  - Status: Implemented
  - Location: website/api/, possibly drf schema views

- Repo discovery & scanning
  - Status: Implemented
  - Location: website/management/commands/fetch_os_repos.py

- Seeded adventures / educational tasks
  - Status: Implemented
  - Location: website/management/commands/seed_adventures.py

- Roadmap / feature metadata
  - Status: Implemented
  - Location: website/views/core.py (RoadmapView.get_context_data), website/templates/roadmap*

- GitHub integrations & Actions links
  - Status: Partial
  - Location: website/templates/features.html, website/services/github_integration/* — verify hooks/actions

- Leaderboards, Points, Badges, Streaks
  - Status: Implemented (UI + models)
  - Location: website/templates/features.html, website/models.py (rewards/points)

- BLT Extension / Mobile (links to repos)
  - Status: UI-only (links)
  - Location: website/templates/features.html

- Developer Tools (template creation, repo tools)
  - Status: Partial/Implemented
  - Location: website/templates/features.html, website/views/dev_tools/*

- Stats / Analytics pipelines
  - Status: Partial
  - Location: website/views/stats.py, services/analytics/* — verify ETL

- Slack docs & setup
  - Status: Implemented (doc)
  - Location: docs/bot-setup.md, website/templates/slack.html

Recommendations / Next steps

- Audit all "Partial" and "UI-only" entries by searching for related services, consumers, and tests.
- Add or update tests under website/tests/ for features marked Partial/Implemented.
- For AI features, confirm environment/service credentials are NOT committed and are behind feature flags.
- If desired, persist this checklist as a living file and add issue links to items needing work.

Note: Genrated with CoPilot 3DEC2025 by kittenbytes
