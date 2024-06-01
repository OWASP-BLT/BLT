from __future__ import unicode_literals

from hypothesis.strategies import integers
from star_ratings import app_settings


def scores(max_rating=app_settings.STAR_RATINGS_RANGE):
    return integers(min_value=0, max_value=max_rating)
