from website.aibot.aibot_env import configure_and_validate_settings
from website.aibot.clients import q_client
from website.aibot.qdrant_utils import q_process_remote_repote_repo

configure_and_validate_settings()


# collection = process_remote_repo(q_client, "SahilDhillon21/task-treasure", "842551877")
collection = q_process_remote_repote_repo(q_client, "SahilDhillon21/iot-basic-renamed", "964079422")
print(collection)
