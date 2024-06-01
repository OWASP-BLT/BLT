import factory
from factory import fuzzy


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'auth.User'
        django_get_or_create = ('username',)

    username = factory.Faker('user_name')
    email = factory.Faker('email')


class FeedbackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'tellme.Feedback'

    url = factory.Faker('url')
    browser = factory.Faker('user_agent')
    comment = factory.Faker('sentence')
    screenshot = factory.django.ImageField(color='green')

    user = factory.SubFactory(UserFactory)
    email = factory.Faker('email')
    created = factory.Faker('date_time')
