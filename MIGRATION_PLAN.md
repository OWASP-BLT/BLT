# BLT Components Summary and Vitality

---

## Current Status Assessment

> **Legend:**
> - ✅ **Already Separate** – Code lives outside the monolith or is a pure stub with no DB/model coupling.
> - 🟡 **Mostly Done** – Self-contained view + models, but still shares `models.py` and needs an API contract to fully decouple.
> - 🔵 **Quick Migration** – Minimal core dependencies; extractable in a sprint or two.
> - 🔴 **Complex Migration** – Deep coupling to core models, shared auth, or requires new infrastructure.

---

### ✅ Phase 1 — Already Separate / Stub-Ready (Do These First)

#### 1. BLT Browser Extension → `blt-browser-extension`
- **Status**: ✅ Already separate codebase — no views, models, or templates exist in this repo.
- **Files in BLT core**: None. Referenced only in docs.
- **Action needed**: Ensure the extension calls BLT's public REST API (`/api/`) rather than any internal endpoints.
- **Copilot prompt**:
  > "Review the BLT REST API at `website/api/views.py` and document the endpoints that the browser extension requires (bug submission, domain lookup, user auth). Create an `API_CONTRACTS.md` listing each endpoint, its request/response schema, and authentication method."

---

#### 2. BLT GitHub Action → `blt-github-action`
- **Status**: ✅ Already a standalone tool — no views, models, or templates in this repo.
- **Files in BLT core**: None. Referenced only in documentation and `.github/` workflows.
- **Action needed**: Verify the action only calls BLT's public API; pin the API version it targets.
- **Copilot prompt**:
  > "Scan `.github/` workflows and any `blt-action` references in this repo. Identify any BLT internal endpoints used. Add those endpoints to the public REST API (`website/api/views.py`) with versioning so the action can be independently maintained."

---

#### 3. Video Call → External Service
- **Status**: ✅ Already a stub — 6-line view, no models, no DB queries.
- **Files**:
  - `website/views/video_call.py` (6 lines, renders `video_call.html`)
  - `website/templates/video_call.html`
- **Action needed**: Replace the stub with an iframe or SDK embed from an external provider (Jitsi/Daily.co/Zoom).
- **Copilot prompt**:
  > "Update `website/views/video_call.py` and `website/templates/video_call.html` to embed a Jitsi Meet session using an environment-variable-configured Jitsi server URL. The room name should be derived from the user session. Remove any placeholder template markup and replace with a working Jitsi iframe integration."

---

### 🔵 Phase 2 — Quick Migrations (Low Risk, 1–2 Sprints Each)

#### 4. Slackbot & Slack Integration → `blt-slack-integration`
- **Status**: 🔵 Quick Migration — logic is mostly isolated in two view files; the main blocker is direct ORM access to core models.
- **Files**:
  - `website/views/slackbot.py` — Bot initialisation, `/discover` command, DM helpers
  - `website/views/slack_handlers.py` (~2,700 lines) — Event handlers, team-join flow, GSOC/chapter/events commands
  - `website/templates/slack.html` — Landing page
  - `website/templates/slack_channels.html`
  - `website/models.py`: `SlackIntegration` (105–128), `SlackChannel` (129–174), `SlackBotActivity` (2016–2044)
