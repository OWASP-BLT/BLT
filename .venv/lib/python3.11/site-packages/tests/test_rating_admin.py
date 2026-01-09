from __future__ import unicode_literals

from random import random
from django.contrib.admin import site
from django.test import TestCase
from star_ratings.admin import RatingAdmin
from star_ratings import get_star_ratings_rating_model
from .fakes import fake_rating


class AdminRatingAdmin(TestCase):
    def test_stars_return_the_correct_html(self):
        average = 5 * random()
        max_val = 5
        rating = fake_rating(average=average)

        res = RatingAdmin(get_star_ratings_rating_model(), site).stars(rating)

        self.assertHTMLEqual(
            """<div style='position: relative;'>
                <span style='position: absolute; top: 0; left: 0; width: {}px; height: 10px; background: url(/static/star-ratings/images/admin_stars.png) 0px 10px'>&nbsp;</span>
                <span style='position: absolute; top: 0; left: 0; width: {}px; height: 10px; background: url(/static/star-ratings/images/admin_stars.png)'>&nbsp;</span>
            </div>""".format(max_val * 10, average * 10),
            res
        )

    def test_allow_tags_is_set_on_stars_method(self):
        self.assertTrue(RatingAdmin.stars.allow_tags)

    def test_short_description_is_set_on_stars_method(self):
        self.assertEqual('Rating average', RatingAdmin.stars.short_description)

    def test_list_display_contains_the_correct_columns(self):
        self.assertEqual(('__str__', 'stars'), RatingAdmin.list_display)

    def test_rating_is_registered(self):
        self.assertIsInstance(site._registry[get_star_ratings_rating_model()], RatingAdmin)
