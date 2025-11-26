# Components We Should Remove from BLT

## Overview
This document identifies components and features in the OWASP BLT project that should be removed or moved to separate repositories. The goal is to focus the main BLT repository on its core mission: **bug bounties, vulnerability reporting, issue reporting, and crowdsourced QA**.

## Core Mission (Keep)
The following features align with BLT's core mission and should remain:
- ✅ Bug/Issue reporting and tracking (`Issue`, `IssueScreenshot`)
- ✅ Bug hunts and bounties (`Hunt`, `HuntPrize`, `Winner`)
- ✅ Domain and organization management (`Domain`, `Organization`, `OrganizationAdmin`)
- ✅ User profiles and authentication (`UserProfile`, `User`)
- ✅ Points and leaderboards for bug reporting (`Points`, `Winner`)
- ✅ Basic badges for bug hunting achievements (`Badge`, `UserBadge`)
- ✅ API endpoints for issue reporting
- ✅ Integration with security tools (GitHub, Slack for bug notifications)

---

## Components to Remove/Extract

### 1. 🪙 Cryptocurrency & Blockchain Features
**Rationale:** These features add significant complexity unrelated to bug reporting and vulnerability management. They should be extracted into a separate "BLT-Blockchain" or "BLT-Rewards" repository.

**Components:**
- **Models:**
  - `Wallet` - User cryptocurrency wallets
  - `Transaction` - Financial transactions
  - `Payment` - Payment processing
  - `BaconToken` - Bitcoin Runes token system
  - `BaconSubmission` - Token submission system
  - `BaconEarning` - Token earnings tracking
  - Cryptocurrency address validators (`validate_btc_address`, `validate_bch_address`)
  
- **Views/Features:**
  - `website/views/bitcoin.py` - All Bitcoin/BACON token operations
  - `website/bitcoin_utils.py` - Bitcoin RPC utilities
  - Bitcoin transaction processing
  - Wallet balance management
  - Token distribution system
  
- **Directory:**
  - `BACON/` - Entire Bitcoin Runes infrastructure including:
    - Regtest and mainnet configurations
    - Ord server setup scripts
    - Bitcoin node configurations
    - BACON token etching documentation

- **Database Fields:**
  - `UserProfile.btc_address`
  - `UserProfile.bch_address`
  - `UserProfile.eth_address`
  - `Hunt.prize_in_crypto`
  - `Payment.amount_bch`
  - `Payment.bch_address`
  - `Payment.p2p_amount_bch`
  - `Payment.bch_tx_id`

### 2. 🎯 Staking & Competitive Gaming
**Rationale:** Staking pools and competitive gaming features are not related to bug reporting. These gamification elements add complexity without serving the core mission.

**Components:**
- **Models:**
  - `StakingPool` - Staking pool management
  - `StakingEntry` - User staking entries
  - `StakingTransaction` - Staking transaction tracking
  - `Bid` - Bidding system
  - `Monitor` - Monitoring features
  
- **Views/Features:**
  - `website/views/staking_competitive.py` - All staking and competitive features
  - Staking pool creation and management
  - Competitive staking mechanics

- **Templates:**
  - `website/templates/staking/` - All staking-related templates

### 3. 🎓 Education Platform
**Rationale:** While educational content about security is valuable, a full-fledged course platform with enrollments, lectures, and ratings should be a separate project (e.g., "BLT-Academy").

**Components:**
- **Models:**
  - `Course` - Course management
  - `Section` - Course sections
  - `Lecture` - Individual lectures
  - `LectureStatus` - Lecture completion tracking
  - `Enrollment` - Course enrollments
  - `Rating` - Course ratings
  
- **Views/Features:**
  - `website/views/education.py` - All education platform features
  - Course creation and management
  - Enrollment system
  - Lecture video/live streaming
  - Course ratings and reviews
  
- **Templates:**
  - `website/templates/education/` - All education templates

### 4. 🧪 Security Labs & Simulations
**Rationale:** Interactive security labs and simulations are valuable for learning but not core to bug reporting. This should be a standalone "BLT-Labs" or "BLT-Training" project.

**Components:**
- **Models:**
  - `Labs` - Security lab exercises
  - `Tasks` - Lab tasks/challenges
  - `TaskContent` - Task content and instructions
  - `UserTaskProgress` - User progress in tasks
  - `UserLabProgress` - User progress in labs
  
