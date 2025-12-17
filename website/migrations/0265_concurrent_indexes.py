from django.db import migrations


def create_indexes(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    # POSTGRESQL (PRODUCTION)
    if vendor == "postgresql":
        schema_editor.execute(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_dai_user_id_1d9003_idx" '
            'ON "website_dailystatusreport" ("user_id", "created" DESC);'
        )
        schema_editor.execute(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_dai_goal_ac_39f9cb_idx" '
            'ON "website_dailystatusreport" ("goal_accomplished");'
        )
        schema_editor.execute(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_use_leaderb_aa31e8_idx" '
            'ON "website_userprofile" ("leaderboard_score" DESC, "current_streak" DESC);'
        )
        schema_editor.execute(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_use_team_id_8dcd03_idx" '
            'ON "website_userprofile" ("team_id", "leaderboard_score" DESC);'
        )
        schema_editor.execute(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_use_quality_777c8d_idx" '
            'ON "website_userprofile" ("quality_score" DESC);'
        )

    #  SQLITE / OTHERS (TESTS)

    else:
        schema_editor.execute(
            'CREATE INDEX IF NOT EXISTS "website_dai_user_id_1d9003_idx" '
            'ON "website_dailystatusreport" ("user_id", "created" DESC);'
        )
        schema_editor.execute(
            'CREATE INDEX IF NOT EXISTS "website_dai_goal_ac_39f9cb_idx" '
            'ON "website_dailystatusreport" ("goal_accomplished");'
        )
        schema_editor.execute(
            'CREATE INDEX IF NOT EXISTS "website_use_leaderb_aa31e8_idx" '
            'ON "website_userprofile" ("leaderboard_score" DESC, "current_streak" DESC);'
        )
        schema_editor.execute(
            'CREATE INDEX IF NOT EXISTS "website_use_team_id_8dcd03_idx" '
            'ON "website_userprofile" ("team_id", "leaderboard_score" DESC);'
        )
        schema_editor.execute(
            'CREATE INDEX IF NOT EXISTS "website_use_quality_777c8d_idx" '
            'ON "website_userprofile" ("quality_score" DESC);'
        )


def drop_indexes(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        schema_editor.execute('DROP INDEX CONCURRENTLY IF EXISTS "website_dai_user_id_1d9003_idx";')
        schema_editor.execute('DROP INDEX CONCURRENTLY IF EXISTS "website_dai_goal_ac_39f9cb_idx";')
        schema_editor.execute('DROP INDEX CONCURRENTLY IF EXISTS "website_use_leaderb_aa31e8_idx";')
        schema_editor.execute('DROP INDEX CONCURRENTLY IF EXISTS "website_use_team_id_8dcd03_idx";')
        schema_editor.execute('DROP INDEX CONCURRENTLY IF EXISTS "website_use_quality_777c8d_idx";')
    else:
        schema_editor.execute('DROP INDEX IF EXISTS "website_dai_user_id_1d9003_idx";')
        schema_editor.execute('DROP INDEX IF EXISTS "website_dai_goal_ac_39f9cb_idx";')
        schema_editor.execute('DROP INDEX IF EXISTS "website_use_leaderb_aa31e8_idx";')
        schema_editor.execute('DROP INDEX IF EXISTS "website_use_team_id_8dcd03_idx";')
        schema_editor.execute('DROP INDEX IF EXISTS "website_use_quality_777c8d_idx";')


class Migration(migrations.Migration):
    atomic = False  # ✅ Still required for PostgreSQL CONCURRENTLY

    dependencies = [
        ("website", "0264_userprofile_check_in_count_and_more"),
    ]

    operations = [
        migrations.RunPython(create_indexes, drop_indexes),
    ]
