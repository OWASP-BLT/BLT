# AI-Powered GitHub Sportscaster Feature

## Overview

The AI-Powered GitHub Sportscaster is a live streaming feature that monitors GitHub activity across repositories and organizations, providing real-time sports-style commentary powered by AI. It displays activity as an exciting sports broadcast with animated visuals, live commentary, and dynamic leaderboards.

## Visual Design

The feature includes an animated sportscaster bot (represented by 🤖) that announces GitHub events in real-time. The interface features:

- **Animated Bot**: A pulsing circular bot avatar that represents the sportscaster
- **Live Commentary**: Dynamic text updates with AI-generated sports-style commentary
- **Event Feed**: Scrolling feed of recent events with emojis and timestamps
- **Real-time Leaderboard**: Rankings showing repository performance metrics

## Architecture

### Backend Stack

```
Django App (sportscaster)
├── Models
│   ├── MonitoredEntity (repos/orgs to track)
│   ├── GitHubEvent (events with AI commentary)
│   ├── Leaderboard (real-time rankings)
│   ├── UserChannel (user-curated channels)
│   └── AICommentaryTemplate (commentary templates)
├── Services
│   ├── GitHubService (API integration)
│   ├── AICommentaryService (AI commentary)
│   └── EventProcessingService (event processing)
├── Consumers
│   └── SportscasterConsumer (WebSocket handler)
├── Views & APIs
│   ├── Web views (home, live, manage)
│   └── REST API endpoints
└── Management Commands
    ├── process_github_events
    └── seed_sportscaster
```

### Frontend Stack

- **HTML5 + Tailwind CSS**: Responsive, modern UI
- **JavaScript + WebSocket**: Real-time updates
- **Django Templates**: Server-side rendering

### Data Flow

```
GitHub API → EventProcessingService → Database
                                    ↓
                              AI Commentary Generation
                                    ↓
                         WebSocket Consumer
                                    ↓
                              Frontend Display
```

## Key Components

### 1. Models (`sportscaster/models.py`)

#### MonitoredEntity
Represents a GitHub entity being monitored.

**Fields**:
- `name`: Repository/organization name
- `scope`: Type (repository, organization, tag, curated_list, all_github)
- `github_url`: GitHub URL
- `is_active`: Whether monitoring is active
- `metadata`: Additional configuration

#### GitHubEvent
Stores GitHub events with generated commentary.

**Fields**:
- `monitored_entity`: Foreign key to MonitoredEntity
- `event_type`: Type of event (star, fork, pull_request, etc.)
- `event_data`: JSON data about the event
- `timestamp`: When the event occurred
- `processed`: Whether event has been processed
- `commentary_generated`: Whether AI commentary was generated
- `commentary_text`: The generated commentary

#### Leaderboard
Tracks real-time rankings.

**Fields**:
- `monitored_entity`: Foreign key to MonitoredEntity
- `metric_type`: Type of metric (stars, forks, etc.)
- `current_value`: Current metric value
- `previous_value`: Previous value for change calculation
- `rank`: Current rank position

#### UserChannel
User-curated monitoring channels.

**Fields**:
- `user`: Foreign key to User
- `name`: Channel name
- `description`: Channel description
- `monitored_entities`: Many-to-many with MonitoredEntity
- `is_public`: Whether channel is publicly visible

### 2. Services (`sportscaster/services.py`)

#### GitHubService
Handles GitHub API integration with caching and rate limiting.

**Methods**:
- `get_repository_events(owner, repo)`: Fetch recent events
- `get_repository_stats(owner, repo)`: Get repo statistics
- `get_organization_repositories(org)`: List org repos
- `parse_github_url(url)`: Extract owner/repo from URL

**Features**:
- Request caching (1-10 minutes based on endpoint)
- Rate limit handling
- Error logging and recovery

#### AICommentaryService
Generates sports-style commentary using OpenAI.

**Methods**:
- `generate_commentary(event)`: Generate AI commentary
- `_get_commentary_template(event_type)`: Get template for event
- `_prepare_event_context(event)`: Prepare event context
- `_build_prompt(event, context, template)`: Build AI prompt
- `_generate_fallback_commentary(event)`: Fallback without AI

**AI Model**: GPT-4o-mini (o3-mini-high not yet available)

**Prompt Example**:
```
Generate an exciting sports-style commentary for this GitHub event:

Event Type: star
Repository: facebook/react
Context: Oh wow! facebook/react just gained 5 stars! The crowd goes wild!

Make it sound like you're commentating a thrilling sports match. Be energetic and engaging!
Keep it under 100 words.
```

