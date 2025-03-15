# Generated by Django 5.1.6 on 2025-02-22 03:18

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0206_suggestioncategory_alter_suggestion_options_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="SuggestionCategory",
            new_name="ForumCategory",
        ),
        migrations.RenameModel(
            old_name="SuggestionComment",
            new_name="ForumComment",
        ),
        migrations.RenameModel(
            old_name="Suggestion",
            new_name="ForumPost",
        ),
        migrations.RenameModel(
            old_name="SuggestionVotes",
            new_name="ForumVote",
        ),
        migrations.AlterModelOptions(
            name="forumcategory",
            options={"verbose_name_plural": "Forum Categories"},
        ),
        migrations.RenameField(
            model_name="forumcomment",
            old_name="suggestion",
            new_name="post",
        ),
        migrations.RenameField(
            model_name="forumvote",
            old_name="suggestion",
            new_name="post",
        ),
    ]

