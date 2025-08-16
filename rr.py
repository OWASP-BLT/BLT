from website.aibot.aibot_env import configure_and_validate_settings
from website.aibot.qdrant_utils import process_remote_repo

configure_and_validate_settings()

collection = process_remote_repo("SahilDhillon21/task-treasure", "842551877")
print(collection)
