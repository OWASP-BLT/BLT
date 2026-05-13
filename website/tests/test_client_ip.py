from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from website.utils import get_client_ip


def request_with_meta(remote_addr, forwarded_for=None):
    meta = {"REMOTE_ADDR": remote_addr}
    if forwarded_for is not None:
        meta["HTTP_X_FORWARDED_FOR"] = forwarded_for
    return SimpleNamespace(META=meta)


class ClientIPTests(SimpleTestCase):
    @override_settings(TRUSTED_PROXY_IPS=[], TRUSTED_PROXY_CIDRS=[])
    def test_ignores_x_forwarded_for_from_untrusted_remote(self):
        request = request_with_meta("198.51.100.10", "203.0.113.5")

        self.assertEqual(get_client_ip(request), "198.51.100.10")

    @override_settings(TRUSTED_PROXY_IPS=["198.51.100.10"], TRUSTED_PROXY_CIDRS=[])
    def test_uses_x_forwarded_for_from_trusted_proxy(self):
        request = request_with_meta("198.51.100.10", "203.0.113.5, 198.51.100.10")

        self.assertEqual(get_client_ip(request), "203.0.113.5")

    @override_settings(TRUSTED_PROXY_IPS=[], TRUSTED_PROXY_CIDRS=["198.51.100.0/24"])
    def test_uses_x_forwarded_for_from_trusted_proxy_cidr(self):
        request = request_with_meta("198.51.100.42", "203.0.113.7")

        self.assertEqual(get_client_ip(request), "203.0.113.7")

    @override_settings(TRUSTED_PROXY_IPS=["198.51.100.10"], TRUSTED_PROXY_CIDRS=[])
    def test_invalid_x_forwarded_for_falls_back_to_remote_addr(self):
        request = request_with_meta("198.51.100.10", "not an ip")

        self.assertEqual(get_client_ip(request), "198.51.100.10")
