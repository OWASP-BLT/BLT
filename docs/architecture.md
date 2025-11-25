# OWASP BLT Architecture Diagram

This document provides a visual overview of the OWASP BLT (Bug Logging Tool) architecture.

## System Overview

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        Browser["Web Browser"]
        Mobile["Mobile App"]
        Extension["Browser Extension"]
    end

    subgraph Frontend["Frontend (Django Templates + Tailwind CSS)"]
        Templates["HTML Templates"]
        Static["Static Files (JS/CSS)"]
        Tailwind["Tailwind CSS"]
    end

    subgraph Django["Django Application (blt/)"]
        URLs["URL Router (urls.py)"]
        Middleware["Middleware"]
        Settings["Settings"]
    end

    subgraph Views["Views Layer (website/views/)"]
        CoreViews["Core Views"]
        IssueViews["Issue/Bug Views"]
        OrgViews["Organization Views"]
        UserViews["User Views"]
        ProjectViews["Project Views"]
        HackathonViews["Hackathon Views"]
        EducationViews["Education Views"]
        TeamViews["Team Views"]
        StakingViews["Staking Views"]
    end

    subgraph API["REST API (website/api/)"]
        DRF["Django REST Framework"]
        Serializers["Serializers"]
        ViewSets["ViewSets"]
        Swagger["Swagger/OpenAPI Docs"]
    end

    subgraph WebSocket["Real-time (Django Channels)"]
        ChatConsumer["Chat Consumer"]
        SimilarityConsumer["Similarity Scanner"]
        DirectChatConsumer["Direct Messaging"]
        VideoCallConsumer["Video Call"]
    end

    subgraph Models["Data Models (website/models.py)"]
        UserModels["User & Profile"]
        OrgModels["Organization & Domain"]
        IssueModels["Issue & Hunt"]
        ProjectModels["Project & Repo"]
        GamificationModels["Challenge & Staking"]
        ChatModels["Room & Message"]
        EducationModels["Course & Lecture"]
    end

    subgraph Services["External Services (website/services/)"]
        BlueSky["BlueSky Service"]
    end

    subgraph External["External Integrations"]
        GitHub["GitHub API"]
        Slack["Slack API"]
        OAuth["OAuth Providers"]
        Bitcoin["Bitcoin/BCH"]
        SendGrid["SendGrid Email"]
        GCS["Google Cloud Storage"]
    end

    subgraph Database["Data Layer"]
        PostgreSQL["PostgreSQL"]
        Redis["Redis Cache"]
    end

    Client --> Frontend
    Frontend --> Django
    Django --> Views
    Django --> API
    Django --> WebSocket
    Views --> Models
    API --> Models
    WebSocket --> Models
    Models --> Database
    Views --> Services
    Services --> External
    Views --> External
```

## Component Details

### Core Components Architecture

```mermaid
flowchart LR
    subgraph UserFlow["User Flow"]
        Auth["Authentication"]
        Profile["User Profile"]
        Dashboard["User Dashboard"]
    end

    subgraph BugBounty["Bug Bounty System"]
        Report["Bug Report"]
        Issue["Issue Management"]
        Hunt["Bug Hunt"]
        Bounty["Bounty Payout"]
    end

    subgraph Organization["Organization Management"]
        Org["Organization"]
        Domain["Domain"]
        Team["Team Members"]
        Jobs["Job Board"]
    end

    subgraph Gamification["Gamification"]
        Points["Points System"]
        Badges["Badges"]
        Leaderboard["Leaderboard"]
        Challenges["Challenges"]
        Staking["Staking Pools"]
    end

    subgraph Community["Community Features"]
        Forum["Forum"]
        Chat["Discussion Rooms"]
        DirectMsg["Direct Messages"]
        VideoCall["Video Calls"]
    end

    subgraph Content["Content & Education"]
        Blog["Blog Posts"]
        Courses["Courses"]
        Lectures["Lectures"]
        Adventures["Adventures"]
    end

    Auth --> Profile
    Profile --> Dashboard
    Dashboard --> BugBounty
    Dashboard --> Organization
    Dashboard --> Gamification
    Dashboard --> Community
    Dashboard --> Content
