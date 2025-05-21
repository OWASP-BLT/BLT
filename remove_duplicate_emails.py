import os

import django
from django.db import transaction

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Count

User = get_user_model()

# Find duplicate email
duplicates = User.objects.values("email").annotate(email_count=Count("id")).filter(email_count__gt=1)

for duplicate in duplicates:
    email = duplicate["email"]
    print(f"Processing duplicates for email: {email}")

    # Get all users with this email
    users = User.objects.filter(email=email).order_by("id")

    duplicate_count = users.count() - 1

    with transaction.atomic():
        # Keep the first user and delete the rest
        first_user = users.first()
        users.exclude(id=first_user.id).delete()

    print(f"Kept user {first_user.id}, deleted {duplicate_count} duplicates.")
