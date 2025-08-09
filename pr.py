import json
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

from website.aibot.main import PullRequest, _fetch_pr_diff

with open("webhook_pr_event.txt", "r", encoding="utf-8") as f:
    payload = f.read()
    payload = json.loads(payload)

pr_instance = PullRequest(payload)

pr_diff = _fetch_pr_diff(pr_instance.diff_url)

print(pr_diff)
