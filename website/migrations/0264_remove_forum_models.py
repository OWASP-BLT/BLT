# Generated manually for removing forum models

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0263_githubissue_githubissue_pr_merged_idx_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="forumcomment",
            name="parent",
        ),
        migrations.RemoveField(
            model_name="forumcomment",
            name="post",
        ),
        migrations.RemoveField(
            model_name="forumcomment",
            name="user",
        ),
        migrations.RemoveField(
            model_name="forumpost",
            name="category",
        ),
        migrations.RemoveField(
            model_name="forumpost",
            name="organization",
        ),
        migrations.RemoveField(
            model_name="forumpost",
            name="project",
        ),
        migrations.RemoveField(
            model_name="forumpost",
            name="repo",
        ),
        migrations.RemoveField(
            model_name="forumpost",
            name="user",
        ),
        migrations.RemoveField(
            model_name="forumvote",
            name="post",
        ),
        migrations.RemoveField(
            model_name="forumvote",
            name="user",
        ),
        migrations.DeleteModel(
            name="ForumCategory",
        ),
        migrations.DeleteModel(
            name="ForumComment",
        ),
        migrations.DeleteModel(
            name="ForumPost",
        ),
        migrations.DeleteModel(
            name="ForumVote",
        ),
    ]
