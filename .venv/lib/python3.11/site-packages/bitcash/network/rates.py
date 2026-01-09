from collections import OrderedDict
from decimal import ROUND_DOWN

import requests
from bitcash.network.http import session
from bitcash.utils import Decimal, time_cache

DEFAULT_CACHE_TIME = 60

# Constant for use in deriving exchange
# rates when given in terms of 1 BCH.
ONE = Decimal(1)

# https://en.bitcoin.it/wiki/Units
SATOSHI = 1
uBCH = 10**2
mBCH = 10**5
BCH = 10**8

SUPPORTED_CURRENCIES = OrderedDict(
    [
        ("satoshi", "Satoshi"),
        ("ubch", "Microbitcoincash"),
        ("mbch", "Millibitcoincash"),
        ("bch", "BitcoinCash"),
        ("usd", "United States Dollar"),
        ("eur", "Eurozone Euro"),
        ("gbp", "Pound Sterling"),
        ("jpy", "Japanese Yen"),
        ("cny", "Chinese Yuan"),
        ("cad", "Canadian Dollar"),
        ("aud", "Australian Dollar"),
        ("nzd", "New Zealand Dollar"),
        ("rub", "Russian Ruble"),
        ("brl", "Brazilian Real"),
        ("chf", "Swiss Franc"),
        ("sek", "Swedish Krona"),
        ("dkk", "Danish Krone"),
        ("isk", "Icelandic Krona"),
        ("pln", "Polish Zloty"),
        ("hkd", "Hong Kong Dollar"),
        ("krw", "South Korean Won"),
        ("sgd", "Singapore Dollar"),
        ("thb", "Thai Baht"),
        ("twd", "New Taiwan Dollar"),
        ("mxn", "Mexican Peso"),
        ("cop", "Colombian Peso"),
        ("ars", "Argentinian Peso"),
        ("cup", "Cuban Peso"),
        ("pen", "Peruvian Sol"),
        ("uyu", "Uruguayan Peso"),
        ("bob", "Bolivian Boliviano"),
        ("dop", "Dominican Peso"),
        ("clp", "Chilean Peso"),
    ]
)

# https://en.wikipedia.org/wiki/ISO_4217
CURRENCY_PRECISION = {
    "satoshi": 0,
    "ubch": 2,
    "mbch": 5,
    "bch": 8,
    "usd": 2,
    "eur": 2,
    "gbp": 2,
    "jpy": 0,
    "cny": 2,
    "cad": 2,
    "aud": 2,
    "nzd": 2,
    "rub": 2,
    "brl": 2,
    "chf": 2,
    "sek": 2,
    "dkk": 2,
    "isk": 2,
    "pln": 2,
    "hkd": 2,
    "krw": 0,
    "sgd": 2,
    "thb": 2,
    "twd": 2,
    "mxn": 2,
    "cop": 0,
    "ars": 2,
    "cup": 2,
    "pen": 2,
    "uyu": 2,
    "bob": 2,
    "dop": 2,
    "clp": 0,
}


def set_rate_cache_time(seconds):
    global DEFAULT_CACHE_TIME
    DEFAULT_CACHE_TIME = seconds


def satoshi_to_satoshi():
    return SATOSHI


def ubch_to_satoshi():
    return uBCH


def mbch_to_satoshi():
    return mBCH


def bch_to_satoshi():
    return BCH


class BitpayRates:
    """
    API Documentation:
    https://bitpay.com/api/rates#rest-api-resources-rates
    """

    SINGLE_RATE = "https://bitpay.com/rates/BCH/"

    @classmethod
    def currency_to_satoshi(cls, currency):
        headers = {"x-accept-version": "2.0.0", "Accept": "application/json"}
        r = session.get(cls.SINGLE_RATE + currency, headers=headers)
        r.raise_for_status()
        rate = r.json()["data"]["rate"]
        return int(ONE / Decimal(rate) * BCH)

    @classmethod
    def usd_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("usd")

    @classmethod
    def eur_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("eur")

    @classmethod
    def gbp_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("gbp")

    @classmethod
    def jpy_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("jpy")

    @classmethod
    def cny_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("cny")

    @classmethod
    def hkd_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("hkd")

    @classmethod
    def cad_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("cad")

    @classmethod
    def aud_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("aud")

    @classmethod
    def nzd_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("nzd")

    @classmethod
    def rub_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("rub")

    @classmethod
    def brl_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("brl")

    @classmethod
    def chf_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("chf")

    @classmethod
    def sek_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("sek")

    @classmethod
    def dkk_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("dkk")

    @classmethod
    def isk_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("isk")

    @classmethod
    def pln_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("pln")

    @classmethod
    def krw_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("krw")

    @classmethod
    def twd_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("twd")

    @classmethod
    def mxn_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("mxn")

    @classmethod
    def ars_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("ars")

    @classmethod
    def cop_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("cop")

    @classmethod
    def cup_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("cup")

    @classmethod
    def pen_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("pen")

    @classmethod
    def uyu_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("uyu")

    @classmethod
    def clp_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("clp")

    @classmethod
    def sgd_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("sgd")

    @classmethod
    def thb_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("thb")

    @classmethod
    def bob_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("bob")

    @classmethod
    def dop_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("dop")


