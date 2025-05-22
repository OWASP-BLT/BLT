from django.test import TestCase
from django.urls import reverse

class HomepageURLTests(TestCase):
    def test_newhome_url_resolves_and_template_used(self):
        """
        Tests that the /newhome URL resolves, returns a 200 status code,
        and uses the newhome.html template.
        """
        response = self.client.get(reverse('newhome'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'newhome.html')

    def test_home_url_resolves_and_template_used(self):
        """
        Tests that the / URL resolves, returns a 200 status code,
        and uses the home.html template.
        """
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
