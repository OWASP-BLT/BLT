from __future__ import unicode_literals

from random import randint
from django.contrib.admin import site
from django.test import TestCase
from star_ratings.admin import UserRatingAdmin
from star_ratings.models import UserRating
from .fakes import fake_user_rating


class AdminRatingAdmin(TestCase):
    def test_stars_return_the_correct_html(self):
        score = randint(1, 5)
        rating = fake_user_rating(score=score)

        res = UserRatingAdmin(UserRating, site).stars(rating)

        self.assertHTMLEqual(
            "<span style='display: block; width: {}px; height: 10px; background: url(/static/star-ratings/images/admin_stars.png)'>&nbsp;</span>".format(score * 10),
            res
        )

    def test_allow_tags_is_set_on_stars_method(self):
        self.assertTrue(UserRatingAdmin.stars.allow_tags)

    def test_short_description_is_set_on_stars_method(self):
        self.assertEqual('Score', UserRatingAdmin.stars.short_description)

    def test_list_display_contains_the_correct_columns(self):
        self.assertEqual(('__str__', 'stars'), UserRatingAdmin.list_display)

    def test_rating_is_registered(self):
        self.assertIsInstance(site._registry[UserRating], UserRatingAdmin)
