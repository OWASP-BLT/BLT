from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import override_settings
from hypothesis import given, settings
from hypothesis.strategies import lists, tuples
from hypothesis.extra.django import TestCase
from mock import patch
from model_mommy import mommy
from star_ratings import get_star_ratings_rating_model

from .base import BaseFooTest
from .fakes import fake_rating, fake_user, fake_user_rating
from .strategies import scores
from six import assertRaisesRegex


def mean(nums):
    """
    Our own mean function, as Python 2 doesn't include the statistics module.
    """
    return float(sum(nums)) / len(nums)


class RatingManagerForInstance(BaseFooTest, TestCase):
    def test_rating_object_exists_for_model___that_object_is_returned(self):
        item = mommy.make(self.foo_model)
        rating = fake_rating(content_object=item)

        res = get_star_ratings_rating_model().objects.for_instance(item)

        self.assertEqual(rating, res)

    def test_rating_object_does_not_exist_for_model___object_is_created_and_returned(self):
        item = mommy.make(self.foo_model)

        res = get_star_ratings_rating_model().objects.for_instance(item)

        self.assertIsInstance(res, get_star_ratings_rating_model())
        self.assertEqual(item, res.content_object)
        self.assertEqual(0, res.count)
        self.assertEqual(0, res.total)
        self.assertEqual(0, res.average)

    def test_passed_a_rating_instance___type_error_is_raised(self):
        item = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(item)

        with assertRaisesRegex(self, TypeError, "Rating manager 'for_instance' expects model to be rated, not Rating model."):
            get_star_ratings_rating_model().objects.for_instance(ratings)


