from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from model_mommy import mommy

from star_ratings import get_star_ratings_rating_model
from star_ratings.models import UserRating
from six import assertRaisesRegex

from .base import BaseFooTest


class RatingManagerHasRated(BaseFooTest, TestCase):
    def test_has_rate_is_passed_a_rating_instance___type_error_is_raised(self):
        user = mommy.make(get_user_model())
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)

        with assertRaisesRegex(self, TypeError, "UserRating manager 'has_rated' expects model to be rated, not UserRating model."):
            UserRating.objects.has_rated(ratings, user)


class ForInstanceByUser(BaseFooTest, TestCase):
    @override_settings(STAR_RATINGS_ANONYMOUS=False)
    def test_anon_ratings_is_false_user_not_set___value_error_is_raised(self):
        foo = mommy.make(self.foo_model)

        with assertRaisesRegex(self, ValueError, "User is mandatory. Enable 'STAR_RATINGS_ANONYMOUS' for anonymous ratings."):
            UserRating.objects.for_instance_by_user(foo)

    @override_settings(STAR_RATINGS_ANONYMOUS=True)
    def test_anon_ratings_is_true___none_is_returned(self):
        foo = mommy.make(self.foo_model)

        get_star_ratings_rating_model().objects.rate(foo, 1, ip='127.0.0.1')
        get_star_ratings_rating_model().objects.rate(foo, 1, ip='127.0.0.1')

        self.assertIsNone(
            UserRating.objects.for_instance_by_user(foo),
        )

    def test_user_is_set___rating_object_for_is_returned(self):
        foo = mommy.make(self.foo_model)
        user = mommy.make(get_user_model())

        get_star_ratings_rating_model().objects.rate(foo, 1, user=mommy.make(get_user_model()))
        expected = get_star_ratings_rating_model().objects.rate(foo, 1, user=user).user_ratings.get(user=user)

        self.assertEqual(
            expected,
            UserRating.objects.for_instance_by_user(foo, user=user),
        )


class BulkCreate(BaseFooTest, TestCase):
    def test_correct_number_of_(self):
        foo = mommy.make(self.foo_model, name='name')
        rating = get_star_ratings_rating_model().objects.for_instance(foo)
        user_a, user_b = mommy.make(get_user_model(), _quantity=2)

        data = [
            UserRating(user=user_a, ip='127.0.0.1', score=3, rating=rating),
            UserRating(user=user_b, ip='127.0.0.2', score=3, rating=rating),
        ]

        UserRating.objects.bulk_create(data)
        self.assertEqual(UserRating.objects.count(), 2)

    def test_multiple_user_ratings_are_created_for_multiple_ratings___calculateion_are_updated_correctly(self):
        foo, bar = mommy.make(self.foo_model, name='name', _quantity=2)

        foo_rating = get_star_ratings_rating_model().objects.for_instance(foo)
        bar_rating = get_star_ratings_rating_model().objects.for_instance(bar)

        user_a, user_b, user_c = mommy.make(get_user_model(), _quantity=3)

        data = [
            UserRating(user=user_a, ip='127.0.0.1', score=1, rating=foo_rating),
            UserRating(user=user_b, ip='127.0.0.2', score=3, rating=foo_rating),
            UserRating(user=user_a, ip='127.0.0.1', score=1, rating=bar_rating),
            UserRating(user=user_b, ip='127.0.0.2', score=3, rating=bar_rating),
            UserRating(user=user_c, ip='127.0.0.2', score=5, rating=bar_rating),
        ]

        UserRating.objects.bulk_create(data)

        foo_rating = get_star_ratings_rating_model().objects.get(pk=foo_rating.pk)
        self.assertEqual(2, foo_rating.count)
        self.assertEqual(4, foo_rating.total)
        self.assertEqual(2, foo_rating.average)

        bar_rating = get_star_ratings_rating_model().objects.get(pk=bar_rating.pk)
        self.assertEqual(3, bar_rating.count)
        self.assertEqual(9, bar_rating.total)
        self.assertEqual(3, bar_rating.average)
