from __future__ import unicode_literals

from mock import patch
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.test import override_settings
from hypothesis import given, settings
from hypothesis.extra.django import TestCase
from hypothesis.strategies import lists, integers
from model_mommy import mommy
from six import assertRaisesRegex

from .base import BaseFooTest
from .fakes import fake_user
from .strategies import scores
from star_ratings import app_settings, get_star_ratings_rating_model
from star_ratings.models import UserRating
from star_ratings.templatetags.ratings import ratings


class TemplateTagsRatings(BaseFooTest, TestCase):
    @patch('django.template.Template.render')
    def test_item_is_not_yet_rated___rating_object_for_item_is_returned(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        print(context)
        self.assertIsInstance(context['rating'], get_star_ratings_rating_model())
        self.assertEqual(item, context['rating'].content_object)

    @patch('django.template.Template.render')
    def test_item_is_rated___rating_object_for_item_is_returned(self, render_mock):
        item = mommy.make(self.foo_model)

        rating = get_star_ratings_rating_model().objects.for_instance(item)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertEqual(rating, context['rating'])

    @patch('django.template.Template.render')
    def test_request_is_added_to_the_result(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertEqual(request, context['request'])

    @patch('django.template.Template.render')
    def test_request_user_is_added_to_the_result(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertEqual(request.user, context['user'])

    @patch('django.template.Template.render')
    def test_user_is_authenticated_without_rating_for_object___user_rating_is_none(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')

        request.user = get_user_model().objects.create_user(username='user', password='pass')
        self.client.login(username='user', password='pass')

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertIsNone(context['user_rating'])

    @patch('django.template.Template.render')
    def test_user_is_not_authenticated_with_rating_for_object___user_rating_is_none(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = AnonymousUser()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertIsNone(context['user_rating'])

    @patch('django.template.Template.render')
    def test_user_is_authenticated_with_rating_for_object___user_rating_for_user_is_returned(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = get_user_model().objects.create_user(username='user', password='pass')
        self.client.login(username='user', password='pass')

        rating = get_star_ratings_rating_model().objects.rate(item, 3, request.user)
        user_rating = UserRating.objects.get(rating=rating, user=request.user)

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertEqual(user_rating, context['user_rating'])

    @patch('django.template.Template.render')
    def test_user_is_authenticated_without_rating_for_object___user_rating_percentage_is_none(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')

        request.user = get_user_model().objects.create_user(username='user', password='pass')
        self.client.login(username='user', password='pass')

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertIsNone(context['user_rating_percentage'])

    @patch('django.template.Template.render')
    def test_user_is_not_authenticated_with_rating_for_object___user_rating_percentage_is_none(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = AnonymousUser()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertIsNone(context['user_rating_percentage'])

    @patch('django.template.Template.render')
    def test_user_is_authenticated_with_rating_for_object___user_rating_percentage_for_user_is_returned(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = get_user_model().objects.create_user(username='user', password='pass')
        self.client.login(username='user', password='pass')

        rating = get_star_ratings_rating_model().objects.rate(item, 3, request.user)
        user_rating = UserRating.objects.get(rating=rating, user=request.user)

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        expected_avg = 100 * (user_rating.score / Decimal(app_settings.STAR_RATINGS_RANGE))
        self.assertEqual(expected_avg, context['user_rating_percentage'])

    @patch('django.template.Template.render')
    def test_stars_list_is_added_to_the_result(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertEqual(list(range(1, app_settings.STAR_RATINGS_RANGE + 1)), context['stars'])

    @patch('django.template.Template.render')
    def test_star_count_is_added_to_the_result(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertEqual(app_settings.STAR_RATINGS_RANGE, context['star_count'])

    @given(scores=lists(scores()))
    @settings(max_examples=5)
    def test_several_ratings_are_made___percentage_is_correct_in_result(self, scores):
        with patch('django.template.Template.render') as render_mock:
            item = mommy.make(self.foo_model)

            request = RequestFactory().get('/')
            request.user = fake_user()

            for score in scores:
                get_star_ratings_rating_model().objects.rate(item, score, mommy.make(get_user_model()))

            rating = get_star_ratings_rating_model().objects.for_instance(item)

            ratings({
                'request': request,
            }, item)

            context = render_mock.call_args_list[0][0][0]
            expected_avg = 100 * (rating.average / Decimal(app_settings.STAR_RATINGS_RANGE))
            self.assertEqual(expected_avg, context['percentage'])

    @patch('django.template.Template.render')
    def test_icon_height_is_not_set___icon_height_is_32(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertEqual(32, context['icon_height'])

    @given(integers())
    def test_icon_height_is_set___icon_height_is_correct(self, height):
        with patch('django.template.Template.render') as render_mock:
            item = mommy.make(self.foo_model)

            request = RequestFactory().get('/')
            request.user = fake_user()

            ratings({
                'request': request,
            }, item, icon_height=height)

            context = render_mock.call_args_list[0][0][0]
            self.assertEqual(height, context['icon_height'])

    @patch('django.template.Template.render')
    def test_icon_width_is_not_set___icon_height_is_32(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertEqual(32, context['icon_width'])

    @given(integers())
    def test_icon_width_is_set___icon_height_is_correct(self, width):
        with patch('django.template.Template.render') as render_mock:
            item = mommy.make(self.foo_model)

            request = RequestFactory().get('/')
            request.user = fake_user()

            ratings({
                'request': request,
            }, item, icon_width=width)

            context = render_mock.call_args_list[0][0][0]
            self.assertEqual(width, context['icon_width'])

    @patch('django.template.Template.render')
    def test_id_is_a_uid_with_dsr_prefix(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item)

        context = render_mock.call_args_list[0][0][0]
        self.assertTrue(context['id'].startswith('dsr'))
        self.assertIsNotNone(int(context['id'][3:], 16))

    def test_request_is_not_set_in_context___exception_is_raised(self):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        with assertRaisesRegex(self, Exception, 'Make sure you have "django.core.context_processors.request" in your templates context processor list'):
            ratings({}, item)

    @override_settings(STAR_RATINGS_ANONYMOUS=False)
    @patch('django.template.Template.render')
    def test_read_only_is_false_user_is_not_authenticated_anon_rating_is_false___editable_is_false(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = AnonymousUser()

        ratings({
            'request': request,
        }, item, read_only=False)

        context = render_mock.call_args_list[0][0][0]
        self.assertFalse(context['editable'])
        self.assertFalse(context['read_only'])
        self.assertFalse(context['clearable'])

    @override_settings(STAR_RATINGS_ANONYMOUS=False)
    @patch('django.template.Template.render')
    def test_read_only_is_false_user_is_authenticated_anon_rating_is_false___editable_is_true(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item, read_only=False)

        context = render_mock.call_args_list[0][0][0]
        self.assertTrue(context['editable'])
        self.assertFalse(context['read_only'])
        self.assertFalse(context['clearable'])

    @override_settings(STAR_RATINGS_ANONYMOUS=True)
    @patch('django.template.Template.render')
    def test_read_only_is_false_user_is_not_authenticated_anon_rating_is_true___editable_is_true(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = AnonymousUser()

        ratings({
            'request': request,
        }, item, read_only=False)

        context = render_mock.call_args_list[0][0][0]
        self.assertTrue(context['editable'])
        self.assertFalse(context['read_only'])
        self.assertFalse(context['clearable'])

    @patch('django.template.Template.render')
    def test_read_only_is_set_to_true___editable_is_false(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item, read_only=True)

        context = render_mock.call_args_list[0][0][0]
        self.assertFalse(context['editable'])
        self.assertTrue(context['read_only'])
        self.assertFalse(context['clearable'])

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    @patch('django.template.Template.render')
    def test_clearable_is_true__not_readonly__authenticated__clearable(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item, read_only=False)

        context = render_mock.call_args_list[0][0][0]
        self.assertTrue(context['clearable'])

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    @patch('django.template.Template.render')
    def test_clearable_is_true__not_readonly__anon__not_clearable(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = AnonymousUser()

        ratings({
            'request': request,
        }, item, read_only=False)

        context = render_mock.call_args_list[0][0][0]
        self.assertFalse(context['clearable'])

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    @patch('django.template.Template.render')
    def test_clearable_is_true__readonly__authenticated__not_clearable(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item, read_only=True)

        context = render_mock.call_args_list[0][0][0]
        self.assertFalse(context['clearable'])

    @override_settings(STAR_RATINGS_CLEARABLE=False)
    @patch('django.template.Template.render')
    def test_clearable_is_false__not_readonly__authenticated__not_clearable(self, render_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item, read_only=False)

        context = render_mock.call_args_list[0][0][0]
        self.assertFalse(context['clearable'])

    @patch('django.template.loader.get_template')
    def test_template_name_is_set_in_parameter_and_context___parameter_is_used_as_template_name(self, get_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
            'star_ratings_template_name': 'context_template',
        }, item, read_only=True, template_name='parameter_template')

        get_mock.assert_called_once_with('parameter_template')

    @patch('django.template.loader.get_template')
    def test_template_name_is_set_in_context___context_is_used_as_template_name(self, get_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
            'star_ratings_template_name': 'context_template',
        }, item, read_only=True)

        get_mock.assert_called_once_with('context_template')

    @patch('django.template.loader.get_template')
    def test_template_name_is_not_set_in_param_or_context___default_is_used_as_template_name(self, get_mock):
        item = mommy.make(self.foo_model)

        request = RequestFactory().get('/')
        request.user = fake_user()

        ratings({
            'request': request,
        }, item, read_only=True)

        get_mock.assert_called_once_with('star_ratings/widget.html')