- **Core model dependencies**: `Domain`, `Hunt`, `Issue`, `Project`, `SlackBotActivity`, `SlackIntegration`, `User`
- **Extraction steps**:
  1. Add REST API endpoints in `website/api/views.py` for `Domain`, `Hunt`, `Issue`, `Project` lookups the bot currently queries directly.
  2. Replace ORM calls in `slack_handlers.py` with `requests` calls to those endpoints.
  3. Move bot files to a new standalone Django app or plain Python package.
  4. Keep `SlackIntegration` / `SlackChannel` models in BLT core (they configure the org's connection) and expose them via a dedicated API.
- **Copilot prompt**:
  > "In `website/views/slack_handlers.py`, identify every `from website.models import` usage and every Django ORM query. For each, create or extend an existing DRF ViewSet in `website/api/views.py` to expose that data as a REST endpoint. Then replace the ORM calls in `slack_handlers.py` with `requests.get`/`requests.post` calls to the new endpoints, using a `BLT_API_BASE_URL` environment variable. Wrap API calls in a helper that handles auth via a service token stored in `SLACK_BLT_API_TOKEN`."

---

#### 5. Open Source Sorting Hat (OSSH) → `ossh-service`
- **Status**: 🔵 Quick Migration — almost entirely self-contained; only depends on `Repo` from core.
- **Files**:
  - `website/views/ossh.py` (~530 lines) — Recommendation engine: tag-based, language-based repo/community/article recommender
  - `website/templates/ossh/home.html`
  - `website/templates/ossh/results.html`
  - `website/templates/ossh/includes/github_stats.html`
  - `website/templates/ossh/includes/recommended_repos.html`
  - `website/templates/ossh/includes/recommended_communities.html`
  - `website/templates/ossh/includes/recommended_discussion_channels.html`
  - `website/templates/ossh/includes/recommended_articles.html`
  - `website/models.py`: `OsshCommunity` (2497–2518), `OsshDiscussionChannel` (2519–2534), `OsshArticle` (2535–2555); `Repo` (1910–1990)
  - `website/views/constants.py` — `COMMON_TECHNOLOGIES`, `COMMON_TOPICS`, `PROGRAMMING_LANGUAGES`, `TAG_NORMALIZATION`
- **Core model dependencies**: `Repo`, `Tag` (for filtering repos by tags/language)
- **Extraction steps**:
  1. Expose `Repo` data via BLT's public API (already partially done via `RepoListView`).
  2. Move `OsshCommunity`, `OsshDiscussionChannel`, `OsshArticle` models and views to a new `ossh` Django app or standalone service.
  3. Replace `Repo.objects.filter(...)` with an API call to BLT.
- **Copilot prompt**:
  > "Extract the OSSH recommendation engine from `website/views/ossh.py` into a new standalone Django app called `ossh` at the project root. Move the three OSSH models (`OsshCommunity`, `OsshDiscussionChannel`, `OsshArticle`) from `website/models.py` into `ossh/models.py`. Replace the direct `Repo.objects.filter(...)` query in `repo_recommender()` with a call to the BLT REST API endpoint `/api/v1/repos/?tags=...&language=...`. Create migrations for the new app and update `blt/settings.py` and `blt/urls.py` accordingly."

---

#### 6. Education Platform → `blt-academy`
- **Status**: 🟡 Mostly Done — fully contained view file and template directory; depends on `UserProfile` for enrollment.
- **Files**:
  - `website/views/education.py` (~580 lines)
  - `website/templates/education/education.html`
  - `website/templates/education/instructor_dashboard.html`
  - `website/templates/education/view_course.html`
  - `website/templates/education/study_course.html`
  - `website/templates/education/view_lecture.html`
  - `website/templates/education/content_management.html`
  - `website/templates/education/create_standalone_lecture.html`
  - `website/templates/education/edit_standalone_lecture.html`
  - `website/templates/education/dashboard_edit_course.html`
  - `website/templates/education/includes/` (partial templates)
  - `website/models.py`: `Course` (2575–2589), `Section` (2590–2609), `Lecture` (2610–2706), `LectureStatus` (2707–2719), `Enrollment` (2720–2748), `Rating` (2749–2761)
  - `website/decorators.py` — `instructor_required` decorator
- **Core model dependencies**: `UserProfile`, `Tag`
- **Extraction steps**:
  1. Create a `blt-academy` Django project with its own auth (OAuth2 against BLT).
  2. Move the six LMS models to the new project.
  3. Replace `UserProfile` lookups with JWT-authenticated user identity.
  4. Migrate existing enrollment data via a data migration script.
- **Copilot prompt**:
  > "Create a new Django app called `education` inside the BLT project to isolate the education platform as a preparation step for extraction. Move `Course`, `Section`, `Lecture`, `LectureStatus`, `Enrollment`, and `Rating` models from `website/models.py` into `education/models.py`. Move all views from `website/views/education.py` into `education/views.py`. Move all templates from `website/templates/education/` into `education/templates/education/`. Add the `instructor_required` decorator to `education/decorators.py`. Update `blt/settings.py` INSTALLED_APPS, `blt/urls.py`, and all imports. Create and run Django migrations. Ensure all existing tests still pass."

---

#### 7. Security Labs / Simulation → `blt-security-labs`
- **Status**: 🟡 Mostly Done — self-contained; isolated models with no core entanglements beyond `request.user`.
- **Files**:
  - `website/views/Simulation.py`
  - `website/templates/Simulation.html`
  - `website/templates/lab_detail.html`
  - `website/templates/task_detail.html`
  - `website/models.py`: `Labs` (3141–3168), `Tasks` (3169–3192), `TaskContent` (3193–3211), `UserTaskProgress` (3212–3235), `UserLabProgress` (3236–3280)
- **Core model dependencies**: `request.user` (Django auth only)
- **Extraction steps**:
  1. Move five models and the view file to a new `simulation` Django app.
  2. Use Django's built-in `auth.User` — no `UserProfile` coupling.
  3. The sandbox/execution environment for CTF-style labs still needs isolated container infrastructure (Docker-in-Docker or Kubernetes jobs).
- **Copilot prompt**:
  > "Create a new Django app called `simulation` inside the BLT project to isolate the Security Labs feature. Move `Labs`, `Tasks`, `TaskContent`, `UserTaskProgress`, and `UserLabProgress` models from `website/models.py` into `simulation/models.py`. Move all views from `website/views/Simulation.py` into `simulation/views.py`. Move `Simulation.html`, `lab_detail.html`, and `task_detail.html` into `simulation/templates/`. Update `blt/settings.py` INSTALLED_APPS, `blt/urls.py`, and all imports. Create Django migrations for the new app."

---

### 🔴 Phase 3 — Complex Migrations (High Risk, Multiple Sprints)

#### 8. BACON Token System → `blt-bacon-service`
- **Status**: 🔴 Complex — blockchain infrastructure, wallet security, Slack integration, mentor-role checks.
- **Files**:
  - `website/views/bitcoin.py` (~480 lines) — Token submission, batch send, transaction initiation, wallet balance
  - `website/bitcoin_utils.py` — Bitcoin RPC client, `create_bacon_token()` helper
  - `BACON/` directory — Ordinal server configs, setup scripts, regtest/mainnet configs
  - `website/templates/bacon.html`
  - `website/templates/bacon_requests.html`
  - `website/templates/bacon_transaction.html`
  - `website/models.py`: `BaconToken` (1503–1513), `BaconEarning` (2338–2346), `BaconSubmission` (2762–2782)
- **Core model dependencies**: `Badge`, `UserBadge`, `Organization`, `SlackIntegration`, `UserProfile`
- **Blockers**:
  - Mentor badge check (`Badge`/`UserBadge`) must be replaced with a role API or JWT claim.
  - Slack notification is coupled to `Organization.SlackIntegration` — needs Slack service extraction first.
  - ORD server URL and Bitcoin RPC credentials need secure service-to-service auth.
- **Copilot prompt**:
  > "In `website/views/bitcoin.py`, replace every `Badge.objects.filter()`/`UserBadge.objects.filter()` mentor-check with a call to a new internal API endpoint `GET /api/v1/users/{username}/roles/` that returns the user's badge/role list. Add that endpoint to `website/api/views.py`. Document the change in `API_CONTRACTS.md`. Do not change the BACON blockchain logic itself."

---

#### 9. Staking System → `blt-staking` (or part of `blt-bacon-service`)
- **Status**: 🔴 Complex — tightly coupled with BACON earning model; DeFi logic with atomic transactions.
- **Files**:
  - `website/views/staking_competitive.py` (~458 lines)
  - `website/templates/staking/staking_home.html`
  - `website/templates/staking/pool_detail.html`
  - `website/templates/staking/my_staking.html`
  - `website/templates/staking/create_pool.html`
  - `website/templates/staking/leaderboard.html`
  - `website/models.py`: `StakingPool` (3349–3526), `StakingEntry` (3527–3577), `StakingTransaction` (3578–3602), `Challenge` (2045–2069)
- **Core model dependencies**: `BaconEarning`, `Challenge`, `Issue`, `IpReport`, `TimeLog`
- **Copilot prompt**:
  > "In `website/views/staking_competitive.py`, identify every reference to `BaconEarning`, `Challenge`, `Issue`, `IpReport`, and `TimeLog`. For each, note whether it reads or writes data. Create a list in a comment block at the top of the file documenting the exact API shape needed (fields, filters) to replace each ORM call with an HTTP request. Do not change the logic yet — this is an API contract discovery step."

---

#### 10. Hackathons → `blt-hackathons`
- **Status**: 🔴 Complex — depends on many core models including `Organization`, `Repo`, `GitHubIssue`, `Contributor`.
- **Files**:
  - `website/views/hackathon.py` (~800 lines)
  - `website/templates/hackathons/list.html`
  - `website/templates/hackathons/detail.html`
  - `website/templates/hackathons/form.html`
  - `website/templates/hackathons/prize_form.html`
  - `website/templates/hackathons/sponsor_form.html`
  - `website/forms.py`: `HackathonForm`, `HackathonPrizeForm`, `HackathonSponsorForm`
  - `website/models.py`: `Hackathon` (2798–3022), `HackathonSponsor` (3023–3048), `HackathonPrize` (3049–3073)
- **Core model dependencies**: `IP`, `Contributor`, `GitHubIssue`, `Hackathon`, `HackathonPrize`, `HackathonSponsor`, `Organization`, `Repo`, `Tag`, `UserProfile`
- **Copilot prompt**:
  > "In `website/views/hackathon.py`, replace every `GitHubIssue.objects` query with a call to the existing `/api/v1/github-issues/` endpoint (check `website/api/views.py` for the current implementation). Add any missing filter parameters to the API endpoint. Document the before/after in a comment at the top of `hackathon.py`. This reduces one core dependency and is a first step toward extraction."

---

#### 11. Messaging / Chat / Discussion Rooms → `blt-messaging-service`
- **Status**: 🔴 Complex — uses Django Channels (WebSocket), needs persistent connection infrastructure separate from HTTP.
- **Files**:
  - `website/consumers.py` — WebSocket consumers (Django Channels)
  - `website/templates/messaging.html`
  - `website/templates/room_form.html`
  - `website/templates/rooms_list.html`
  - `website/templates/join_room.html`
  - `website/models.py`: `Room` (2070–2096), `Thread` (3116–3123), `Message` (3124–3140)
  - `blt/routing.py` — Django Channels routing
- **Core model dependencies**: `UserProfile`
- **Copilot prompt**:
  > "Create a new Django app called `messaging` inside the BLT project as a preparation step for extraction. Move `Room`, `Thread`, and `Message` models from `website/models.py` into `messaging/models.py`. Move `website/consumers.py` into `messaging/consumers.py`. Update `blt/routing.py`, `blt/settings.py`, and `blt/urls.py`. Create Django migrations. Ensure the WebSocket URL `/ws/chat/<room_name>/` continues to work."

---

#### 12. Jobs Board → `blt-jobs`
- **Status**: 🔴 Complex (medium effort) — Job views are embedded in `company.py`; need extraction before repo split.
- **Files**:
  - `website/views/company.py` (Job-related functions near lines 2754–2945: `create_job`, `edit_job`, `delete_job`, `toggle_job_status`)
  - `website/models.py`: `Job` (299–385)
  - `website/api/views.py`: `JobViewSet`, `OrganizationJobStatsViewSet`
- **Core model dependencies**: `Organization`, `UserProfile`
- **Copilot prompt**:
  > "Extract all job-related view functions (`create_job`, `edit_job`, `delete_job`, `toggle_job_status`) from `website/views/company.py` into a new file `website/views/jobs.py`. Update imports in `blt/urls.py` to use the new file. Do not change function signatures or logic — this is a pure file extraction to prepare for later service separation."

---

#### 13. Trademark Search → `blt-trademark-service`
- **Status**: 🟡 Mostly Done — self-contained API + templates; depends on USPTO external calls.
- **Files**:
  - `website/api/views.py`: `trademark_search_api` function
  - `website/templates/trademark_search.html`
  - `website/templates/trademark_detailview.html`
  - `website/models.py`: `TrademarkOwner` (487–503), `Trademark` (504–539)
- **Core model dependencies**: None (external USPTO API calls)
- **Copilot prompt**:
  > "Move the `trademark_search_api` view, `Trademark`, and `TrademarkOwner` models, and their two templates into a new Django app called `trademarks`. Update `blt/settings.py` INSTALLED_APPS, `blt/urls.py`, and all imports. Create Django migrations for the new app. This is a self-contained extraction with no core model dependencies."

---

### Summary Table

| Component | Status | Effort | View File | Template Dir | Key Models |
|---|---|---|---|---|---|
| Browser Extension | ✅ Already Separate | — | — | — | — |
| GitHub Action | ✅ Already Separate | — | — | — | — |
| Video Call | ✅ Stub Only | Hours | `views/video_call.py` | `video_call.html` | None |
| Slackbot | 🔵 Quick | 1–2 sprints | `views/slackbot.py`, `views/slack_handlers.py` | `slack.html` | SlackIntegration, SlackChannel |
| OSSH | 🔵 Quick | 1 sprint | `views/ossh.py` | `ossh/` | OsshCommunity, OsshArticle, Repo |
| Education | 🟡 Mostly Done | 1–2 sprints | `views/education.py` | `education/` | Course, Section, Lecture, Enrollment |
| Security Labs | 🟡 Mostly Done | 1 sprint | `views/Simulation.py` | `Simulation.html`, `lab_detail.html` | Labs, Tasks, UserLabProgress |
| Trademark Search | 🟡 Mostly Done | 1 sprint | `api/views.py` (partial) | `trademark_*.html` | Trademark, TrademarkOwner |
| Jobs Board | 🔴 Complex | 2–3 sprints | `views/company.py` (embedded) | *(within company templates)* | Job, Organization |
| Hackathons | 🔴 Complex | 3–4 sprints | `views/hackathon.py` | `hackathons/` | Hackathon, GitHubIssue, Org, Repo |
| Messaging | 🔴 Complex | 3–4 sprints | `consumers.py` | `messaging.html`, `rooms_list.html` | Room, Thread, Message |
| BACON Token | 🔴 Complex | 4+ sprints | `views/bitcoin.py` | `bacon*.html` | BaconToken, BaconEarning, BaconSubmission |
| Staking | 🔴 Complex | 4+ sprints | `views/staking_competitive.py` | `staking/` | StakingPool, StakingEntry |

---

## Components Recommended for Separation into Independent Repositories

The following components should be extracted from the monolithic BLT application into separate repositories to improve maintainability, scalability, and development velocity:

### Client Applications (Different Tech Stack)
- **BLT Flutter/Mobile App** → `blt-mobile`
  - **Why**: Different tech stack (Flutter/Dart), independent release cycle, mobile-specific concerns (app stores, permissions, offline functionality)
- **BLT Extension/Chrome Extension** → `blt-browser-extension`
  - **Why**: Browser extension architecture differs significantly from web apps; separate build process, different security model, extension store distribution
- **iPhone App** → Could merge with `blt-mobile` or be standalone `blt-ios`
  - **Why**: Native iOS if not using Flutter; separate App Store deployment

### DevOps Tools & Integrations
- **BLT Action** → `blt-github-action`
  - **Why**: GitHub Actions have specific packaging/deployment requirements; independent versioning; used by external projects
- **Slackbot & Slack Integration** → `blt-slack-integration`
  - **Why**: Separate deployment model (Slack App Store); can scale independently; OAuth flows; webhook handling

### Blockchain & Token Management
- **BACON Token System** → `blt-bacon-service`
  - **Why**: Blockchain interactions require specialized infrastructure; security isolation for wallet/transaction handling; different scaling requirements; potential regulatory concerns
- **Staking System** → Part of `blt-bacon-service` or `blt-staking`
  - **Why**: DeFi operations; smart contract interactions; needs separate security audit; high-value transaction handling

### Standalone Platforms
- **Education Platform** → `blt-academy` or `blt-learn`
  - **Why**: Full Learning Management System (LMS) with courses, lectures, enrollment; could serve broader community; different user base (students vs bug hunters)
- **Security Labs/Simulation** → `blt-security-labs`
  - **Why**: CTF-style challenges with vulnerable environments; requires isolated sandbox infrastructure; CPU/memory intensive; needs container orchestration
- **Hackathons** → `blt-hackathons` or integrate with existing event platforms
  - **Why**: Event management system with sponsors, prizes, registration; seasonal/sporadic usage; different access patterns
- **Jobs Board** → `blt-jobs` or integrate with external job platforms
  - **Why**: Job posting/application workflow; different user flows; could be monetized separately; integrations with job boards (LinkedIn, Indeed)
- **Open Source Sorting Hat (OSSH)** → `ossh-recommender` or `ossh-service`
  - **Why**: Recommendation engine with ML/algorithm complexity; can serve multiple platforms; separate data pipeline; GitHub API intensive

### Real-Time Communication Services
- **Video Call** → External service integration (Jitsi, Daily.co, Zoom SDK)
  - **Why**: WebRTC infrastructure is complex and expensive; specialized scaling needs; better served by dedicated providers
- **Direct Messaging/Chat** → `blt-messaging-service` or use external (Matrix, Rocket.Chat)
  - **Why**: Real-time WebSocket connections need separate scaling; encryption complexity; message storage/retention policies
- **Discussion Rooms** → Part of messaging service or use external chat platform
  - **Why**: Real-time chat rooms require persistent connections; different infrastructure than request-response

### Utility Services
- **BLT Lettuce** → Clarify scope, then separate if it's a distinct tool
  - **Why**: Unknown scope—if it's a separate utility, should be in own repo
- **Trademark Search** → External API integration or `blt-trademark-service`
  - **Why**: Integrates with USPTO/trademark databases; rate-limited external APIs; caching strategy differs from core app

### Analytics & Reporting (Optional Separation)
- **Stats Dashboard/Analytics** → Consider `blt-analytics-service`
  - **Why**: Heavy data aggregation; can use separate OLAP database; caching strategies; doesn't need production database access
- **Contributor Stats & GitHub Analytics** → Part of analytics service
  - **Why**: GitHub API rate limits; background job processing; time-series data

### Keep in Core BLT Application
The following remain in the core monolith as they are essential to the bug bounty workflow:
- Organizations, Domains, Projects, Repositories (Core entities)
- Bugs/Issues (Core feature)
- Bounties (Core feature)
- Users & Authentication (Core feature)
- Teams (Core collaboration)
- Feed/Activity Stream (Core engagement)
- Leaderboard/Scoreboard (Core gamification directly tied to issues)
- API (Core integration point)
- Messaging/Notifications (Core communication—unless extracted to microservice)
- Time Logs/Sizzle (Core productivity tracking)

---

## Component Vitality Assessment

Note: Duplicates from the request are consolidated into single entries.

| Component | Summary | Vitality |
|---|---|---|
| Map | Visual discovery of organizations/projects/bugs on a map. | Optional |
| Hackathons | Event-specific participation and tracking. | Optional |
| Jobs | Job board for security/engineering roles. | Optional |
| Reported IPs | IP reporting/abuse tracking. | Optional |
| Trademarks | Trademark search utility. | Optional |
| Bid on Issues | Marketplace-style bidding for fixing issues. | Optional |
| Funding | Funding info or requests for projects. | Optional |
| GSOC PR Reports | Reporting and tracking for GSoC pull requests. | Optional |
| Staking | Stake-based challenges/rewards. | Optional |
| Reminder Settings | User notification preferences. | Optional |
| Education | Educational content and learning paths. | Optional |
| Security Labs | Practice labs or exercises. | Optional |
| Open Source Sorting Hat | Discovery/matching tool for open source work. | Optional |
| BLT Flutter | Mobile app (Flutter). | Optional |
| BLT Extension | Browser extension. | Optional |
| BLT Action | GitHub Action integration. | Optional |
| BLT Lettuce | Additional BLT tool/subproject (unclear scope). | Optional |
| Video Call | Real-time video collaboration. | Optional |
| Apps | Catalog of supported apps. | Optional |
| iPhone App | iOS client. | Optional |
| Chrome Extension | Browser extension client. | Optional |
| Organizations | Entity representing a company or group participating in BLT; used to scope projects, domains, and issues. | Core |
| Register Organization | Onboarding flow to create an organization profile and ownership. | Core |
| Domains | Domain inventory tied to organizations for targeting and reporting. | Core |
| Bugs | Individual bug reports with details and status. | Core |
| Issues | Tracking and workflow for reported bugs. | Core |
| Projects | Work units owned by organizations (apps, sites, repos). | Core |
| Repositories | Git repository entities linked to projects. | Core |
| Users | User accounts, profiles, and permissions. | Core |
| BLT Core | Main web platform and backend. | Core |
| Feed | Activity stream of recent bugs, issues, or updates. | Important |
| Bounties | Rewards attached to issues/bugs. | Important |
| Messaging | Direct messaging and communication between users. | Important |
| Teams | Grouping of users for collaboration and access control. | Important |
| Developer API | API docs and programmatic access. | Important |
| SimilarityScan | Duplicate/related issue detection. | Important |
| Time Logs | Time tracking (Sizzle) for work sessions. | Supporting |
| Check-In | Daily/periodic check-in for streaks or activity. | Supporting |
| Scoreboard | Aggregate points and rankings view. | Supporting |
| BACON (coin) | Token/reward system for participation. | Supporting |
| Bacon Requests | Requests or redemption flow for BACON rewards. | Supporting |
| Challenges | Gamified tasks and goals. | Supporting |
| Leaderboard | Ranked contributors list. | Supporting |
| Takedowns | Reporting/removal requests for content. | Supporting |
| Badges | Achievement system tied to activity. | Supporting |
| Adventures | Guided learning or task flows. | Supporting |
| Contribute | Guidance for contributors. | Supporting |
| Documentation | Product and developer documentation. | Supporting |
| Submit PR for review | Workflow entry for code review. | Supporting |
| Create an Issue | Entry point to report issues (often GitHub). | Supporting |
| GitHub | Integration and links to source control. | Supporting |
| BLT BACON | Token/rewards product surface. | Supporting |
| Communication | General comms hub or page. | Supporting |
| Rooms | Chat rooms for group communication. | Supporting |
| Banned Apps | Moderation list of disallowed apps. | Supporting |
| Slack | Community chat link/integration. | Supporting |
| Sitemap | Site navigation index for SEO. | Supporting |
| Status | System status page. | Supporting |
| Stats | High-level metrics. | Supporting |
| Stats Dashboard | Detailed analytics view. | Supporting |
| Template List | Templates for issues/projects or content. | Supporting |
| Website Stats | Web traffic and usage metrics. | Supporting |
| Legal | Legal notices and compliance pages. | Supporting |
| Terms | Terms of service. | Supporting |
| Language | Localization selector. | Supporting |
| English | Default locale option. | Supporting |
| Contributors | Public list of project contributors. | Informational |
| About Us | Project overview and mission. | Informational |
| Features | Marketing/overview of platform capabilities. | Informational |
| Sponsorships | Sponsorship and partner information. | Informational |
| OWASP Project | OWASP affiliation information. | Informational |
| Donations | Donation page and links. | Informational |
| GSOC | Google Summer of Code info and workflows. | Informational |
| Roadmap | Planned features and timeline. | Informational |
| Social Links | Links to social media and community. | Informational |
| Twitter | Social channel link. | Informational |
| Facebook | Social channel link. | Informational |
| Blog | News and updates. | Informational |
| Site Info | Site metadata and info page. | Informational |
| Resources | Resource links and references. | Informational |
| Design | Design resources or guidelines. | Informational |
| Style Guide | UI/brand usage rules. | Informational |
| Edit this page | Link to edit docs/content. | Informational |

---

## Migration Strategy & Priorities

### Phase 1: Quick Wins (Low Risk, High Value)
**Priority: Immediate**
1. **BLT Extension** - Already separate codebase in reality; just needs proper repo split
2. **BLT GitHub Action** - Standalone tool; no database dependencies
3. **Slackbot** - Can operate via webhooks/API; minimal core dependencies

**Benefits**: Reduces main repo complexity, allows dedicated teams, clearer ownership

### Phase 2: Platform Extractions (Medium Risk, High Value)
**Priority: Next 6-12 months**
1. **BLT Mobile App** - Communicates via API only; natural separation point
2. **Education Platform** - Self-contained LMS with own data model
3. **Security Labs** - Requires isolated infrastructure anyway for security

**Benefits**: Each platform can evolve independently, different tech stacks possible

### Phase 3: Backend Service Decomposition (Higher Risk, Strategic Value)
**Priority: 12-24 months**
1. **BACON Token Service** - Extract blockchain/wallet logic behind API
2. **OSSH Recommendation Engine** - ML/algorithm service with own data pipeline
3. **Messaging Service** - Real-time WebSocket service (or adopt external solution)

**Benefits**: Microservices architecture, independent scaling, technology flexibility

### Phase 4: Evaluate & Optimize (Optional)
**Priority: As needed**
1. **Hackathons** - Consider if usage justifies dedicated platform or external integration
2. **Jobs Board** - Evaluate against competitors; might be better to integrate with LinkedIn/Indeed
3. **Analytics/Stats** - If data warehouse needs emerge, extract to dedicated service

### Migration Considerations

**Before Extracting Any Component:**
- ✅ Document all API contracts and dependencies
- ✅ Ensure comprehensive test coverage
- ✅ Create feature flags to maintain backward compatibility
- ✅ Set up separate CI/CD pipelines
- ✅ Plan data migration strategy (if applicable)
- ✅ Define ownership and maintenance responsibility

**Authentication/Authorization:**
- Implement OAuth2/JWT for service-to-service communication
- Consider centralized identity provider (e.g., Keycloak) or keep auth in core

**Data Strategy:**
- Each service should own its data (database per service pattern)
- Use events/webhooks for cross-service communication
- Consider API Gateway pattern for unified external API

**Deployment:**
- Containerize all services (Docker)
- Use Kubernetes or similar for orchestration
- Implement proper monitoring and observability
- Ensure graceful degradation when optional services are down

### Anti-Patterns to Avoid
- ❌ Don't create distributed monoliths (services that are too tightly coupled)
- ❌ Don't extract too early (wait for clear boundaries and stability)
- ❌ Don't skip the API layer (avoids shared database anti-pattern)
- ❌ Don't ignore operational complexity (more services = more overhead)

### Success Metrics
- Developer velocity increases (parallel development possible)
- Deployment frequency increases (independent releases)
- Codebase maintainability improves (smaller, focused repos)
- Service reliability maintained or improved (isolated failures)
- Onboarding time for new developers decreases (smaller scope to understand)