class CoinbaseRates:
    """
    API Documentation:
    https://developers.coinbase.com/api/v2#get-currencies
    """

    SINGLE_RATE = "https://api.coinbase.com/v2/exchange-rates?currency=BCH"

    @classmethod
    def currency_to_satoshi(cls, currency):
        r = session.get(cls.SINGLE_RATE.format(currency))
        r.raise_for_status()
        rate = r.json()["data"]["rates"][currency]
        return int(ONE / Decimal(rate) * BCH)

    @classmethod
    def usd_to_satoshi(cls):  # pragma: no cover
        return cls.currency_to_satoshi("USD")


class RatesAPI:
    """Each method converts exactly 1 unit of the currency to the equivalent
    number of satoshi.
    """

    IGNORED_ERRORS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
        requests.exceptions.Timeout,
    )

    USD_RATES = [BitpayRates.usd_to_satoshi, CoinbaseRates.usd_to_satoshi]
    EUR_RATES = [BitpayRates.eur_to_satoshi]
    GBP_RATES = [BitpayRates.gbp_to_satoshi]
    JPY_RATES = [BitpayRates.jpy_to_satoshi]
    CNY_RATES = [BitpayRates.cny_to_satoshi]
    HKD_RATES = [BitpayRates.hkd_to_satoshi]
    CAD_RATES = [BitpayRates.cad_to_satoshi]
    AUD_RATES = [BitpayRates.aud_to_satoshi]
    NZD_RATES = [BitpayRates.nzd_to_satoshi]
    RUB_RATES = [BitpayRates.rub_to_satoshi]
    BRL_RATES = [BitpayRates.brl_to_satoshi]
    CHF_RATES = [BitpayRates.chf_to_satoshi]
    SEK_RATES = [BitpayRates.sek_to_satoshi]
    DKK_RATES = [BitpayRates.dkk_to_satoshi]
    ISK_RATES = [BitpayRates.isk_to_satoshi]
    PLN_RATES = [BitpayRates.pln_to_satoshi]
    KRW_RATES = [BitpayRates.krw_to_satoshi]
    CLP_RATES = [BitpayRates.clp_to_satoshi]
    SGD_RATES = [BitpayRates.sgd_to_satoshi]
    THB_RATES = [BitpayRates.thb_to_satoshi]
    TWD_RATES = [BitpayRates.twd_to_satoshi]
    MXN_RATES = [BitpayRates.mxn_to_satoshi]
    ARS_RATES = [BitpayRates.ars_to_satoshi]
    COP_RATES = [BitpayRates.cop_to_satoshi]
    CUP_RATES = [BitpayRates.cup_to_satoshi]
    PEN_RATES = [BitpayRates.pen_to_satoshi]
    UYU_RATES = [BitpayRates.uyu_to_satoshi]
    BOB_RATES = [BitpayRates.bob_to_satoshi]
    DOP_RATES = [BitpayRates.dop_to_satoshi]

    @classmethod
    def usd_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.USD_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def eur_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.EUR_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def gbp_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.GBP_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def jpy_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.JPY_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def cny_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.CNY_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def hkd_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.HKD_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def cad_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.CAD_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def aud_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.AUD_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def nzd_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.NZD_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def rub_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.RUB_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def brl_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.BRL_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def chf_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.CHF_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def sek_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.SEK_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def dkk_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.DKK_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def isk_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.ISK_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def pln_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.PLN_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def krw_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.KRW_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def clp_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.CLP_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def sgd_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.SGD_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def thb_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.THB_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def twd_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.TWD_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def mxn_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.MXN_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass
        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def ars_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.ARS_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def cop_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.COP_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def cup_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.CUP_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def pen_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.PEN_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def uyu_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.UYU_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def dop_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.DOP_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")

    @classmethod
    def bob_to_satoshi(cls):  # pragma: no cover
        for api_call in cls.BOB_RATES:
            try:
                return api_call()
            except cls.IGNORED_ERRORS:
                pass

        raise ConnectionError("All APIs are unreachable.")