class RatingManagerRate(BaseFooTest, TestCase):
    def setUp(self):
        super().setUp()
        self.user_a = mommy.make(get_user_model())
        self.user_b = mommy.make(get_user_model())
        self.foo = self.foo_model.objects.create()

    @given(scores())
    def test_user_rates_object___rating_object_is_create(self, score):
        ratings = get_star_ratings_rating_model().objects.rate(self.foo, score, self.user_a, '127.0.0.1')
        rating = ratings.user_ratings.get(user=self.user_a)

        self.assertEqual(score, rating.score)

    @given(lists(scores(), min_size=2))
    @settings(max_examples=5)
    def test_multiple_users_rating_the_object___aggregates_are_updated(self, scores):
        ratings = None
        for score in scores:
            ratings = get_star_ratings_rating_model().objects.rate(self.foo, score, fake_user(), '127.0.0.1')

        self.assertEqual(ratings.count, len(scores))
        self.assertAlmostEqual(ratings.total, sum(scores))
        self.assertAlmostEqual(ratings.average, mean(scores))

    @given(lists(scores(), min_size=2))
    @settings(max_examples=5)
    def test_deleting_the_rating___aggregates_are_updated(self, scores):
        ratings = None
        for score in scores:
            ratings = get_star_ratings_rating_model().objects.rate(self.foo, score, fake_user(), '127.0.0.1')

        removed_score = scores.pop()
        ratings.user_ratings.filter(score=removed_score).first().delete()

        self.assertEqual(ratings.count, len(scores))
        self.assertAlmostEqual(ratings.total, sum(scores))
        self.assertAlmostEqual(ratings.average, mean(scores))

    @override_settings(STAR_RATINGS_RERATE=True)
    @given(tuples(scores(), scores()).filter(lambda x: x[0] != x[1]))
    def test_same_user_rate_twice_rerate_is_true___rating_is_changed(self, scores):
        first, second = scores

        ratings = get_star_ratings_rating_model().objects.rate(self.foo, first, self.user_a, '127.0.0.1')
        self.assertTrue(ratings.user_ratings.filter(user=self.user_a, score=first))
        self.assertEqual(ratings.count, 1)
        self.assertEqual(ratings.total, first)
        self.assertEqual(ratings.average, first)

        ratings = get_star_ratings_rating_model().objects.rate(self.foo, second, self.user_a, '127.0.0.1')
        self.assertTrue(ratings.user_ratings.filter(user=self.user_a, score=second))
        self.assertEqual(ratings.count, 1)
        self.assertEqual(ratings.total, second)
        self.assertEqual(ratings.average, second)

    @override_settings(STAR_RATINGS_RERATE=False)
    def test_same_user_rate_twice_rerate_is_false___validation_error_is_raised(self):
        """
        If re-rating is disabled the rating should not count
        """
        ratings = get_star_ratings_rating_model().objects.rate(self.foo, 4, self.user_a, '127.0.0.1')
        with self.assertRaises(ValidationError):
            ratings = get_star_ratings_rating_model().objects.rate(self.foo, 2, self.user_a, '127.0.0.1')

        self.assertEqual(ratings.count, 1)
        self.assertEqual(ratings.total, 4)
        self.assertEqual(ratings.average, 4)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    @given(tuples(scores(), scores()).filter(lambda x: x[0] != x[1]))
    def test_same_user_rate_twice_rerate_delete_score_diff__rating_is_changed(self, scores):
        first, second = scores

        ratings = get_star_ratings_rating_model().objects.rate(self.foo, first, self.user_a, '127.0.0.1')
        self.assertTrue(ratings.user_ratings.filter(user=self.user_a, score=first))
        self.assertEqual(ratings.count, 1)
        self.assertEqual(ratings.total, first)
        self.assertEqual(ratings.average, first)

        ratings = get_star_ratings_rating_model().objects.rate(self.foo, second, self.user_a, '127.0.0.1')
        self.assertTrue(ratings.user_ratings.filter(user=self.user_a, score=second))
        self.assertEqual(ratings.count, 1)
        self.assertEqual(ratings.total, second)
        self.assertEqual(ratings.average, second)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_same_user_rate_twice_rerate_is_delete_score_same__rating_is_deleted(self):
        """
        If re-rating is disabled the rating should not count
        """
        ratings = get_star_ratings_rating_model().objects.rate(self.foo, 2, self.user_a, '127.0.0.1')
        self.assertEqual(ratings.user_ratings.filter(user=self.user_a).count(), 1)

        ratings = get_star_ratings_rating_model().objects.rate(self.foo, 2, self.user_a, '127.0.0.1')
        self.assertEqual(ratings.user_ratings.filter(user=self.user_a).count(), 0)

        self.assertEqual(ratings.count, 0)
        self.assertEqual(ratings.total, 0)
        self.assertEqual(ratings.average, 0.0)

    @override_settings(STAR_RATINGS_RERATE=False)
    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_same_user_rate_twice_rerate_is_false_and_delete__validation_error_is_raised(self):
        """
        If re-rating is disabled the rating should not count and deleted should have no impact.
        """
        ratings = get_star_ratings_rating_model().objects.rate(self.foo, 2, self.user_a, '127.0.0.1')
        with self.assertRaises(ValidationError):
            ratings = get_star_ratings_rating_model().objects.rate(self.foo, 2, self.user_a, '127.0.0.1')

        self.assertEqual(ratings.count, 1)
        self.assertEqual(ratings.total, 2)
        self.assertEqual(ratings.average, 2)

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    def test_same_user_rate_clearable___rating_is_deleted(self):
        user_rating = fake_user_rating(user=self.user_a, score=1)

        ratings = get_star_ratings_rating_model().objects.rate(user_rating, None, self.user_a, '127.0.0.1', True)

        self.assertIsNone(ratings)
        self.assertEqual(get_star_ratings_rating_model().objects.count(), 1)

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    def test_same_user_rate_clearable___no_rating_to_delete(self):
        ratings = get_star_ratings_rating_model().objects.rate(self.foo, None, self.user_a, '127.0.0.1', True)

        self.assertIsNone(ratings)
        self.assertEqual(get_star_ratings_rating_model().objects.count(), 0)

    @override_settings(STAR_RATINGS_CLEARABLE=False)
    def test_same_user_rate_clearable__disabled___rating_is_not_deleted(self):
        user_rating = fake_user_rating(user=self.user_a, score=1)

        ratings = get_star_ratings_rating_model().objects.rate(user_rating, None, self.user_a, '127.0.0.1', True)

        self.assertIsNone(ratings)  # no action/non is returned
        self.assertEqual(get_star_ratings_rating_model().objects.count(), 1)

    def test_rate_is_passed_a_rating_instance___value_error_is_raised(self):
        ratings = get_star_ratings_rating_model().objects.for_instance(self.foo)

        with assertRaisesRegex(self, TypeError, "Rating manager 'rate' expects model to be rated, not Rating model."):
            get_star_ratings_rating_model().objects.rate(ratings, 2, self.user_a, '127.0.0.1')


class RatingsForInstanceDeprication(BaseFooTest, TestCase):
    def test_ratings_for_instance_is_called___deprication_warning_is_given(self):
        foo = self.foo_model.objects.create()

        with patch('star_ratings.models.warn') as warn_mock:
            get_star_ratings_rating_model().objects.ratings_for_instance(foo)

            warn_mock.assert_called_once_with("RatingManager method 'ratings_for_instance' has been renamed to 'for_instance'. Please change uses of 'Rating.objects.ratings_for_instance' to 'Rating.objects.for_instance' in your code.", DeprecationWarning)

    def test_ratings_for_instance_is_called___for_instance_is_called_with_the_correct_instance(self):
        foo = self.foo_model.objects.create()

        with patch('star_ratings.models.RatingManager.for_instance') as for_instance_mock:
            get_star_ratings_rating_model().objects.ratings_for_instance(foo)

            for_instance_mock.assert_called_once_with(foo)
