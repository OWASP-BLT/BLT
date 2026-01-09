from __future__ import division, unicode_literals
from decimal import Decimal

import swapper
from warnings import warn
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Count, Sum
from django.utils.translation import gettext as _
from model_utils.models import TimeStampedModel

from . import app_settings, get_star_ratings_rating_model_name, get_star_ratings_rating_model


def _clean_user(user):
    if not app_settings.STAR_RATINGS_ANONYMOUS:
        if not user:
            raise ValueError(_("User is mandatory. Enable 'STAR_RATINGS_ANONYMOUS' for anonymous ratings."))
        return user
    return None


class RatingManager(models.Manager):
    def for_instance(self, instance):
        if isinstance(instance, self.model):
            raise TypeError("Rating manager 'for_instance' expects model to be rated, not Rating model.")
        ct = ContentType.objects.get_for_model(instance)
        ratings, created = self.get_or_create(content_type=ct, object_id=instance.pk)
        return ratings

    def ratings_for_instance(self, instance):
        warn("RatingManager method 'ratings_for_instance' has been renamed to 'for_instance'. Please change uses of 'Rating.objects.ratings_for_instance' to 'Rating.objects.for_instance' in your code.", DeprecationWarning)
        return self.for_instance(instance)

    def delete_existing(self, existing_rating):
        rating = existing_rating.rating
        existing_rating.delete()
        rating._user_rating_deleted = True
        return rating

    def rate(self, instance, score, user=None, ip=None, clear=False):
        if isinstance(instance, self.model):
            raise TypeError("Rating manager 'rate' expects model to be rated, not Rating model.")
        ct = ContentType.objects.get_for_model(instance)

        user = _clean_user(user)
        existing_rating = UserRating.objects.for_instance_by_user(instance, user)

        if existing_rating:
            if not app_settings.STAR_RATINGS_CLEARABLE and not app_settings.STAR_RATINGS_RERATE:
                raise ValidationError(_('Already rated.'))

            same_as_previous = existing_rating.score == score

            if (app_settings.STAR_RATINGS_CLEARABLE and clear) or \
                    (app_settings.STAR_RATINGS_RERATE_SAME_DELETE and same_as_previous):
                return self.delete_existing(existing_rating=existing_rating)
            elif score is not None:
                existing_rating.score = score
                existing_rating.save()
                return existing_rating.rating
        elif clear:
            # user has cleared without an existing_rating
            return
        else:
            rating, created = self.get_or_create(content_type=ct, object_id=instance.pk)
            return UserRating.objects.create(user=user, score=score, rating=rating, ip=ip).rating


class AbstractBaseRating(models.Model):
    """
    Attaches Rating models and running counts to the model being rated via a generic relation.
    """
    count = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    average = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal(0.0))

    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey()

    objects = RatingManager()

    class Meta:
        unique_together = ['content_type', 'object_id']
        abstract = True

    @property
    def percentage(self):
        return (self.average / app_settings.STAR_RATINGS_RANGE) * 100

    def to_dict(self):
        return {
            'count': self.count,
            'total': self.total,
            'average': self.average,
            'percentage': self.percentage,
        }

    def __str__(self):
        return '{}'.format(self.content_object)

    def calculate(self):
        """
        Recalculate the totals, and save.
        """
        aggregates = self.user_ratings.aggregate(total=Sum('score'), average=Avg('score'), count=Count('score'))
        self.count = aggregates.get('count') or 0
        self.total = aggregates.get('total') or 0
        self.average = aggregates.get('average') or 0.0
        self.save()


class Rating(AbstractBaseRating):
    class Meta(AbstractBaseRating.Meta):
        swappable = swapper.swappable_setting('star_ratings', 'Rating')


class UserRatingManager(models.Manager):
    def for_instance_by_user(self, instance, user=None):
        ct = ContentType.objects.get_for_model(instance)
        user = _clean_user(user)
        if user:
            return self.filter(rating__content_type=ct, rating__object_id=instance.pk, user=user).first()
        else:
            return None

    def has_rated(self, instance, user=None):
        if isinstance(instance, get_star_ratings_rating_model()):
            raise TypeError("UserRating manager 'has_rated' expects model to be rated, not UserRating model.")

        rating = self.for_instance_by_user(instance, user=user)
        return rating is not None

    def bulk_create(self, objs, batch_size=None):
        objs = super(UserRatingManager, self).bulk_create(objs, batch_size=batch_size)
        for rating in set(o.rating for o in objs):
            rating.calculate()
        return objs


class UserRating(TimeStampedModel):
    """
    An individual rating of a user against a model.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(blank=True, null=True)
    score = models.PositiveSmallIntegerField()
    rating = models.ForeignKey(get_star_ratings_rating_model_name(), related_name='user_ratings', on_delete=models.CASCADE)

    objects = UserRatingManager()

    class Meta:
        unique_together = ['user', 'rating']

    def __str__(self):
        if not app_settings.STAR_RATINGS_ANONYMOUS:
            return '{} rating {} for {}'.format(self.user, self.score, self.rating.content_object)
        return '{} rating {} for {}'.format(self.ip, self.score, self.rating.content_object)
