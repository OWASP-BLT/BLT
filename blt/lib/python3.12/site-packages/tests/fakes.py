import string
from random import choice

from django.contrib.auth import get_user_model

from star_ratings import get_star_ratings_rating_model
from star_ratings.models import UserRating


def factory(fn, *args, **kwargs):
    quantity = kwargs.pop('_quantity', 1)
    if quantity == 1:
        return fn(*args, **kwargs)
    else:
        return [fn(*args, **kwargs) for i in range(quantity)]


def fake_user(*args, **kwargs):
    # mommy doesnt support related fields in django 2.0
    # return mommy.make(get_user_model(), *args, **kwargs)

    def _fake(*args, **kwargs):
        ks = dict(kwargs)
        ks.setdefault('username', ''.join(choice(string.digits + string.ascii_letters) for i in range(10)))
        return get_user_model().objects.create(*args, **ks)

    return factory(_fake, *args, **kwargs)


def fake_rating(*args, **kwargs):
    # mommy doesnt support related fields in django 2.0
    # return mommy.make(get_star_ratings_rating_model(), *args, **kwargs)

    return factory(get_star_ratings_rating_model().objects.create, *args, **kwargs)


def fake_user_rating(*args, **kwargs):
    # mommy doesnt support related fields in django 2.0
    # return mommy.make(get_star_ratings_rating_model(), *args, **kwargs)

    def _fake(*args, **kwargs):
        ks = dict(kwargs)

        if 'user' not in ks:
            ks['user'] = fake_user()

        if 'rating' not in ks:
            ks['rating'] = fake_rating()

        return UserRating.objects.create(*args, **ks)

    return factory(_fake, *args, **kwargs)
