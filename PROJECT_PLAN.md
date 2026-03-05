# OWASP BLT — Project Plan

> **Note:** This document was generated with Copilot assistance and reflects the current state of the codebase, existing planning documents, and community priorities. It is a living document — please submit a PR for corrections or updates.

---

## 1. Vision & Goals

**OWASP BLT (Bug Logging Tool)** is a gamified, crowd-sourced QA testing and vulnerability disclosure platform. Our mission is to make it easy for security researchers, developers, and organizations to discover, report, and fix bugs — while building a sustainable, open-source ecosystem of complementary tools.

### Core Objectives

1. **Empower Security Researchers** — Give individual testers (from students to professionals) a structured way to find meaningful testing opportunities, earn recognition, and build their portfolio.
2. **Serve Organizations & OWASP Projects** — Provide a centralized hub where organizations manage multiple repositories, run bug bounties, and collaborate with contributors.
3. **Build an Open Ecosystem** — Decompose the monolith into focused, independently deployable services so each tool can evolve without blocking the others.
4. **Embrace AI** — Integrate AI-powered tooling (issue generation, PR review, similarity scanning, duplicate detection) to improve developer efficiency.
5. **Sustain Contributors** — Drive long-term participation via gamification, BACON token rewards, staking, badges, and leaderboards.

---

## 2. Target Users (Personas)

| Persona | Summary | Key Needs |
|---------|---------|-----------|
| **Alex Rivera** — Aspiring Security Researcher | Student/freelancer building a security portfolio | Skill-building challenges, earning rewards, community recognition |
| **Frank Patel** — Startup Founder | CTO of a growing company with limited security budget | Easy onboarding, domain scanning, affordable vulnerability reports |
| **Harold Linwood** — OWASP Program Manager | Manages 200+ OWASP projects across the community | Centralized org management, role-based access, community incentive programs |

---

## 3. Current Architecture

BLT is a **Django 5.1+ monolith** with the following layers:

- **Backend**: Django (views, management commands, REST API via DRF)
- **Frontend**: Django Templates + Tailwind CSS; static JS in `website/static/`
- **Real-time**: Django Channels + Redis (WebSocket consumers for chat, video, similarity scan)
- **Database**: PostgreSQL (primary) + Redis (cache/queues)
- **External integrations**: GitHub API, Slack API, OAuth providers, Bitcoin/BCH, SendGrid, Google Cloud Storage

See [`docs/architecture.md`](docs/architecture.md) for detailed diagrams and [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) for the component-by-component extraction strategy.

---

## 4. Feature Priorities

