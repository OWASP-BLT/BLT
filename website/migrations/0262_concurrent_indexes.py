from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("website", "0261_userprofile_check_in_count_and_more"),
    ]

    operations = [
        # DailyStatusReport indexes
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_dai_user_id_1d9003_idx" '
            'ON "website_dailystatusreport" ("user_id", "created" DESC);',
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "website_dai_user_id_1d9003_idx";',
        ),
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_dai_goal_ac_39f9cb_idx" '
            'ON "website_dailystatusreport" ("goal_accomplished");',
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "website_dai_goal_ac_39f9cb_idx";',
        ),
        # UserProfile indexes
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_use_leaderb_aa31e8_idx" '
            'ON "website_userprofile" ("leaderboard_score" DESC, "current_streak" DESC);',
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "website_use_leaderb_aa31e8_idx";',
        ),
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_use_team_id_8dcd03_idx" '
            'ON "website_userprofile" ("team_id", "leaderboard_score" DESC);',
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "website_use_team_id_8dcd03_idx";',
        ),
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "website_use_quality_777c8d_idx" '
            'ON "website_userprofile" ("quality_score" DESC);',
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS "website_use_quality_777c8d_idx";',
        ),
    ]
