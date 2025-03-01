# BLT Slack Bot Setup Guide

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
- `/discover` - View latest issues from repositories

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

### Command Handling
- Slash command support
- Interactive components
- Error handling and user feedback

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