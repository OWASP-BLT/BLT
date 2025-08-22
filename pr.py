import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

from website.aibot.network import get_github_installation_token

tkn = get_github_installation_token()
print(tkn)
