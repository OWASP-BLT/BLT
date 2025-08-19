import json

from website.aibot.aibot_env import configure_and_validate_settings
from website.aibot.network import generate_gemini_response

configure_and_validate_settings()

res = generate_gemini_response("Give me a detailed introduction about yourself")

with open("gemini_response.txt", "w", encoding="utf-8") as f:
    f.write(json.dumps(res, indent=2))
