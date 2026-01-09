from time import sleep, time

from _pytest.monkeypatch import MonkeyPatch
import bitcash
from bitcash.network import rates as _rates
from bitcash.network.rates import (
    RatesAPI,
    bch_to_satoshi,
    currency_to_satoshi,
    currency_to_satoshi_cached,
    EXCHANGE_RATES,
    mbch_to_satoshi,
    satoshi_to_currency,
    satoshi_to_currency_cached,
    satoshi_to_satoshi,
    set_rate_cache_time,
    ubch_to_satoshi,
)
from bitcash.utils import Decimal


def test_set_rate_cache_time():
    original = bitcash.network.rates.DEFAULT_CACHE_TIME
    set_rate_cache_time(30)
    updated = bitcash.network.rates.DEFAULT_CACHE_TIME

    assert original != updated
    assert updated == 30

    set_rate_cache_time(original)


def test_satoshi_to_satoshi():
    s = satoshi_to_satoshi()
    assert isinstance(s, int)
    assert s == 1


def test_ubch_to_satoshi():
    s = ubch_to_satoshi()
    assert isinstance(s, int)
    assert s == 100


def test_mbch_to_satoshi():
    s = mbch_to_satoshi()
    assert isinstance(s, int)
    assert s == 100000


def test_bch_to_satoshi():
    s = bch_to_satoshi()
    assert isinstance(s, int)
    assert s == 100000000


def test_currency_to_satoshi():
    assert currency_to_satoshi(1, "usd") > currency_to_satoshi(1, "jpy")


class TestSatoshiToCurrency:
    def test_no_exponent(self):
        assert satoshi_to_currency(1, "bch") == "0.00000001"

    def test_zero_places(self):
        assert Decimal(satoshi_to_currency(100000, "jpy")).as_tuple().exponent == 0


def test_satoshi_to_currency_cached():
    assert satoshi_to_currency_cached(1, "ubch") == "0.01"


def test_rates_close():
    rates = sorted([api_call() for api_call in RatesAPI.USD_RATES])
    # Making sure the rates are less than 10% different
    assert rates[-1] / rates[0] < 1.1 and rates[-1] / rates[0] > 0.9


def _dummy_usd_to_satoshi():
    sleep(1)
    return 1


DUMMY_EXCHANGE_RATES = {"usd": _dummy_usd_to_satoshi}


class TestRateCache:
    def setup_method(self):
        self.monkeypatch = MonkeyPatch()

    def test_cache(self):
        self.monkeypatch.setattr(_rates, "EXCHANGE_RATES", DUMMY_EXCHANGE_RATES)
        start_time = time()
        currency_to_satoshi_cached(1, "usd")
        initial_time = time() - start_time

        start_time = time()
        currency_to_satoshi_cached(2, "usd")
        cached_time = time() - start_time

        assert initial_time > cached_time
        self.monkeypatch.setattr(_rates, "EXCHANGE_RATES", EXCHANGE_RATES)

    def test_expires(self):
        self.monkeypatch.setattr(_rates, "EXCHANGE_RATES", DUMMY_EXCHANGE_RATES)
        set_rate_cache_time(1.2)
        currency_to_satoshi_cached(1, "usd")

        start_time = time()
        currency_to_satoshi_cached(2, "usd")
        cached_time = time() - start_time

        sleep(0.2)

        start_time = time()
        currency_to_satoshi_cached(3, "usd")
        update_time = time() - start_time

        assert update_time > cached_time
        self.monkeypatch.setattr(_rates, "EXCHANGE_RATES", EXCHANGE_RATES)
