from __future__ import unicode_literals

from hypothesis import given
from hypothesis.extra.django import TestCase
from hypothesis.strategies import text
from random import randint
from django.contrib.auth import get_user_model
from django.test import override_settings
from model_mommy import mommy
from star_ratings import get_star_ratings_rating_model
from star_ratings.models import UserRating

from .base import BaseFooTest


class UserRatingStr(BaseFooTest, TestCase):
    @override_settings(STAR_RATINGS_ANONYMOUS=False)
    def test_anon_is_false___result_contains_user_id_and_rating_name(self):
        user = mommy.make(get_user_model())
        foo = mommy.make(self.foo_model)

        rating = get_star_ratings_rating_model().objects.rate(foo, 1, user, '0.0.0.0')
        user_rating = rating.user_ratings.get(user=user)

        self.assertEqual('{} rating {} for {}'.format(user, user_rating.score, foo), str(user_rating))

    @override_settings(STAR_RATINGS_ANONYMOUS=True)
    def test_anon_is_true___result_contains_ip_and_rating_name(self):
        user = mommy.make(get_user_model())
        foo = mommy.make(self.foo_model)

        rating = get_star_ratings_rating_model().objects.rate(foo, 1, user, '127.0.0.1')
        user_rating = rating.user_ratings.get(ip='127.0.0.1')

        self.assertEqual('{} rating {} for {}'.format('127.0.0.1', user_rating.score, foo), str(user_rating))

    @override_settings(STAR_RATINGS_ANONYMOUS=False)
    @given(text(min_size=1))
    def test_object_name_contains_any_unicode___str_does_not_error(self, name):
        user = mommy.make(get_user_model())
        foo = mommy.make(self.foo_model, name=name)

        rating = get_star_ratings_rating_model().objects.rate(foo, 1, user, '0.0.0.0')
        user_rating = rating.user_ratings.get(user=user)

        try:
            str(user_rating)
        except:  # noqa: E722
            self.fail('"str" raised when it shouldn\'t')


class UserRatingHasRated(BaseFooTest, TestCase):
    def setUp(self):
        super().setUp()
        self.foo = mommy.make(self.foo_model)
        self.bar = mommy.make(self.bar_model)
        self.user_a = mommy.make(get_user_model())
        self.user_b = mommy.make(get_user_model())

    def test_user_has_rated_the_model___results_is_true(self):
        get_star_ratings_rating_model().objects.rate(self.foo, randint(1, 5), self.user_a, '0.0.0.0')

        self.assertTrue(UserRating.objects.has_rated(self.foo, self.user_a))

    def test_different_user_has_rated_the_model___results_is_false(self):
        get_star_ratings_rating_model().objects.rate(self.foo, randint(1, 5), self.user_a, '0.0.0.0')

        self.assertFalse(UserRating.objects.has_rated(self.foo, self.user_b))

    def test_user_has_rated_a_different_model___results_is_false(self):
        get_star_ratings_rating_model().objects.rate(self.foo, randint(1, 5), self.user_a, '0.0.0.0')

        self.assertFalse(UserRating.objects.has_rated(self.bar, self.user_a))

    def test_user_has_rated_a_different_model_instance___results_is_false(self):
        foo2 = mommy.make(self.foo_model)

        get_star_ratings_rating_model().objects.rate(self.foo, randint(1, 5), self.user_a, '0.0.0.0')

        self.assertFalse(UserRating.objects.has_rated(foo2, self.user_a))
