"""
Configuration for Sizzle app with sensible defaults for BLT.
Follows Django's AUTH_USER_MODEL pattern for swappable models.
"""
from django.conf import settings

# Sizzle configuration - makes the plugin flexible for different Django projects
SIZZLE_SETTINGS = {
    # Default base template for standalone projects
    'BASE_TEMPLATE': getattr(settings, 'SIZZLE_BASE_TEMPLATE', 'base.html'),
    
    # Parent base template - set this in your main project for integration
    'PARENT_BASE': getattr(settings, 'SIZZLE_PARENT_BASE', None),
    
    # Whether to integrate with the parent project's layout
    'USE_PROJECT_BASE': getattr(settings, 'SIZZLE_USE_PROJECT_BASE', True),
    
    # Show sidenav if available (for BLT integration)
    'SHOW_SIDENAV': getattr(settings, 'SIZZLE_SHOW_SIDENAV', True),
}

# ===============================
# Model Configuration (Swappable)
# ===============================

# Slack Integration Model (swappable)
SIZZLE_SLACK_INTEGRATION_MODEL = getattr(
    settings,
    'SIZZLE_SLACK_INTEGRATION_MODEL',
    'website.SlackIntegration'  # Default for BLT
)

# Organization Model (swappable)
SIZZLE_ORGANIZATION_MODEL = getattr(
    settings,
    'SIZZLE_ORGANIZATION_MODEL',
    'website.Organization'  # Default for BLT
)

# UserProfile Model (swappable)
SIZZLE_USERPROFILE_MODEL = getattr(
    settings,
    'SIZZLE_USERPROFILE_MODEL',
    'website.UserProfile'  # Default for BLT
)

# Notification Model (swappable)
SIZZLE_NOTIFICATION_MODEL = getattr(
    settings,
    'SIZZLE_NOTIFICATION_MODEL',
    'website.Notification'  # Default for BLT
)

# ===============================
# Feature Flags
# ===============================

# Enable/disable features
SIZZLE_SLACK_ENABLED = getattr(
    settings,
    'SIZZLE_SLACK_ENABLED',
    True  # Enabled by default for BLT
)

SIZZLE_EMAIL_REMINDERS_ENABLED = getattr(
    settings,
    'SIZZLE_EMAIL_REMINDERS_ENABLED',
    True
)

SIZZLE_DAILY_CHECKINS_ENABLED = getattr(
    settings,
    'SIZZLE_DAILY_CHECKINS_ENABLED',
    True
)

def get_base_template():
    """Get the appropriate base template for sizzle templates"""
    if SIZZLE_SETTINGS['PARENT_BASE']:
        return SIZZLE_SETTINGS['PARENT_BASE']
    return SIZZLE_SETTINGS['BASE_TEMPLATE']