from django.test import SimpleTestCase

from website.services.dns_security import _extract_hostname


class DnsSecurityServiceTests(SimpleTestCase):
    def test_extract_hostname_strips_www_prefix(self):
        self.assertEqual(_extract_hostname("https://www.example.com"), "example.com")

    def test_extract_hostname_keeps_non_www_subdomain(self):
        self.assertEqual(_extract_hostname("https://api.example.com"), "api.example.com")

    def test_extract_hostname_handles_plain_domain(self):
        self.assertEqual(_extract_hostname("example.com"), "example.com")
