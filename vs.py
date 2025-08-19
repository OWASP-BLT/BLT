import json

from website.aibot.aibot_env import load_prompts

p = load_prompts()
print(json.dumps(p, indent=2))
