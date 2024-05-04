from __future__ import unicode_literals

import json
import os
import uuid

import pytest
from random import randint
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from .base import BaseFooTest

try:
    from django.core.urlresolvers import reverse
except ImportError:
    from django.urls import reverse

from django.test import override_settings, Client, TestCase
from model_mommy import mommy
from star_ratings import get_star_ratings_rating_model
from star_ratings.models import UserRating


class BaseTestViewRate:
    csrf_checks = False
    client = Client(REMOTE_ADDR='127.0.0.1')

    def post_json(self, url, data, **kwargs):
        if 'user' in kwargs:
            self.client.login(username=kwargs['user'].username, password='password')
        if 'xhr' in kwargs:
            return self.client.post(url, json.dumps(data), content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        return self.client.post(url, data)

    def get_user(self, username='username'):
        return get_user_model().objects.create_user(
            username=username,
            first_name='first',
            last_name='last',
            email='example@example.com',
            password='password'
        )

    @override_settings(STAR_RATINGS_ANONYMOUS=False)
    def test_view_is_called_when_nobody_is_logged_in_and_anon_ratings_is_false___user_is_forwarded_to_login(self):
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)

        url = self.get_url(obj=ratings)
        response = self.post_json(url, {'score': 1})

        self.assertRedirects(response, settings.LOGIN_URL + '?next=' + url, fetch_redirect_response=False)

    @override_settings(STAR_RATINGS_ANONYMOUS=True)
    def test_view_is_called_when_nobody_is_logged_in_and_anon_ratings_is_true___rating_is_created(self):
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)

        score = randint(1, 5)

        url = self.get_url(obj=ratings)
        self.post_json(url, {'score': score})

        ct = ContentType.objects.get_for_model(foo)

        self.assertTrue(UserRating.objects.filter(rating__object_id=foo.pk, rating__content_type=ct, score=score, ip='127.0.0.1').exists())

    def test_user_is_logged_in_and_doesnt_already_have_a_rating___rating_is_created(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)

        score = randint(1, 5)

        url = self.get_url(obj=ratings)
        self.post_json(url, {'score': score}, user=user)

        ct = ContentType.objects.get_for_model(foo)

        self.assertTrue(UserRating.objects.filter(user=user, rating__object_id=foo.pk, rating__content_type=ct, score=score).exists())

    def test_user_is_logged_in_and_doesnt_already_have_a_rating_no_next_url_is_given___redirected_to_root(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)

        score = randint(1, 5)

        url = self.get_url(obj=ratings)
        response = self.post_json(url, {'score': score}, user=user)

        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_user_is_logged_in_and_doesnt_already_have_a_rating_next_url_is_given___redirected_to_next(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)

        score = randint(1, 5)

        url = self.get_url(obj=ratings)
        response = self.post_json(url, {'score': score, 'next': '/foo/bar'}, user=user)

        self.assertRedirects(response, '/foo/bar', fetch_redirect_response=False)

    def test_user_is_logged_in_and_doesnt_already_have_a_rating_request_is_ajax___rating_is_created(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)

        score = randint(1, 5)

        url = self.get_url(obj=ratings)

        self.post_json(url, {'score': score}, user=user, xhr=True)

        ct = ContentType.objects.get_for_model(foo)

        self.assertTrue(UserRating.objects.filter(user=user, rating__object_id=foo.pk, rating__content_type=ct, score=score).exists())

    def test_user_is_logged_in_and_doesnt_already_have_a_rating_request_is_ajax___response_is_updated_aggregate_data(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)

        score = randint(1, 5)

        url = self.get_url(obj=ratings)

        response = self.post_json(
            url, {'score': score}, user=user, xhr=True)

        ratings = get_star_ratings_rating_model().objects.get(pk=ratings.pk)
        expected = ratings.to_dict()
        expected['user_rating'] = score
        expected['percentage'] = float(expected['percentage'])

        try:
            json_resp = response.json()
        except AttributeError:
            json_resp = json.loads(response.content.decode())

        self.assertEqual(expected, json_resp)

    @override_settings(STAR_RATINGS_RERATE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_true___rating_is_updated(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = self.get_url(obj=ratings)
        self.post_json(url, {'score': score}, user=user)

        rating = UserRating.objects.get(pk=rating.pk)

        self.assertEqual(score, rating.score)

    @override_settings(STAR_RATINGS_RERATE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_true___redirected_to_root(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = self.get_url(obj=ratings)
        response = self.post_json(url, {'score': score}, user=user)

        self.assertRedirects(response, '/', fetch_redirect_response=False)

    @override_settings(STAR_RATINGS_RERATE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_true___redirected_to_next(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = self.get_url(obj=ratings)
        response = self.post_json(url, {'score': score, 'next': '/foo/bar'}, user=user)

        self.assertRedirects(response, '/foo/bar', fetch_redirect_response=False)

    @override_settings(STAR_RATINGS_RERATE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_true_request_is_ajax___rating_is_updated(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = self.get_url(obj=ratings)
        self.post_json(url, {'score': score}, user=user, xhr=True)

        rating = UserRating.objects.get(pk=rating.pk)

        self.assertEqual(score, rating.score)

    @override_settings(STAR_RATINGS_RERATE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_true_request_is_ajax___response_is_updated_aggregate_data(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = self.get_url(obj=ratings)

        response = self.post_json(url, {'score': score}, user=user, xhr=True)
        ratings = get_star_ratings_rating_model().objects.get(pk=ratings.pk)
        expected = ratings.to_dict()
        expected['percentage'] = float(expected['percentage'])
        expected['user_rating'] = score

        try:
            json_resp = response.json()
        except AttributeError:
            json_resp = json.loads(response.content.decode())

        self.assertEqual(expected, json_resp)

    @override_settings(STAR_RATINGS_RERATE=False)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_false___rating_is_not_changed(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)

        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)
        orig_score = rating.score

        score = randint(2, 5)

        url = self.get_url(obj=ratings)
        self.post_json(url, {'score': score}, user=user)

        rating = UserRating.objects.get(pk=rating.pk)

        self.assertEqual(orig_score, rating.score)

    @override_settings(STAR_RATINGS_RERATE=False)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_false___redirected_to_next(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = self.get_url(obj=ratings)
        response = self.post_json(url, {'score': score, 'next': '/foo/bar'}, user=user)

        self.assertRedirects(response, '/foo/bar', fetch_redirect_response=False)

    @override_settings(STAR_RATINGS_RERATE=False)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_false_request_is_ajax___rating_is_not_changed(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)
        orig_score = rating.score

        score = randint(2, 5)

        url = self.get_url(obj=ratings)
        self.post_json(url, {'score': score}, user=user, xhr=True, expect_errors=True)

        rating = UserRating.objects.get(pk=rating.pk)
        self.assertEqual(orig_score, rating.score)

    @override_settings(STAR_RATINGS_RERATE=False)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_false_reqest_is_ajax___response_is_400(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = self.get_url(obj=ratings, extra='?next=/foo/bar')
        response = self.post_json(url, {'score': score}, user=user, xhr=True, expect_errors=True)

        self.assertEqual(400, response.status_code)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_score_same__rating_deleted(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)
        orig_score = rating.score

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        self.post_json(url, {'score': orig_score}, user=user)

        with self.assertRaises(UserRating.DoesNotExist):
            UserRating.objects.get(pk=rating.pk)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_score_same__redirected_to_next(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        response = self.post_json(url, {'score': rating.score, 'next': '/foo/bar'}, user=user)

        self.assertRedirects(response, '/foo/bar', fetch_redirect_response=False)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_request_is_ajax_score_same__rating_deleted(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)
        orig_score = rating.score

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        self.post_json(url, {'score': orig_score}, user=user, xhr=True, expect_errors=True)

        with self.assertRaises(UserRating.DoesNotExist):
            UserRating.objects.get(pk=rating.pk)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_reqest_is_ajax_score_same__response_is_200(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id)) + '?next=/foo/bar'
        response = self.post_json(url, {'score': rating.score}, user=user, xhr=True, expect_errors=True)

        self.assertEqual(200, response.status_code)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_reqest_is_ajax_score_same__response_empty(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        # expecting it to be removed
        expected = {'average': 0.0, 'count': 0, 'percentage': 0.0, 'total': 0, 'user_rating': None}

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id)) + '?next=/foo/bar'
        response = self.post_json(url, {'score': rating.score}, user=user, xhr=True, expect_errors=True)

        try:
            json_resp = response.json()
        except AttributeError:
            json_resp = json.loads(response.content.decode())

        self.assertEqual(expected, json_resp)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_reqest_is_ajax_score_same__response_updated(self):
        user = self.get_user()
        other_user = self.get_user(username='other')
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)
        mommy.make(UserRating, rating=ratings, score=2, user=other_user)

        # expecting it to be removed
        expected = {'average': 2.0, 'count': 1, 'percentage': 40.0, 'total': 2, 'user_rating': None}

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id)) + '?next=/foo/bar'
        response = self.post_json(url, {'score': rating.score}, user=user, xhr=True, expect_errors=True)

        try:
            json_resp = response.json()
        except AttributeError:
            json_resp = json.loads(response.content.decode())

        self.assertEqual(expected, json_resp)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_score_diff__ratingchanged(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        self.post_json(url, {'score': score}, user=user)

        rating = UserRating.objects.get(pk=rating.pk)

        self.assertEqual(score, rating.score)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_score_diff__redirected_to_next(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        response = self.post_json(url, {'score': score, 'next': '/foo/bar'}, user=user)

        self.assertRedirects(response, '/foo/bar', fetch_redirect_response=False)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_score_diff__rating_changed(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        self.post_json(url, {'score': score}, user=user, xhr=True, expect_errors=True)

        rating = UserRating.objects.get(pk=rating.pk)
        self.assertEqual(score, rating.score)

    @override_settings(STAR_RATINGS_RERATE_SAME_DELETE=True)
    def test_user_is_logged_in_already_has_a_rating_rerate_is_delete_score_diff__response_is_200(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        score = randint(2, 5)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id)) + '?next=/foo/bar'
        response = self.post_json(url, {'score': score}, user=user, xhr=True, expect_errors=True)

        self.assertEqual(200, response.status_code)

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    def test_user_is_logged_in_already_has_a_rating__clearable__rating_deleted(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        self.post_json(url, {'clear': 1}, user=user)

        with self.assertRaises(UserRating.DoesNotExist):
            UserRating.objects.get(pk=rating.pk)

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    def test_user_is_logged_in_already_has_a_rating__clearable__redirected_to_next(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        response = self.post_json(url, {'clear': 1, 'next': '/foo/bar'}, user=user)

        self.assertRedirects(response, '/foo/bar', fetch_redirect_response=False)

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    def test_user_is_logged_in_already_has_a_rating__clearable__request_is_ajax__rating_deleted(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        self.post_json(url, {'clear': 1}, user=user, xhr=True, expect_errors=True)

        with self.assertRaises(UserRating.DoesNotExist):
            UserRating.objects.get(pk=rating.pk)

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    def test_user_is_logged_in_already_has_a_rating__clearable_request_is_ajax__response_is_200(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id)) + '?next=/foo/bar'
        response = self.post_json(url, {'clear': 1}, user=user, xhr=True, expect_errors=True)

        self.assertEqual(200, response.status_code)

    @override_settings(STAR_RATINGS_CLEARABLE=True)
    def test_user_is_logged_in_already_has_a_rating__clearable_request_is_ajax__response_empty(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        mommy.make(UserRating, rating=ratings, score=1, user=user)

        # expecting it to be removed
        expected = {'average': 0.0, 'count': 0, 'percentage': 0.0, 'total': 0, 'user_rating': None}

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id)) + '?next=/foo/bar'
        response = self.post_json(url, {'clear': 1}, user=user, xhr=True, expect_errors=True)

        try:
            json_resp = response.json()
        except AttributeError:
            json_resp = json.loads(response.content.decode())

        self.assertEqual(expected, json_resp)

    @override_settings(STAR_RATINGS_CLEARABLE=False)
    def test_user_is_logged_in_already_has_a_rating__clearable__disabled__rating_not_deleted(self):
        user = self.get_user()
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        rating = mommy.make(UserRating, rating=ratings, score=1, user=user)

        url = reverse('ratings:rate', args=(ratings.content_type_id, ratings.object_id))
        self.post_json(url, {'clear': 1}, user=user)

        self.assertEqual(UserRating.objects.filter(pk=rating.pk).count(), 1)


@pytest.mark.skipif(os.environ.get('USE_CUSTOM_MODEL', 'false') == 'true', reason='Only run without swapped model.')
@pytest.mark.django_db
class TestViewRateWithStandardURLPattern(BaseTestViewRate, BaseFooTest, TestCase):
    """
        Run TestViewRate with standard URL/no model change.
    """
    def setUp(self):
        super().setUp()
        self.foo_model = self.foo_model

    @staticmethod
    def get_url(obj, extra=''):
        return reverse('ratings:rate', args=(obj.content_type_id, obj.object_id)) + extra

    def test_url__correct(self):
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        self.assertIsInstance(ratings.object_id, int)
        self.assertEqual(
            self.get_url(ratings),
            '/ratings/{}/{}/'.format(ratings.content_type_id, ratings.object_id)
        )

    def test_url_with_extra__correct(self):
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        self.assertIsInstance(ratings.object_id, int)
        self.assertEqual(
            self.get_url(ratings, extra='?123'),
            '/ratings/{}/{}/?123'.format(ratings.content_type_id, ratings.object_id)
        )


@pytest.mark.skipif(os.environ.get('USE_CUSTOM_MODEL', 'false') == 'false', reason='Only run when with swapped model.')
@pytest.mark.django_db
@override_settings(STAR_RATINGS_OBJECT_ID_PATTERN='[0-9a-f-]+')
class TestViewRateWithCustomURLPattern(BaseTestViewRate, BaseFooTest, TestCase):
    """
        Run TestViewRate with swapped URL/model change.

        Handles the change in URL.
    """
    @staticmethod
    def get_url(obj, extra=''):
        return reverse('ratings:rate', args=(obj.content_type_id, str(obj.object_id))) + extra

    def test_url__correct(self):
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        self.assertIsInstance(ratings.object_id, uuid.UUID)
        self.assertEqual(
            self.get_url(ratings),
            '/ratings/{}/{}/'.format(ratings.content_type_id, ratings.object_id)
        )

    def test_url_with_extra__correct(self):
        foo = mommy.make(self.foo_model)
        ratings = get_star_ratings_rating_model().objects.for_instance(foo)
        self.assertIsInstance(ratings.object_id, uuid.UUID)
        self.assertEqual(
            self.get_url(ratings, extra='?123'),
            '/ratings/{}/{}/?123'.format(ratings.content_type_id, ratings.object_id)
        )
