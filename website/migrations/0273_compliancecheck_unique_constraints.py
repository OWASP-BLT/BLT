from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0272_threatintelentry_vulnerability_compliancecheck"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="compliancecheck",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="compliancecheck",
            constraint=models.UniqueConstraint(
                condition=models.Q(("organization__isnull", False)),
                fields=["organization", "framework", "requirement_id"],
                name="unique_compliance_with_org",
            ),
        ),
    ]
