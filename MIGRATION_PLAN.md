# BLT Components Summary and Vitality

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
