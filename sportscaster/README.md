# AI-Powered GitHub Sportscaster

An animated sportscaster bot that monitors GitHub activity and provides live play-by-play commentary with real-time leaderboards.

## Features

- **Real-Time Monitoring**: Tracks GitHub events (stars, forks, PRs, commits, releases) across repositories and organizations
- **AI Commentary**: Generates sports-style commentary using OpenAI's GPT models
- **Live Leaderboards**: Real-time rankings showing repository performance
- **WebSocket Streaming**: Live updates delivered via WebSocket connections
- **User Channels**: Create custom channels to monitor specific repositories
- **Public & Private Channels**: Share your channels or keep them private

## Architecture

### Backend Components

1. **Models** (`models.py`):
   - `MonitoredEntity`: Repositories, organizations, or tags being tracked
   - `GitHubEvent`: GitHub events with generated commentary
   - `Leaderboard`: Real-time rankings by metrics
   - `UserChannel`: User-curated monitoring channels
   - `AICommentaryTemplate`: Templates for AI commentary generation

2. **Services** (`services.py`):
   - `GitHubService`: GitHub API integration
   - `AICommentaryService`: AI-powered commentary generation
   - `EventProcessingService`: Event processing and leaderboard updates

3. **Consumers** (`consumers.py`):
   - `SportscasterConsumer`: WebSocket handler for real-time updates

4. **Views** (`views.py`):
   - Web views for home, live stream, and channel management
   - REST API endpoints for data access

### Frontend Components

1. **Templates**:
   - `home.html`: Landing page with features and channels
   - `live.html`: Live stream interface with animated bot
   - `manage_channels.html`: Channel creation and management

2. **WebSocket Client**:
   - Real-time connection management
   - Event handling and UI updates
   - Leaderboard synchronization

## Setup Instructions

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- PostgreSQL or SQLite (for development)
- Redis (for WebSocket channel layer)
- GitHub API token
- OpenAI API key (optional, for AI commentary)

### Installation

1. **Install Dependencies**:
   ```bash
   poetry install
   ```

2. **Configure Environment Variables**:
   Add to your `.env` file:
   ```bash
   GITHUB_TOKEN=your_github_token_here
   OPENAI_API_KEY=your_openai_api_key_here
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

1. **Start the Django Server**:
   ```bash
   poetry run python manage.py runserver
   ```

2. **Start Event Processing** (in a separate terminal):
   ```bash
   # One-time processing
   poetry run python manage.py process_github_events
   
   # Continuous processing
   poetry run python manage.py process_github_events --continuous --interval 60
   ```

3. **Access the Interface**:
   - Home: `http://localhost:8000/sportscaster/`
   - Live Stream: `http://localhost:8000/sportscaster/live/`

## Usage Guide

### Creating a Channel

1. Navigate to "Manage Channels" from the sportscaster home
2. Click "Create New Channel"
3. Enter channel name and description
4. Choose to make it public or private
5. Add repositories to monitor

### Watching the Live Stream

1. Go to the sportscaster home
2. Click "Watch Live Stream" or select a specific channel
3. See real-time events with AI commentary
4. Monitor the leaderboard for rankings

### API Endpoints

- `GET /sportscaster/api/leaderboard/`: Get current leaderboard
- `GET /sportscaster/api/events/`: Get recent events
- `POST /sportscaster/api/refresh/`: Trigger event refresh

## Configuration Options

### Monitored Entity Scopes

- `all_github`: Monitor all GitHub activity
- `organization`: Monitor specific organization
- `repository`: Monitor specific repository
- `tag`: Monitor repositories with specific tag
- `curated_list`: Monitor custom list of repositories

### Event Types

- `star`: Star gains
- `fork`: Fork events
- `pull_request`: Pull request activity
- `commit`: Commit pushes
- `release`: Release publications
- `issue`: Issue creation
- `hackathon`: Hackathon announcements

## Development

### Running Tests

```bash
poetry run python manage.py test sportscaster
```

### Adding New Event Types

1. Add event type to `GitHubEvent.EVENT_TYPES` in `models.py`
2. Create AI commentary template in admin or via `seed_sportscaster`
3. Update event mapping in `EventProcessingService._map_event_type()`

### Customizing Commentary

AI commentary can be customized by:
1. Modifying templates in the admin interface
2. Adjusting the prompt in `AICommentaryService._build_prompt()`
3. Changing the OpenAI model in `AICommentaryService.generate_commentary()`

## Performance Considerations

- **Rate Limiting**: GitHub API has rate limits; use caching appropriately
- **WebSocket Connections**: Monitor concurrent connections
- **Event Processing**: Run as background task (Celery recommended for production)
- **Database Indexing**: Indexes are set on timestamp and event_type fields

## Security

- API keys are stored in environment variables
- WebSocket connections can be authenticated
- Channel visibility controlled by `is_public` flag
- CSRF protection on API endpoints

## Troubleshooting

### WebSocket Connection Issues

- Ensure Redis is running for channel layer
- Check WebSocket URL scheme (ws:// vs wss://)
- Verify ASGI configuration in `routing.py`

### No Events Appearing

- Verify GitHub token is valid and has correct permissions
- Check that monitored entities are marked as `is_active=True`
- Run event processing command manually to test
- Check logs for API errors

### AI Commentary Not Generating

- Verify OpenAI API key is set correctly
- Check for API errors in logs
- Fallback templates will be used if AI fails

## Future Enhancements

- [ ] Support for more event sources (GitLab, Bitbucket)
- [ ] Enhanced video/animation for the sportscaster bot
- [ ] Voice narration for commentary
- [ ] Historical event playback
- [ ] Advanced analytics and insights
- [ ] Mobile app support
- [ ] Export leaderboards and reports

## Contributing

Contributions are welcome! Please follow the project's coding standards and include tests for new features.

## License

This feature is part of the BLT project and follows the same license (AGPLv3).