```

## Data Model Relationships

```mermaid
erDiagram
    User ||--o{ UserProfile : has
    User ||--o{ Issue : reports
    User ||--o{ Points : earns
    User ||--o{ Message : sends
    
    Organization ||--o{ Domain : owns
    Organization ||--o{ Hunt : hosts
    Organization ||--o{ Project : manages
    Organization ||--o{ Hackathon : organizes
    Organization ||--o{ Job : posts
    
    Domain ||--o{ Issue : contains
    
    Hunt ||--o{ Issue : tracks
    Hunt ||--o{ HuntPrize : offers
    
    Project ||--o{ Repo : includes
    Project ||--o{ Contribution : has
    
    Repo ||--o{ GitHubIssue : tracks
    Repo ||--o{ Contributor : has
    
    Hackathon ||--o{ HackathonPrize : offers
    Hackathon ||--o{ HackathonSponsor : has
    Hackathon ||--o{ Repo : includes
    
    Challenge ||--o{ StakingPool : uses
    StakingPool ||--o{ StakingEntry : contains
    
    Course ||--o{ Section : contains
    Section ||--o{ Lecture : includes
    
    Room ||--o{ Message : contains
    Thread ||--o{ Message : contains
    
    UserProfile }o--o{ Badge : earns
```

## Views Structure

```mermaid
flowchart TB
    subgraph Core["Core (core.py)"]
        Home["Home Page"]
        Search["Search"]
        Stats["Statistics"]
        Forum["Forum"]
        Donate["Donate"]
    end

    subgraph Issue["Issue (issue.py)"]
        CreateIssue["Create Issue"]
        ViewIssue["View Issue"]
        EditIssue["Edit Issue"]
        GitHubIssues["GitHub Issues"]
        Contribute["Contribute"]
    end

    subgraph Org["Organization (organization.py)"]
        OrgList["Organization List"]
        OrgDetail["Organization Detail"]
        OrgDashboard["Organization Dashboard"]
        DomainMgmt["Domain Management"]
        HuntMgmt["Hunt Management"]
    end

    subgraph UserV["User (user.py)"]
        UserProfile2["User Profile"]
        Leaderboard2["Leaderboard"]
        Contributors["Contributors"]
        Notifications["Notifications"]
        Messaging["Messaging"]
    end

    subgraph Project["Project (project.py)"]
        ProjectList["Project List"]
        ProjectDetail["Project Detail"]
        RepoDetail["Repo Detail"]
        BaconDist["Bacon Distribution"]
    end

    subgraph Hackathon["Hackathon (hackathon.py)"]
        HackList["Hackathon List"]
        HackDetail["Hackathon Detail"]
        HackCreate["Create Hackathon"]
        HackPrizes["Manage Prizes"]
    end

    subgraph Education["Education (education.py)"]
        CourseList["Course List"]
        CourseView["Course View"]
        StudyCourse["Study Course"]
        InstructorDash["Instructor Dashboard"]
    end

    subgraph Teams["Teams (teams.py)"]
        TeamOverview["Team Overview"]
        CreateTeam["Create Team"]
        TeamChallenges2["Team Challenges"]
        Kudos["Give Kudos"]
    end
```

## API Endpoints Structure

```mermaid
flowchart LR
    subgraph RESTAPI["REST API (/api/v1/)"]
        IssuesAPI["Issues API"]
        UsersAPI["Users API"]
        DomainsAPI["Domains API"]
        OrgsAPI["Organizations API"]
        ProjectsAPI["Projects API"]
        TimeLogAPI["Time Logs API"]
        JobsAPI["Jobs API"]
        LeaderboardAPI["Leaderboard API"]
        StatsAPI["Stats API"]
    end

    subgraph Auth["Authentication"]
        TokenAuth["Token Auth"]
        OAuthLogin["OAuth Login"]
        Registration["Registration"]
    end

    subgraph Integration["Integrations"]
        GitHubWebhook["GitHub Webhook"]
        SlackEvents["Slack Events"]
        SendGridWebhook["SendGrid Webhook"]
    end

    Client2["Client"] --> RESTAPI
    Client2 --> Auth
    External2["External Services"] --> Integration
```

## WebSocket Connections

```mermaid
flowchart TB
    subgraph WSConnections["WebSocket Endpoints"]
        WS1["ws/similarity/"]
        WS2["ws/discussion-rooms/chat/<room_id>/"]
        WS3["ws/messaging/<thread_id>/"]
        WS4["ws/video/<room_name>/"]
    end

    subgraph Consumers["WebSocket Consumers"]
        SC["SimilarityConsumer"]
        CC["ChatConsumer"]
        DC["DirectChatConsumer"]
        VC["VideoCallConsumer"]
    end

    WS1 --> SC
    WS2 --> CC
    WS3 --> DC
    WS4 --> VC

    SC --> |"Code Similarity Analysis"| Analysis["Repository Comparison"]
    CC --> |"Real-time Chat"| RoomMsgs["Room Messages"]
    DC --> |"Encrypted DMs"| DirectMsgs["Direct Messages"]
    VC --> |"WebRTC Signaling"| VideoSig["Video Signaling"]
```

## Deployment Architecture

```mermaid
flowchart TB
    subgraph Production["Production Environment"]
        LB["Load Balancer"]
        
        subgraph AppServers["Application Servers"]
            Django1["Django + Gunicorn"]
            Django2["Django + Gunicorn"]
        end
        
        subgraph WSServers["WebSocket Servers"]
            Daphne1["Daphne/Channels"]
        end
        
        subgraph DataStores["Data Stores"]
            PG["PostgreSQL"]
            RedisCache["Redis"]
        end
        
        subgraph Storage["File Storage"]
            GCSBucket["Google Cloud Storage"]
            StaticFiles["Static Files CDN"]
        end
    end

    subgraph External3["External Services"]
        GH["GitHub"]
        Slack2["Slack"]
        SG["SendGrid"]
        BCH["Bitcoin Cash"]
    end

    Users["Users"] --> LB
    LB --> AppServers
    LB --> WSServers
    AppServers --> DataStores
    WSServers --> DataStores
    AppServers --> Storage
    AppServers --> External3
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend Framework** | Django 5.1+ |
| **Frontend** | Django Templates, Tailwind CSS, JavaScript |
| **Database** | PostgreSQL |
| **Cache** | Redis |
| **Real-time** | Django Channels (WebSocket) |
| **API** | Django REST Framework |
| **Authentication** | Django AllAuth, OAuth2 |
| **Task Queue** | Celery (optional) |
| **File Storage** | Google Cloud Storage |
| **Email** | SendGrid |
| **Version Control Integration** | GitHub API |
| **Communication** | Slack API |
| **Payments** | Bitcoin/BCH |
| **Containerization** | Docker |
| **Package Management** | Poetry |

## Feature Modules

| Module | Description |
|--------|-------------|
| **Bug Reporting** | Core issue/bug submission and tracking |
| **Bug Bounties** | Hunt creation, bounty management, rewards |
| **Organizations** | Company/org management, domains, team members |
| **Projects** | Open source project tracking, repos |
| **Hackathons** | Hackathon events, prizes, leaderboards |
| **Education** | Courses, lectures, learning paths |
| **Gamification** | Points, badges, challenges, staking |
| **Community** | Forum, chat rooms, direct messaging |
| **OSSH** | Open Source Sorting Hat - project recommendations |
| **Sizzle** | Time tracking and activity logging |