EXCHANGE_RATES = {
    "satoshi": satoshi_to_satoshi,
    "ubch": ubch_to_satoshi,
    "mbch": mbch_to_satoshi,
    "bch": bch_to_satoshi,
    "usd": RatesAPI.usd_to_satoshi,
    "eur": RatesAPI.eur_to_satoshi,
    "gbp": RatesAPI.gbp_to_satoshi,
    "jpy": RatesAPI.jpy_to_satoshi,
    "cny": RatesAPI.cny_to_satoshi,
    "cad": RatesAPI.cad_to_satoshi,
    "aud": RatesAPI.aud_to_satoshi,
    "nzd": RatesAPI.nzd_to_satoshi,
    "rub": RatesAPI.rub_to_satoshi,
    "brl": RatesAPI.brl_to_satoshi,
    "chf": RatesAPI.chf_to_satoshi,
    "sek": RatesAPI.sek_to_satoshi,
    "dkk": RatesAPI.dkk_to_satoshi,
    "isk": RatesAPI.isk_to_satoshi,
    "pln": RatesAPI.pln_to_satoshi,
    "hkd": RatesAPI.hkd_to_satoshi,
    "krw": RatesAPI.krw_to_satoshi,
    "sgd": RatesAPI.sgd_to_satoshi,
    "thb": RatesAPI.thb_to_satoshi,
    "twd": RatesAPI.twd_to_satoshi,
    "mxn": RatesAPI.mxn_to_satoshi,
    "ars": RatesAPI.ars_to_satoshi,
    "cop": RatesAPI.cop_to_satoshi,
    "cup": RatesAPI.cup_to_satoshi,
    "uyu": RatesAPI.uyu_to_satoshi,
    "bob": RatesAPI.bob_to_satoshi,
    "pen": RatesAPI.pen_to_satoshi,
    "dop": RatesAPI.dop_to_satoshi,
    "clp": RatesAPI.clp_to_satoshi,
}


def currency_to_satoshi(amount, currency):
    """Converts a given amount of currency to the equivalent number of
    satoshi. The amount can be either an int, float, or string as long as
    it is a valid input to :py:class:`decimal.Decimal`.

    :param amount: The quantity of currency.
    :param currency: One of the :ref:`supported currencies`.
    :type currency: ``str``
    :rtype: ``int``
    """
    satoshis = EXCHANGE_RATES[currency]()
    return int(satoshis * Decimal(amount))


@time_cache(max_age=DEFAULT_CACHE_TIME, cache_size=len(EXCHANGE_RATES))
def _currency_to_satoshi_cached(currency):
    return EXCHANGE_RATES[currency]()


def currency_to_satoshi_cached(amount, currency):
    """Converts a given amount of currency to the equivalent number of
    satoshi. The amount can be either an int, float, or string as long as
    it is a valid input to :py:class:`decimal.Decimal`. Results are cached
    using a decorator for 60 seconds by default. See :ref:`cache times`.

    :param amount: The quantity of currency.
    :param currency: One of the :ref:`supported currencies`.
    :type currency: ``str``
    :rtype: ``int``
    """
    satoshis = _currency_to_satoshi_cached(currency)
    return int(satoshis * Decimal(amount))


def satoshi_to_currency(num, currency):
    """Converts a given number of satoshi to another currency as a formatted
    string rounded down to the proper number of decimal places.

    :param num: The number of satoshi.
    :type num: ``int``
    :param currency: One of the :ref:`supported currencies`.
    :type currency: ``str``
    :rtype: ``str``
    """
    return "{:f}".format(
        Decimal(num / Decimal(EXCHANGE_RATES[currency]()))
        .quantize(
            Decimal("0." + "0" * CURRENCY_PRECISION[currency]), rounding=ROUND_DOWN
        )
        .normalize()
    )


def satoshi_to_currency_cached(num, currency):
    """Converts a given number of satoshi to another currency as a formatted
    string rounded down to the proper number of decimal places. Results are
    cached using a decorator for 60 seconds by default. See :ref:`cache times`.

    :param num: The number of satoshi.
    :type num: ``int``
    :param currency: One of the :ref:`supported currencies`.
    :type currency: ``str``
    :rtype: ``str``
    """
    return "{:f}".format(
        Decimal(num / Decimal(currency_to_satoshi_cached(1, currency)))
        .quantize(
            Decimal("0." + "0" * CURRENCY_PRECISION[currency]), rounding=ROUND_DOWN
        )
        .normalize()
    )
