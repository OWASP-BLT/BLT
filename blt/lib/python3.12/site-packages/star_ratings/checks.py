from django.core.checks import Warning


def rerate_check(app_configs, **kwargs):
    errors = []
    # STAR_RATINGS_RERATE_SAME_DELETE has no impact without STAR_RATINGS_RERATE
    from star_ratings import app_settings
    if app_settings.STAR_RATINGS_RERATE_SAME_DELETE and not app_settings.STAR_RATINGS_RERATE:
        errors.append(
            Warning(
                "You have specified STAR_RATINGS_RERATE_SAME_DELETE=True and STAR_RATINGS_RERATE=False.",
                hint="If you wish to enable STAR_RATINGS_RERATE_SAME_DELETE please also enable STAR_RATINGS_RERATE.",
                id="star_ratings.W001"
            )
        )
    return errors
