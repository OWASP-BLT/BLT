from __future__ import unicode_literals

from django.conf import settings


class Settings:
    @property
    def STAR_RATINGS_RANGE(self):
        return getattr(settings, 'STAR_RATINGS_RANGE', 5)

    @property
    def STAR_RATINGS_CLEARABLE(self):
        return getattr(settings, 'STAR_RATINGS_CLEARABLE', False)

    @property
    def STAR_RATINGS_ANONYMOUS(self):
        return getattr(settings, 'STAR_RATINGS_ANONYMOUS', False)

    @property
    def STAR_RATINGS_RERATE(self):
        return getattr(settings, 'STAR_RATINGS_RERATE', True)

    @property
    def STAR_RATINGS_RERATE_SAME_DELETE(self):
        return getattr(settings, 'STAR_RATINGS_RERATE_SAME_DELETE', False)

    @property
    def STAR_RATINGS_STAR_HEIGHT(self):
        return getattr(settings, 'STAR_RATINGS_STAR_HEIGHT', 32)

    @property
    def STAR_RATINGS_STAR_WIDTH(self):
        return getattr(settings, 'STAR_RATINGS_STAR_WIDTH', self.STAR_RATINGS_STAR_HEIGHT)

    @property
    def STAR_RATINGS_STAR_SPRITE(self):
        return getattr(settings, 'STAR_RATINGS_STAR_SPRITE', 'star-ratings/images/stars.png')

    @property
    def STAR_RATINGS_OBJECT_ID_PATTERN(self):
        return getattr(settings, 'STAR_RATINGS_OBJECT_ID_PATTERN', r'\d+')
