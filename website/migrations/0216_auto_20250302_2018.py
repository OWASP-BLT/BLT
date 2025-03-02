from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0215_bid_github_username_alter_bid_user"),
    ]

    operations = [
        # Change categories column
        migrations.RunSQL(
            sql="""
            ALTER TABLE website_organization
            ALTER COLUMN categories TYPE jsonb
            USING jsonb_build_array(categories);
            """,
            reverse_sql="""
            ALTER TABLE website_organization
            ALTER COLUMN categories TYPE character varying[]
            USING array(SELECT jsonb_array_elements_text(categories));
            """,
        ),
        # Change tech_tags column
        migrations.RunSQL(
            sql="""
            ALTER TABLE website_organization
            ALTER COLUMN tech_tags TYPE jsonb
            USING jsonb_build_array(tech_tags);
            """,
            reverse_sql="""
            ALTER TABLE website_organization
            ALTER COLUMN tech_tags TYPE character varying[]
            USING array(SELECT jsonb_array_elements_text(tech_tags));
            """,
        ),
        # Change topic_tags column
        migrations.RunSQL(
            sql="""
            ALTER TABLE website_organization
            ALTER COLUMN topic_tags TYPE jsonb
            USING jsonb_build_array(topic_tags);
            """,
            reverse_sql="""
            ALTER TABLE website_organization
            ALTER COLUMN topic_tags TYPE character varying[]
            USING array(SELECT jsonb_array_elements_text(topic_tags));
            """,
        ),
    ]
