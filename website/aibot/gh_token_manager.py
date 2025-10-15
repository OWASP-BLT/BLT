from django.conf import settings

from website.aibot.github_api import GitHubTokenManager

_token_manager = None


def get_token_manager():
    global _token_manager
    if _token_manager is None:
        _token_manager = GitHubTokenManager(
            settings.GITHUB_AIBOT_APP_ID, settings.GITHUB_AIBOT_APP_NAME, settings.GITHUB_AIBOT_PRIVATE_KEY_B64
        )
    return _token_manager