#### EventProcessingService
Processes GitHub events and updates leaderboards.

**Methods**:
- `process_monitored_entities()`: Process all active entities
- `process_entity(entity)`: Process single entity
- `_process_events(entity, events)`: Create event records
- `_update_leaderboard(entity, stats)`: Update rankings
- `_update_rankings()`: Recalculate all rankings

### 3. WebSocket Consumer (`sportscaster/consumers.py`)

#### SportscasterConsumer
Handles real-time WebSocket connections.

**Methods**:
- `connect()`: Accept WebSocket connection
- `disconnect(close_code)`: Handle disconnection
- `receive(text_data)`: Process client messages
- `send_periodic_updates()`: Send updates every 10 seconds
- `get_leaderboard_data()`: Fetch leaderboard
- `get_recent_events(limit)`: Fetch recent events

**Message Types**:
- `connection_status`: Connection state
- `live_update`: Periodic event updates
- `new_event`: New event broadcast
- `leaderboard`: Leaderboard data
- `ping/pong`: Keep-alive

### 4. Views & APIs (`sportscaster/views.py`)

#### Web Views
- `sportscaster_home`: Landing page with features and channels
- `sportscaster_live`: Live stream interface
- `manage_channels`: Channel creation and management

#### API Endpoints
- `GET /sportscaster/api/leaderboard/`: Get current leaderboard
- `GET /sportscaster/api/events/`: Get recent events
- `POST /sportscaster/api/refresh/`: Trigger event refresh
- REST API for MonitoredEntity and UserChannel (via ViewSets)

### 5. Management Commands

#### process_github_events
Processes GitHub events for monitored entities.

**Usage**:
```bash
# One-time processing
python manage.py process_github_events

# Continuous processing
python manage.py process_github_events --continuous --interval 60
```

#### seed_sportscaster
Seeds initial data including commentary templates and sample repositories.

**Usage**:
```bash
python manage.py seed_sportscaster
```

## Frontend Interface

### Home Page (`sportscaster/templates/sportscaster/home.html`)

Features:
- Hero section with main call-to-action
- Features grid explaining the system
- Channel listings (user channels and public channels)
- "How It Works" section

