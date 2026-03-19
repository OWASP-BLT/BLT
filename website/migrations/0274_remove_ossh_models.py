from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0273_issue_spam_reason_issue_spam_score"),
    ]

    operations = [
        migrations.DeleteModel(name="OsshArticle"),
        migrations.DeleteModel(name="OsshCommunity"),
        migrations.DeleteModel(name="OsshDiscussionChannel"),
    ]