- **Views/Features:**
  - `website/views/Simulation.py` - Lab simulation dashboard
  - Lab task completion tracking
  - Progress calculation
  - XSS, CSRF, Command Injection simulations

### 5. 🗺️ Adventure/Quest System
**Rationale:** Adventure-based gamification (quests, tasks, progress tracking) is a game mechanic unrelated to bug bounty workflows.

**Components:**
- **Models:**
  - `Adventure` - Adventure/quest definitions
  - `AdventureTask` - Tasks within adventures
  - `UserAdventureProgress` - User adventure progress
  - `UserTaskSubmission` - Task submission tracking
  
- **Views/Features:**
  - `website/views/adventure.py` - Adventure system
  - Adventure listing and filtering
  - Task submission and completion
  - Progress tracking
  
- **Templates:**
  - `website/templates/adventures/` - Adventure templates

### 6. 📝 Forum & Discussion Platform
**Rationale:** General discussion forums are not specific to bug reporting. Consider using existing platforms (Discourse, Slack) for community discussions.

**Components:**
- **Models:**
  - `ForumCategory` - Forum categories
  - `ForumPost` - Forum posts
  - `ForumVote` - Post voting
  - `ForumComment` - Forum comments
  
- **Features:**
  - Forum post creation and management
  - Voting and comment systems
  - Category organization

### 7. 📰 Blog Platform
**Rationale:** A full blog system is not core to bug reporting. Use external blogging platforms or a separate content management system.

**Components:**
- **Models:**
  - `Post` - Blog posts
  
- **Views/Features:**
  - `website/views/blog.py` - Blog management
  - Post creation, editing, deletion
  - Blog post listing
  
- **Templates:**
  - `website/templates/blog/` - Blog templates

### 8. 🏆 Hackathon Management
**Rationale:** While hackathons can involve security, the full hackathon management system (sponsors, prizes, participants) is better suited as a separate "BLT-Events" repository.

**Components:**
- **Models:**
  - `Hackathon` - Hackathon events
  - `HackathonSponsor` - Sponsor management
  - `HackathonPrize` - Prize tracking
  
- **Views/Features:**
  - `website/views/hackathon.py` - Hackathon management
  - Hackathon creation and listing
  - Sponsor management
  - Prize distribution
  
- **Templates:**
  - `website/templates/hackathons/` - Hackathon templates

### 9. 🎮 Challenge & Room System
**Rationale:** Challenge rooms and CTF-style challenges are gaming features that should be in a separate training/education platform.

**Components:**
- **Models:**
  - `Challenge` - CTF-style challenges
  - `Room` - Challenge rooms
  
- **Features:**
  - Challenge creation and management
  - Room-based competitions

### 10. 💼 Job Board
**Rationale:** A job board for security positions is valuable but not core to bug reporting. This could be a separate "BLT-Jobs" microservice or use existing job platforms.

**Components:**
- **Models:**
  - `Job` - Job postings
  
- **Views/Features:**
  - Job creation and management in `website/views/company.py`
  - Job listing and filtering
  - Application tracking
  
- **Templates:**
  - `website/templates/jobs/` - Job board templates

### 11. 🤖 ChatBot & AI Features
**Rationale:** ChatBot logging is ancillary to core bug reporting functionality.

**Components:**
- **Models:**
  - `ChatBotLog` - ChatBot interaction logging
  - `bot.py` - Bot functionality

### 12. 📹 Video Call Feature
**Rationale:** Video calling is not related to bug reporting. Use existing video platforms (Zoom, Google Meet, etc.).

**Components:**
- **Views/Features:**
  - `website/views/video_call.py` - Video call interface
  
- **Templates:**
  - Video call templates

### 13. 📊 OSSH (Open Source Software Hunt) Features
**Rationale:** While interesting for open source project discovery, this is tangential to bug reporting and could be a separate tool.

**Components:**
- **Models:**
  - `OsshCommunity` - Community data
  - `OsshDiscussionChannel` - Discussion channels
  - `OsshArticle` - Articles
  
- **Views/Features:**
  - `website/views/ossh.py` - OSSH functionality
  - GitHub data analysis
  - Community matching
  
- **Templates:**
  - `website/templates/ossh/` - OSSH templates

### 14. 📮 Queue/Messaging System
**Rationale:** If this is a general messaging/queue system (not for bug notifications), it may be unnecessary with modern messaging platforms.

**Components:**
- **Models:**
  - `Queue` - Queue management
  - `Thread` - Message threads
  - `Message` - Individual messages
  
