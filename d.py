import json

from website.aibot.aibot_env import configure_and_validate_settings
from website.aibot.main import handle_installation_event

configure_and_validate_settings()

with open("website/aibot/payloads/installation.created.selected.txt", "r", encoding="utf-8") as f:
    payload = f.read()

    payload_json = json.loads(payload)
    handle_installation_event(payload_json)
