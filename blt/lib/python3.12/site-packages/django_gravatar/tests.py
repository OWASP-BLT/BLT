from django.template import Context, Template
from django.test import TestCase
from django.utils.html import escape

from .compat import parse_qs, quote_plus, urlparse
from .helpers import *


class TestGravatarHelperMethods(TestCase):

    def test_gravatar_hash_generation(self):
        """
        Verify the generation of hash from email string.
        """
        email = "MyEmailAddress@example.com"
        email_hash = "0bc83cb571cd1c50ba6f3e8a78ef1346"

        self.assertEqual(calculate_gravatar_hash(email), email_hash)
        self.assertEqual(calculate_gravatar_hash(email), calculate_gravatar_hash(email.lower()))

    def test_gravatar_url(self):
        """
        Verify that the gravatar_url method returns the expected output.
        """
        email = "joe@example.com"
        email_upper = "JOE@example.com"
        email_strip = "   JOE@example.com "

        # Construct the url
        url = get_gravatar_url(email)

        # Verify email is properly sanitized
        self.assertEqual(url, get_gravatar_url(email_upper))
        self.assertEqual(url, get_gravatar_url(email_strip))

        # Parse query string from url
        urlp = urlparse(url)
        qs = parse_qs(urlp.query)

        # Verify the correct query arguments are included with the proper defaults
        self.assertTrue('s' in qs)
        self.assertTrue('d' in qs)
        self.assertTrue('r' in qs)

        self.assertEqual(qs.get('s').pop(), str(GRAVATAR_DEFAULT_SIZE))
        self.assertEqual(qs.get('d').pop(), GRAVATAR_DEFAULT_IMAGE)
        self.assertEqual(qs.get('r').pop(), GRAVATAR_DEFAULT_RATING)

        # Verify the correct protocol is used
        if GRAVATAR_DEFAULT_SECURE:
            self.assertTrue(GRAVATAR_SECURE_URL in url)
        else:
            self.assertTrue(GRAVATAR_URL in url)

        # Verify that a url value for default is urlencoded
        default_url = 'https://www.example.com/default.jpg'
        url = get_gravatar_url(email, default=default_url)

        # Verify urlencoding
        self.assertTrue(quote_plus(default_url) in url)

    def test_has_gravatar(self):
        """
        Verify that the has_gravatar helper method correctly
        determines if a user has a gravatar or not.
        """
        bad_email = 'eve@example.com'
        good_email = 'matt@automattic.com'

        self.assertFalse(has_gravatar(bad_email))
        self.assertTrue(has_gravatar(good_email))

    def test_gravatar_profile_url(self):
        """
        Verify that the get_gravatar_profile_url helper method correctly
        generates a profile url for gravatar user.
        """
        email = 'joe@example.com'
        profile_url = get_gravatar_profile_url(email)
        email_hash = calculate_gravatar_hash(email)

        self.assertTrue(profile_url.endswith(email_hash))


class TestGravatarTemplateTags(TestCase):
    def test_gravatar_url(self):
        email = 'matt@automattic.com'
        context = Context({'email': email})

        t = Template("{% load gravatar %}{% gravatar_url email %}")
        rendered = t.render(context)

        self.assertEqual(rendered, escape(get_gravatar_url(email)))

    def test_gravatar_img(self):
        # Some defaults for testing
        email = 'matt@automattic.com'
        alt_text = 'some alt text'
        css_class = 'gravatar-thumb'
        size = 250

        # Build context
        context = Context({
            'email': email,
            'size': size,
            'alt_text': alt_text,
            'css_class': css_class,
        })

        # Default behavior
        t = Template("{% load gravatar %}{% gravatar email %}")
        rendered = t.render(context)

        self.assertTrue(escape(get_gravatar_url(email)) in rendered)
        self.assertTrue('class="gravatar"' in rendered)
        self.assertTrue('alt=""' in rendered)

        t = Template("{% load gravatar %}{% gravatar email size alt_text css_class %}")
        rendered = t.render(context)

        self.assertTrue('width="%s"' % (size,) in rendered)
        self.assertTrue('height="%s"' % (size,) in rendered)
        self.assertTrue('alt="%s"' % (alt_text,) in rendered)
        self.assertTrue('class="%s"' % (css_class,) in rendered)

    def test_gravatar_user_url(self):
        # class with email attribute
        class user:
            email = 'bouke@webatoom.nl'

        context = Context({'user': user})

        t = Template("{% load gravatar %}{% gravatar_url user %}")
        rendered = t.render(context)

        self.assertEqual(rendered, escape(get_gravatar_url(user.email)))

    def test_gravatar_user_img(self):
        # class with email attribute
        class user:
            email = 'bouke@webatoom.nl'

        context = Context({'user': user})

        t = Template("{% load gravatar %}{% gravatar user %}")
        rendered = t.render(context)

        self.assertTrue(escape(get_gravatar_url(user.email)) in rendered)

    def test_invalid_input(self):
        context = Context({'email': None})

        t = Template("{% load gravatar %}{% gravatar email %}")
        rendered = t.render(context)

        self.assertEqual("", rendered, "Invalid input should return empty result")

    def test_gravatar_profile_url(self):
        """
        Verify the profile url generated from template gravatar_profile_url tag.
        """
        # class with email attribute
        class user:
            email = 'bouke@webatoom.nl'

        context = Context({'user': user})

        t = Template("{% load gravatar %}{% gravatar_profile_url user %}")
        rendered = t.render(context)

        self.assertEqual(rendered, escape(get_gravatar_profile_url(user.email)))
