# BLT Slack Bot Setup Guide
# make sure to run this on your own server 
## Environment Variables

Required environment variables for the bot to function:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_ID_CLIENT=your-client-id
SLACK_WEBHOOK_URL=your-webhook-url
```

## Slack App Configuration

1. Create a new Slack App at https://api.slack.com/apps

2. Under "OAuth & Permissions", add the following scopes:
   ```
   channels:read
   chat:write
   groups:read
   channels:join
   im:write
   users:read
   team:read
   commands
   ```

3. Install the app to your workspace

4. Copy the following credentials:
   - Bot User OAuth Token → `SLACK_BOT_TOKEN`
   - Signing Secret → `SLACK_SIGNING_SECRET`
   - Client ID → `SLACK_ID_CLIENT`

## Slash Commands

The bot currently supports the following commands:

### Basic Commands
- `/help` - Show all available commands
- `/discover` - View latest issues from repositories
- `/stats` - View platform statistics
- `/contrib` - Learn how to contribute to OWASP projects
- `/apps` - List installed apps in the workspace

### Information Commands
- `/gsoc25` - View GSoC 2025 projects and information
- `/blt <subcommand>` - Multi-purpose command with subcommands:
  - `user <username>` - Get OWASP profile for a GitHub user
  - `chapters [search]` - View OWASP chapters
  - `projects [search]` - Discover OWASP projects
  - `gsoc [search]` - Explore GSoC projects
  - `events [category]` - Get upcoming OWASP events
  - `committees [search]` - View OWASP committees

### Poll Commands
- `/blt_poll` - Create and manage polls
  - **Create**: `/blt_poll "Question?" "Option 1" "Option 2" "Option 3"`
  - **Features**:
    - Supports 2-10 options
    - Real-time vote updates with visual progress bars
    - One vote per person (can change vote)
    - Only poll creator can close
  - **Example**: `/blt_poll "What time works best?" "Morning" "Afternoon" "Evening"`

### Reminder Commands
- `/blt_remind` - Set and manage reminders
  - **Create**: `/blt_remind "Message" in <number> <minutes|hours|days>`
  - **For others**: `/blt_remind @user "Message" in <number> <minutes|hours|days>`
  - **List**: `/blt_remind list` - View all pending reminders
  - **Features**:
    - Personal or mention-based reminders
    - Flexible time format (minutes, hours, days)
    - Cancel pending reminders
  - **Examples**:
    - `/blt_remind "Team meeting" in 30 minutes`
    - `/blt_remind me "Follow up" in 2 hours`
    - `/blt_remind @john "Review PR" in 1 day`

### Huddle Commands
- `/blt_huddle` - Schedule and manage huddles/meetings
  - **Create**: `/blt_huddle "Title" "Description" at/in <time> with @user1 @user2`
  - **List**: `/blt_huddle list` - View scheduled huddles in channel
  - **Features**:
    - Schedule with title and description
    - Invite participants with @mentions
    - Accept/decline invitations
    - Only organizer can cancel
  - **Examples**:
    - `/blt_huddle "Sprint Planning" "Q1 planning" at 2:00 PM with @alice @bob`
    - `/blt_huddle "Quick Sync" "Daily standup" in 30 minutes`
    - `/blt_huddle "Design Review" "" at 3:30 PM`

### Bug Reporting
- `/report <description>` - Report a bug or issue

## Integration Setup

1. Navigate to your organization's dashboard
2. Click on "Add Slack Integration"
3. Authorize the app for your workspace
4. Configure the following settings:
   - Default channel for notifications
   - Daily update time (0-23 hour)
   - Welcome message for new members

## Features

### Automatic Welcome Messages
- Customizable welcome messages for new team members
- Supports Slack markdown formatting
- Sent via DM to new members

### Daily Updates
- Configurable daily updates about timelogs
- Set specific hour for updates
- Sent to designated channel

### Repository Discovery
- View latest issues from repositories
- Interactive repository selection
- Issue summaries with links

### Polls
- Create interactive polls with 2-10 options
- Real-time vote counting with visual progress bars
- One vote per person with ability to change vote
- Poll creators can close polls
- Vote anonymously (votes are tracked but not displayed publicly)

### Reminders
- Set personal or mention-based reminders
- Flexible scheduling (minutes, hours, days)
- List and cancel pending reminders
- Automatic delivery at scheduled time
- Support for reminding other users

### Huddles/Meetings
- Schedule meetings with title and description
- Invite participants using @mentions
- Flexible time formats ("at HH:MM" or "in X minutes/hours")
- Accept/decline invitations
- Track participant responses
- Only organizer can cancel
- List all scheduled huddles in a channel

### Command Handling
- Extensive slash command support
- Interactive block components
- Error handling and user feedback
- Help documentation for each command

### Activity Logging
- Comprehensive activity tracking
- Success/failure monitoring
- Workspace-specific logging

## Monitoring

### Bot Activity Tracking
The bot's activity is logged in the `SlackBotActivity` model. You can monitor:
- Success rates
- Activity types
- Workspace usage
- Recent activities

### Admin Interface
Access logs in Django admin under "Slack Bot Activity" with:
- Filtering by activity type
- Success/failure tracking
- Workspace-specific views
- Detailed error messages

## Testing

Test files are available in `website/test_slack.py` for verifying:
- Command handling
- Event processing
- Welcome message delivery
- Integration functionality

## Troubleshooting

Common issues and solutions:

1. **Bot Not Responding**
   - Verify environment variables are set correctly
   - Check bot token permissions
   - Ensure bot is invited to channels

2. **Welcome Messages Not Sending**
   - Verify bot has `im:write` permission
   - Check workspace token is valid
   - Ensure welcome message is configured

3. **Commands Not Working**
   - Verify slash command configuration
   - Check signing secret is correct
   - Ensure command URLs are accessible

## Security Notes

- Keep all tokens and secrets secure
- Never commit environment variables to version control
- Regularly rotate tokens and secrets
- Monitor bot activity for unauthorized usage

## Support

For additional support:
- Check the BLT documentation
- Review the Slack API documentation
- Submit issues on the BLT GitHub repository 
