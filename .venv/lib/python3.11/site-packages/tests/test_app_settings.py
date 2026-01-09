from __future__ import unicode_literals

from django.core.checks import Warning
from django.test import override_settings, SimpleTestCase

from hypothesis import given
from hypothesis.extra.django import TestCase
from hypothesis.strategies import integers

from star_ratings import app_settings
from star_ratings.checks import rerate_check


class AppSettingsDefaults(TestCase):
    def test_range_not_defined_in_the_settings___defaults_to_five(self):
        self.assertEqual(5, app_settings.STAR_RATINGS_RANGE)

    @override_settings(STAR_RATINGS_RANGE=10)
    def test_range_defined_in_the_settings___value_is_setting_value(self):
        self.assertEqual(10, app_settings.STAR_RATINGS_RANGE)

    def test_clearable_not_defined_in_the_settings___defaults_to_true(self):
        self.assertFalse(app_settings.STAR_RATINGS_CLEARABLE)

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    def test_clearable_defined_in_the_settings___value_is_setting_value(self):
        self.assertTrue(app_settings.STAR_RATINGS_CLEARABLE)

    def test_rerate_not_defined_in_the_settings___defaults_to_true(self):
        self.assertTrue(app_settings.STAR_RATINGS_RERATE)

    @override_settings(STAR_RATINGS_RERATE=False)
    def test_rerate_defined_in_the_settings___value_is_setting_value(self):
        self.assertFalse(app_settings.STAR_RATINGS_RERATE)

    def test_rerate_same_delete_not_defined_in_the_settings___defaults_to_false(self):
        self.assertFalse(app_settings.STAR_RATINGS_RERATE_SAME_DELETE)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_rerate_same_delete_defined_in_the_settings___value_is_setting_value(self):
        self.assertTrue(app_settings.STAR_RATINGS_RERATE_SAME_DELETE)

    def test_anon_ratings_not_defined_in_settings___defaults_to_false(self):
        self.assertFalse(app_settings.STAR_RATINGS_ANONYMOUS)

    @override_settings(STAR_RATINGS_ANONYMOUS=True)
    def test_anon_ratings_defined_in_the_settings___value_is_setting_value(self):
        self.assertTrue(app_settings.STAR_RATINGS_ANONYMOUS)

    def test_star_height_not_defined_in_settings___defaults_to_32(self):
        self.assertEqual(32, app_settings.STAR_RATINGS_STAR_HEIGHT)

    @given(integers(min_value=1))
    def test_star_height_set_in_the_settings___value_is_setting_value(self, height):
        with override_settings(STAR_RATINGS_STAR_HEIGHT=height):
            self.assertEqual(height, app_settings.STAR_RATINGS_STAR_HEIGHT)

    @given(integers(min_value=1))
    def test_star_width_not_defined_in_settings___defaults_to_star_height(self, height):
        with override_settings(STAR_RATINGS_STAR_HEIGHT=height):
            self.assertEqual(height, app_settings.STAR_RATINGS_STAR_WIDTH)

    @given(integers(min_value=1), integers(min_value=1))
    def test_star_width_defined_in_the_settings___value_is_setting_value(self, height, width):
        with override_settings(STAR_RATINGS_STAR_HEIGHT=height, STAR_RATINGS_STAR_WIDTH=width):
            self.assertEqual(width, app_settings.STAR_RATINGS_STAR_WIDTH)

    def test_object_id_pattern_not_defined_in_the_settings___defaults_to_integers(self):
        self.assertEqual(r'\d+', app_settings.STAR_RATINGS_OBJECT_ID_PATTERN)

    @override_settings(STAR_RATINGS_OBJECT_ID_PATTERN='[a-z0-9]{32}')
    def test_object_id_pattern_defined_in_the_settings___value_is_setting_value(self):
        self.assertEqual('[a-z0-9]{32}', app_settings.STAR_RATINGS_OBJECT_ID_PATTERN)


class AppSettingsChecks(SimpleTestCase):
    @override_settings(STAR_RATINGS_RERATE=True)
    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_rerate_config__correct(self):
        errors = rerate_check(None)
        self.assertEqual(errors, [])

    @override_settings(STAR_RATINGS_RERATE=True)
    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=False)
    def test_rerate_config_deleted_disabled__correct(self):
        errors = rerate_check(None)
        self.assertEqual(errors, [])

    @override_settings(STAR_RATINGS_RERATE=False)
    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_rerate_config_rerate_disabled__not_correct_check_raised(self):
        errors = rerate_check(None)
        expected_errors = [
            Warning(
                'You have specified STAR_RATINGS_RERATE_SAME_DELETE=True and STAR_RATINGS_RERATE=False.',
                hint='If you wish to enable STAR_RATINGS_RERATE_SAME_DELETE please also enable STAR_RATINGS_RERATE.',
                id='star_ratings.W001',
            )
        ]
        self.assertEqual(errors, expected_errors)