Features are grouped by strategic importance to the core mission. Ratings are based on community input (see [issue #5617](https://github.com/OWASP-BLT/BLT/issues/5617)).

### Tier 1 — Core (Always Keep)

These features are essential to the bug bounty and QA workflow and will remain in the BLT monolith:

| Feature | Status | Notes |
|---------|--------|-------|
| Bug Reporting & Issue Management | ✅ Implemented | Core workflow |
| Bug Bounties / Hunts | ✅ Implemented | Core workflow |
| Organizations & Domains | ✅ Implemented | Core entities |
| Projects & Repositories | ✅ Implemented | Core entities |
| Users & Authentication (OAuth) | ✅ Implemented | Core infrastructure |
| Leaderboard / Scoreboard | ✅ Implemented | Drives engagement |
| Badges & Points | ✅ Implemented | Core gamification |
| Challenges (User & Team) | ✅ Implemented | Core gamification |
| Feed / Activity Stream | ✅ Implemented | Community engagement |
| Developer API & Swagger | ✅ Implemented | Integration foundation |
| Contributors | ✅ Implemented | Repo/project tracking |
| GitHub Issues Integration | ✅ Implemented | Dev workflow |

### Tier 2 — Important Secondary

Keep and improve; some are candidates for eventual service extraction:

| Feature | Status | Notes |
|---------|--------|-------|
| BACON Token / Rewards | ✅ Implemented | Needs blockchain service extraction (Phase 3) |
| Staking System | ✅ Implemented | Needs extraction with BACON service |
| Education Platform | ✅ Implemented | Extract to `blt-academy` (Phase 2) |
| Security Labs / Simulation | ✅ Implemented | Extract to `blt-security-labs` (Phase 2) |
| Hackathons | ✅ Implemented | Extract to `blt-hackathons` (Phase 3) |
| Slack Bot Integration | ✅ Implemented | Extract to `blt-slack-integration` (Phase 2) |
| Open Source Sorting Hat | 🔵 Partial | Extract to `blt-ossh` (Phase 2) |
| Teams | ✅ Implemented | Keep in core |
| Jobs Board | ✅ Implemented | Extract to `blt-jobs` (Phase 3) |
| Roadmap | ✅ Implemented | Keep in core |

### Tier 3 — Evaluate / Experimental

These features need auditing and may be trimmed or promoted:

| Feature | Status | Notes |
|---------|--------|-------|
| AI Chat Bot | 🔵 Partial | Audit backend; enable with feature flag |
| AI Issue Generator | 🔵 Partial | Audit backend; enable with feature flag |
| AI PR Review | 🔵 Partial | Audit backend; enable with feature flag |
| Similarity Scanner | 🔵 Partial | Audit backend; enable with feature flag |
| AI Duplicate Detection (embeddings) | 🔵 Partial | PR #5964 adds vector similarity |
| Trademark Search | 🔵 Partial | External USPTO calls; extract to service |
| Sizzle (Time Tracking) | ✅ Implemented | Keep in core; link to project workflow |
| Analytics Dashboard | 🔵 Partial | Consider analytics service extraction |
| Video Call | ✅ Stub | Replace with Jitsi/Daily.co SDK embed |
| Messaging / Chat Rooms | ✅ Implemented | Extract to messaging service (Phase 3) |
| Stats / Reported IPs | ✅ Implemented | Keep in core |

---

## 5. Development Phases

The plan is organized into four phases, each building on the previous. Phases are aligned with the detailed extraction strategy in [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).

---

### Phase 0 — Stabilize & Document (In Progress)

**Goal**: Establish a stable foundation with clear documentation, consistent code quality, and well-tested core features before beginning any extraction.

| Task | Owner | Status |
|------|-------|--------|
| Enforce pre-commit hooks (Black, isort, ruff, djLint) | Dev team | ✅ Done |
| Document architecture (`docs/architecture.md`) | Dev team | ✅ Done |
| Document features and checklist (`docs/features.md`, `docs/feature-checklist.md`) | Dev team | ✅ Done |
| Create `MIGRATION_PLAN.md` with component analysis | Dev team | ✅ Done |
| Create `PROJECT_PLAN.md` (this document) | Dev team | ✅ Done |
| Add tests for core API views (LikeIssue, FlagIssue, DeleteIssue) | Dev team | ✅ Done (PR #5949) |
| Audit and fix unused imports / narrow exception handling | Dev team | ✅ Done (PR #5989) |
| Fix URL encoding and hardcoded domain references | Dev team | ✅ Done (PRs #5988, #5991) |
| Fix OpenAI and BlueSky error handling | Dev team | ✅ Done (PR #5978) |
| Expand test coverage for all Tier 1 features | Dev team | 🔲 In Progress |
| Write `API_CONTRACTS.md` documenting all public REST endpoints | Dev team | 🔲 Pending |

---

### Phase 1 — Already Separate / Stub-Ready

**Goal**: Finish cleanly separating components that are already mostly decoupled.

| Component | Target Repo | Effort | Status |
|-----------|-------------|--------|--------|
| Browser Extension | [BLT-Extension](https://github.com/OWASP-BLT/BLT-Extension) | — | ✅ Separate |
| GitHub Action | [BLT-Action](https://github.com/OWASP-BLT/BLT-Action) | — | ✅ Separate |
| Flutter Mobile App | [BLT-Flutter](https://github.com/OWASP-BLT/BLT-Flutter) | — | ✅ Separate |
| Video Call (stub → Jitsi embed) | [BLT-SafeCloak](https://github.com/OWASP-BLT/BLT-SafeCloak) | Hours | 🔲 Pending |

**Phase 1 milestones:**
- [ ] Verify Extension and Action only call BLT's public REST API
- [ ] Replace video call stub with a working Jitsi iframe integration
- [ ] Write `API_CONTRACTS.md` for endpoints used by Extension and Action

---

### Phase 2 — Quick Migrations (1–2 Sprints Each)

**Goal**: Extract self-contained features with minimal core dependencies.

| Component | Target Repo | Effort | Key Dependency |
|-----------|-------------|--------|---------------|
| Slack Bot / Handlers | [BLT-Lettuce](https://github.com/OWASP-BLT/BLT-Lettuce) | 1–2 sprints | `Domain`, `Hunt`, `Issue`, `Project` via API |
| Open Source Sorting Hat | [BLT-OSSH](https://github.com/OWASP-BLT/BLT-OSSH) | 1 sprint | `Repo` via API |
| Education Platform | [BLT-University](https://github.com/OWASP-BLT/BLT-University) | 1–2 sprints | `UserProfile` via JWT |
| Security Labs / Simulation | *(new repo needed)* | 1 sprint | Django `auth.User` only |
| Trademark Search | [BLT-Enforcement](https://github.com/OWASP-BLT/BLT-Enforcement) | 1 sprint | No core dependency |

**Phase 2 milestones:**
- [ ] Add REST API endpoints for all models the Slack bot currently queries via ORM
- [ ] Migrate Slack bot ORM calls to API calls
- [ ] Create isolated `ossh` Django app; replace `Repo` ORM query with API call
- [ ] Create isolated `education` Django app; JWT-authenticated user identity
- [ ] Create isolated `simulation` Django app with no `UserProfile` coupling
- [ ] Move `Trademark` models and views to isolated `trademarks` Django app

---

### Phase 3 — Complex Migrations (Multiple Sprints)

**Goal**: Extract deeply coupled features that require new infrastructure or API contracts.

| Component | Target Repo | Effort | Key Blockers |
|-----------|-------------|--------|-------------|
| BACON Token System | [BLT-Rewards](https://github.com/OWASP-BLT/BLT-Rewards) | 4+ sprints | Badge/role API, Slack service, Bitcoin RPC auth |
| Staking System | BLT-Rewards or new | 4+ sprints | `BaconEarning`, `Challenge`, `Issue` API contracts |
| Hackathons | [BLT-Hackathons](https://github.com/OWASP-BLT/BLT-Hackathons) | 3–4 sprints | `GitHubIssue`, `Contributor`, `Org`, `Repo` via API |
| Messaging / Chat Rooms | *(new repo needed)* | 3–4 sprints | WebSocket infra, `UserProfile` via JWT |
| Jobs Board | [BLT-Jobs](https://github.com/OWASP-BLT/BLT-Jobs) | 2–3 sprints | `Organization`, `UserProfile` via API |

**Phase 3 milestones:**
- [ ] Add `/api/v1/users/{username}/roles/` endpoint to replace ORM badge checks in BACON views
- [ ] Document API contract shapes for Staking System's ORM dependencies
- [ ] Extract job-related views from `company.py` to `website/views/jobs.py`
- [ ] Replace `GitHubIssue` ORM queries in `hackathon.py` with API calls
- [ ] Create `messaging` Django app; migrate `Room`, `Thread`, `Message` models

---

### Phase 4 — AI & Advanced Features

**Goal**: Stabilize and productionize experimental AI features behind feature flags.

| Feature | Current State | Target State |
|---------|--------------|-------------|
| AI Chat Bot | Partial (consumers.py) | Fully tested, feature-flagged |
| AI Issue Generator | Partial (services/) | Audited + tested |
| AI PR Review | Partial (services/) | Audited + tested |
| Similarity Scanner | Partial (consumers.py) | Worker/queue audited |
| Vector Duplicate Detection | PR #5964 (in progress) | Merged + tested |
| Analytics Service | Partial (stats.py) | Optional separate OLAP store |

**Phase 4 milestones:**
- [ ] Audit all AI feature backends for missing credentials or broken integrations
- [ ] Add feature flags for all AI features (environment variable controlled)
- [ ] Confirm no secrets committed for any external AI service
- [ ] Add integration tests for AI endpoints

---

## 6. Architecture Roadmap

### Near-Term (Phase 0–1)

```
[BLT Monolith]
    ├── Core (Bugs, Bounties, Orgs, Domains, Users, API)
    ├── Slack Bot (ORM calls → will become API calls)
    ├── Education (self-contained, will become Django app)
    ├── Security Labs (self-contained, will become Django app)
    ├── Trademark Search (external API only, will become Django app)
    └── Video Call (stub → Jitsi iframe)

[Already Separate]
    ├── BLT-Extension (browser extension → calls /api/)
    ├── BLT-Action (GitHub Action → calls /api/)
    └── BLT-Flutter (mobile app → calls /api/)
```

### Long-Term (Phase 2–3)

```
[BLT Core API]  ← single source of truth for shared data
    ├── REST API (/api/v1/)
    └── Auth / JWT

[Independently Deployable Services]
    ├── blt-slack-integration   (BLT-Lettuce / BLT-Sammich)
    ├── blt-academy             (BLT-University)
    ├── blt-security-labs       (new repo)
    ├── blt-ossh                (BLT-OSSH)
    ├── blt-trademark-service   (BLT-Enforcement)
    ├── blt-hackathons          (BLT-Hackathons)
    ├── blt-jobs                (BLT-Jobs)
    ├── blt-messaging-service   (new repo)
    └── blt-bacon-service       (BLT-Rewards, includes staking)
```

---

## 7. Key Repositories

| Repository | Purpose | Status |
|------------|---------|--------|
| [BLT](https://github.com/OWASP-BLT/BLT) | Core Django monolith | Active |
| [BLT-Flutter](https://github.com/OWASP-BLT/BLT-Flutter) | Official mobile app | Active |
| [BLT-Extension](https://github.com/OWASP-BLT/BLT-Extension) | Browser extension | Active |
| [BLT-Action](https://github.com/OWASP-BLT/BLT-Action) | GitHub Action | Active |
| [BLT-Lettuce](https://github.com/OWASP-BLT/BLT-Lettuce) | Intelligent Slack bot | Active |
| [BLT-Sammich](https://github.com/OWASP-BLT/BLT-Sammich) | Slack bot for BLT | Active |
| [BLT-Rewards](https://github.com/OWASP-BLT/BLT-Rewards) | BACON token system | Active |
| [BLT-University](https://github.com/OWASP-BLT/BLT-University) | Security courses | Active |
| [BLT-OSSH](https://github.com/OWASP-BLT/BLT-OSSH) | Open Source Sorting Hat | Active |
| [BLT-Hackathons](https://github.com/OWASP-BLT/BLT-Hackathons) | Hackathon platform | Active |
| [BLT-Jobs](https://github.com/OWASP-BLT/BLT-Jobs) | Community job board | Active |
| [BLT-Enforcement](https://github.com/OWASP-BLT/BLT-Enforcement) | Trademark search tools | Active |
| [BLT-SafeCloak](https://github.com/OWASP-BLT/BLT-SafeCloak) | Secure video chat | Active |
| BLT-security-labs | CTF/simulation labs | ⚠️ New repo needed |
| BLT-messaging-service | Real-time messaging | ⚠️ New repo needed |

---

## 8. Contributing

We welcome contributors of all skill levels. Here's how to get started:

1. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full contribution workflow.
2. Check [`docs/feature-checklist.md`](docs/feature-checklist.md) for features that need implementation or tests.
3. Check [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) for extraction tasks and the Copilot prompts associated with each.
4. Look for issues tagged `good-first-issue` or `help-wanted` on GitHub.

### Development Setup

```bash
# Using Docker (recommended)
cp .env.example .env
docker-compose up

# Local development
poetry install
python manage.py migrate
python manage.py loaddata website/fixtures/initial_data.json
python manage.py runserver
```

### Code Quality Requirements

| Tool | Purpose | Enforced by |
|------|---------|-------------|
| Black | Code formatting | pre-commit |
| isort | Import sorting | pre-commit |
| ruff | Linting & auto-fixes | pre-commit |
| djLint | Template formatting | pre-commit |

Always run `pre-commit run --all-files` before committing.

### Running Tests

```bash
# Quick tests (excludes slow Selenium tests)
poetry run python manage.py test --exclude-tag=slow --parallel --failfast

# Full test suite
poetry run python manage.py test --parallel --failfast
```

---

## 9. Success Metrics

| Metric | Current Baseline | Target |
|--------|-----------------|--------|
| Test coverage (core features) | Partial | 80%+ on Tier 1 features |
| Open issues with reproduction steps | Variable | 100% of filed issues |
| API endpoints documented | Partial | 100% in `API_CONTRACTS.md` |
| Components extracted per plan | 0 / 13 | All Phase 1–2 by end of year |
| Pre-commit pass rate on new PRs | Variable | 100% |
| AI features behind feature flags | 0 / 5 | 100% before production enable |

---

## 10. Related Documents

| Document | Description |
|----------|-------------|
| [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) | Detailed component-by-component extraction plan with Copilot prompts |
| [`docs/architecture.md`](docs/architecture.md) | System architecture diagrams (Mermaid) |
| [`docs/features.md`](docs/features.md) | Full feature list with implementation locations |
| [`docs/feature-checklist.md`](docs/feature-checklist.md) | Feature status checklist (Partial / Implemented / UI-only) |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guidelines, code standards, and PR process |
| [`SECURITY.md`](SECURITY.md) | Security policy and responsible disclosure |
| [`docs/Personas/`](docs/Personas/) | User personas driving product decisions |
