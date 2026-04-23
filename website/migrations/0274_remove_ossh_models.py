from django.db import migrations


class Migration(migrations.Migration):
    """
    Drop OsshCommunity, OsshDiscussionChannel, and OsshArticle tables.
    The OSSH feature has been migrated to https://github.com/OWASP-BLT/BLT-OSSH.
    """

    dependencies = [
        ("website", "0273_issue_spam_reason_issue_spam_score"),
    ]

    operations = [
        migrations.DeleteModel(
            name="OsshArticle",
        ),
        migrations.DeleteModel(
            name="OsshCommunity",
        ),
        migrations.DeleteModel(
            name="OsshDiscussionChannel",
        ),
    ]