Design:
- Dark gradient background (gray-900 to gray-800)
- Tailwind CSS styling
- Red accent color (#e74c3c)
- Responsive grid layout

### Live Stream (`sportscaster/templates/sportscaster/live.html`)

Features:
- Connection status indicator
- Animated sportscaster bot
- Live commentary display
- Scrolling event feed
- Real-time leaderboard sidebar

Interactive Elements:
- WebSocket connection management
- Auto-reconnection on disconnect
- Periodic ping to keep connection alive
- Real-time event animations

WebSocket Client Features:
```javascript
// Connection management
connectWebSocket() - Establishes WebSocket connection
updateConnectionStatus() - Updates UI status
handleLiveUpdate() - Processes incoming events
updateLeaderboard() - Updates rankings display
```

### Manage Channels (`sportscaster/templates/sportscaster/manage_channels.html`)

Features:
- Create new channel form
- List of user's channels
- Edit/delete channel actions
- Public/private toggle

## Configuration

### Environment Variables

```bash
# Required for GitHub monitoring
GITHUB_TOKEN=your_github_personal_access_token

# Optional for AI commentary (falls back to templates if not set)
OPENAI_API_KEY=your_openai_api_key
```

### Django Settings

Added to `INSTALLED_APPS`:
```python
INSTALLED_APPS = (
    ...
    "sportscaster",
    ...
)
```

Added to WebSocket routing (`blt/routing.py`):
```python
re_path(r"ws/sportscaster/(?P<channel_id>[\w-]+)/$", SportscasterConsumer.as_asgi()),
```

Added to URLs (`blt/urls.py`):
```python
path("sportscaster/", include("sportscaster.urls")),
```

## Setup & Deployment

### Initial Setup

1. **Install Dependencies**:
   ```bash
   poetry install
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add GITHUB_TOKEN and OPENAI_API_KEY
   ```

3. **Run Migrations**:
   ```bash
   poetry run python manage.py migrate
   ```

4. **Seed Initial Data**:
   ```bash
   poetry run python manage.py seed_sportscaster
   ```

### Running the Sportscaster

1. **Start Django Server**:
   ```bash
   poetry run python manage.py runserver
   ```

2. **Start Event Processing** (in separate terminal):
   ```bash
   poetry run python manage.py process_github_events --continuous --interval 60
   ```

3. **Access Interface**:
   - Home: http://localhost:8000/sportscaster/
   - Live Stream: http://localhost:8000/sportscaster/live/

### Production Deployment

For production deployment:

1. **Use Celery for Background Processing**:
   - Convert `process_github_events` to Celery task
   - Schedule with Celery Beat for periodic execution

2. **WebSocket Requirements**:
   - Redis for channel layer
   - ASGI server (Daphne or Uvicorn)
   - WebSocket support in load balancer

3. **Scaling Considerations**:
   - Cache GitHub API responses
   - Rate limit WebSocket connections
   - Use database indexes (already configured)
   - Monitor OpenAI API usage

## Testing

### Test Suite (`sportscaster/tests.py`)

Tests cover:
- Model creation and validation
- String representations
- API endpoints
- Leaderboard calculations
- Channel management

**Run Tests**:
```bash
poetry run python manage.py test sportscaster
```

**Test Results**:
```
Ran 10 tests in 1.202s
OK
```

### Test Coverage

- ✅ MonitoredEntity model
- ✅ GitHubEvent model
- ✅ Leaderboard model
- ✅ UserChannel model
- ✅ API endpoints (leaderboard, events)

## Security

### Implemented Security Measures

1. **URL Validation**: GitHub URLs are validated to prevent bypass attacks
2. **API Key Security**: Keys stored in environment variables
3. **CSRF Protection**: Enabled on API endpoints
4. **WebSocket Authentication**: Can be restricted to authenticated users
5. **Rate Limiting**: Implemented for GitHub API calls

### CodeQL Analysis

✅ **No security vulnerabilities found**

Fixed vulnerability:
- Incomplete URL substring sanitization (py/incomplete-url-substring-sanitization)

## Performance

### Optimization Strategies

1. **Caching**:
   - GitHub API responses (1-10 minutes)
   - Leaderboard data
   - Event processing results

2. **Database Indexes**:
   - GitHubEvent: timestamp, event_type, processed
   - Leaderboard: rank ordering

3. **Rate Limiting**:
   - GitHub API: Respect rate limits with caching
   - WebSocket: Limit concurrent connections

4. **Async Operations**:
   - WebSocket consumer uses async/await
   - Periodic updates without blocking

## Future Enhancements

### Planned Features

1. **Enhanced Visuals**:
   - [ ] Voice narration for commentary
   - [ ] Video animations for sportscaster
   - [ ] Interactive charts and graphs

2. **Additional Event Sources**:
   - [ ] GitLab integration
   - [ ] Bitbucket support
   - [ ] Custom event webhooks

3. **Analytics**:
   - [ ] Historical event playback
   - [ ] Trend analysis
   - [ ] Comparative analytics

4. **Mobile Support**:
   - [ ] Mobile-optimized UI
   - [ ] Push notifications
   - [ ] Mobile app

5. **Social Features**:
   - [ ] Share commentary
   - [ ] Team channels
   - [ ] Social integrations

## Troubleshooting

### Common Issues

**WebSocket Connection Fails**:
- Ensure Redis is running for channel layer
- Check WebSocket URL scheme (ws:// vs wss://)
- Verify ASGI configuration

**No Events Appearing**:
- Verify GitHub token is valid
- Check monitored entities are `is_active=True`
- Run event processing manually
- Check logs for API errors

**AI Commentary Not Generating**:
- Verify OpenAI API key is set
- Check for API errors in logs
- System will use fallback templates if AI fails

**Rate Limit Errors**:
- Increase caching timeouts
- Reduce polling frequency
- Use multiple GitHub tokens (if allowed)

## Contributing

Contributions are welcome! Please:

1. Follow Django coding standards
2. Write tests for new features
3. Update documentation
4. Run linters (black, isort, ruff)
5. Ensure security scans pass

## License

This feature is part of the BLT project and follows the same license (AGPLv3).

## Credits

Developed as part of the OWASP BLT project.

Inspired by the concept of making GitHub activity monitoring more engaging and entertaining through AI-powered sports commentary.

## Support

For issues and questions:
- GitHub Issues: https://github.com/OWASP-BLT/BLT/issues
- Documentation: See `sportscaster/README.md`

---

**Last Updated**: 2025-11-16
**Version**: 1.0.0