- **Views/Features:**
  - `website/views/queue.py` - Queue management
  
- **Templates:**
  - `website/templates/queue/` - Queue templates

### 15. 🔍 Trademark Monitoring
**Rationale:** Trademark monitoring is not related to vulnerability reporting. This is better suited as a compliance or legal tool.

**Components:**
- **Models:**
  - `TrademarkOwner` - Trademark ownership tracking
  - `Trademark` - Trademark data
  
- **Features:**
  - Trademark search API
  - Trademark monitoring for organizations

### 16. 📱 Banned Apps Database
**Rationale:** While potentially useful, a database of banned apps is not core to bug bounty functionality.

**Components:**
- **Files:**
  - `banned_apps.json` - Database of banned applications
  
- **Views/Features:**
  - `website/views/banned_apps.py` - Banned apps search
  
- **Templates:**
  - Banned apps search interface

### 17. 👥 Social Features (Non-Essential)
**Rationale:** Some social features go beyond what's needed for bug reporting collaboration.

**Components to Review:**
- `UserProfile.follows` - User following system (if not used for bug notifications)
- `Kudos` - Kudos system (may be redundant with points/badges)
- `InviteFriend` - Friend invitation system (marketing feature)
- `InviteOrganization` - Organization invitation with referral codes

---

## Extraction Strategy

### Phase 1: High Priority Removals
1. **BACON/Cryptocurrency Infrastructure** - Most complex, least related to core mission
2. **Staking System** - Gaming feature unrelated to bug reporting
3. **Labs/Simulations** - Large separate training platform

### Phase 2: Medium Priority Removals
4. **Education Platform** - Course system with significant complexity
5. **Hackathon Management** - Event management system
6. **Adventure/Quest System** - Gamification layer
7. **OSSH Features** - Separate tool for open source discovery

### Phase 3: Low Priority Removals (Can be gradual)
8. **Forum Platform** - Can migrate to external platform
9. **Blog System** - Can use external CMS
10. **Job Board** - Can use existing job platforms
11. **Video Call** - Use external video services
12. **Queue/Messaging** - May be replaced by modern alternatives

### Phase 4: Consider for Simplification
13. **Trademark Monitoring** - Evaluate actual usage
14. **Banned Apps Database** - Evaluate necessity
15. **Some Social Features** - Keep only what's needed for collaboration

---

## Migration Path

### For Each Component:
1. **Assess Dependencies:** Map all database relationships and code dependencies
2. **Create New Repository:** Set up separate repo with clear naming (e.g., `BLT-Academy`, `BLT-Blockchain`)
3. **Export Data:** Create migration scripts for existing data
4. **API Boundaries:** Define clean API interfaces between core BLT and extracted services
5. **Documentation:** Document the extraction and new repository setup
6. **Deprecation Notice:** Announce deprecation timeline to users
7. **Remove Code:** Clean up models, views, templates, and migrations

### Benefits of Extraction:
- **Focused Core:** BLT becomes laser-focused on bug bounties and vulnerability reporting
- **Easier Maintenance:** Smaller codebase is easier to maintain and test
- **Independent Development:** Each extracted component can evolve independently
- **Clearer Purpose:** New users immediately understand BLT's purpose
- **Better Performance:** Reduced complexity improves performance
- **Microservices Architecture:** Enables scaling individual components as needed

---

## Timeline Recommendation

- **Q1 2025:** Phase 1 removals (Crypto, Staking, Labs)
- **Q2 2025:** Phase 2 removals (Education, Hackathons, Adventures)
- **Q3 2025:** Phase 3 removals (Forum, Blog, Jobs, etc.)
- **Q4 2025:** Phase 4 simplification and optimization

---

## Questions to Consider

1. **User Impact:** Which features have active users that need migration support?
2. **Data Retention:** What historical data needs to be preserved?
3. **API Compatibility:** Which integrations depend on these features?
4. **Resource Allocation:** Who will maintain the extracted repositories?
5. **Prioritization:** Which extractions provide the most value with least disruption?

---

## Conclusion

By removing these components, OWASP BLT can return to its roots as a focused, efficient bug bounty and vulnerability reporting platform. The extracted features can thrive as independent projects with dedicated maintainers, while the core BLT codebase becomes more maintainable and accessible to new contributors.

---

**Document Version:** 1.0  
**Last Updated:** November 26, 2025  
**Maintained By:** OWASP BLT Core Team
