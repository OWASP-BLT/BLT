import os
import requests

# Import supported endpoint APIs
from bitcash.network.APIs.BitcoinDotComAPI import BitcoinDotComAPI
from bitcash.network.APIs.ChaingraphAPI import ChaingraphAPI
from bitcash.utils import time_cache

# Dictionary of supported endpoint APIs
ENDPOINT_ENV_VARIABLES = {
    "CHAINGRAPH": ChaingraphAPI,
    "BITCOINCOM": BitcoinDotComAPI,
}

# Default API call total time timeout
DEFAULT_TIMEOUT = 5

# Default sanitized endpoint, based on blockheigt, cache timeout
DEFAULT_SANITIZED_ENDPOINTS_CACHE_TIME = 300

BCH_TO_SAT_MULTIPLIER = 100000000

NETWORKS = {"mainnet", "testnet", "regtest"}


def set_service_timeout(seconds):
    global DEFAULT_TIMEOUT
    DEFAULT_TIMEOUT = seconds


def get_endpoints_for(network):
    # For each available interface in 'ENDPOINT_ENV_VARIABLES'
    # this function will check, in order, if any env variables
    # have been set for EITHER:
    # <NAME>_API_<NETWORK>
    # OR
    # <NAME>_API_<NETWORK>_<N>
    # Where 'N' is a number starting at 1 and increasing to
    # however many endpoints you'd like.
    # If neither of these env variables have been set, it returns
    # the instantiated result of <NAME>.get_default_endpoints(network)

    endpoints = []
    for endpoint in ENDPOINT_ENV_VARIABLES.keys():
        if endpoint == "CHAINGRAPH":
            if os.getenv(f"{endpoint}_API".upper()):
                endpoints.append(
                    ENDPOINT_ENV_VARIABLES[endpoint](
                        os.getenv(f"{endpoint}_API".upper()),
                        os.getenv(f"{endpoint}_API_{network}".upper()),
                    )
                )
            elif os.getenv(f"{endpoint}_API_1".upper()):
                counter = 1
                finished = False
                while not finished:
                    next_endpoint = os.getenv(f"{endpoint}_API_{counter}".upper())
                    next_pattern = os.getenv(
                        f"{endpoint}_API_{network}_{counter}".upper()
                    )
                    if next_endpoint:
                        endpoints.append(
                            ENDPOINT_ENV_VARIABLES[endpoint](
                                next_endpoint, next_pattern
                            )
                        )
                        counter += 1
                    else:
                        finished = True
            else:
                defaults_endpoints = ENDPOINT_ENV_VARIABLES[
                    endpoint
                ].get_default_endpoints(network)
                for each in defaults_endpoints:
                    if hasattr(each, "__iter__") and not isinstance(each, str):
                        endpoints.append(ENDPOINT_ENV_VARIABLES[endpoint](*each))
                    else:
                        endpoints.append(ENDPOINT_ENV_VARIABLES[endpoint](each))
        else:
            if os.getenv(f"{endpoint}_API_{network}".upper()):
                endpoints.append(
                    ENDPOINT_ENV_VARIABLES[endpoint](
                        os.getenv(f"{endpoint}_API_{network}".upper())
                    )
                )
            elif os.getenv(f"{endpoint}_API_{network}_1".upper()):
                counter = 1
                finished = False
                while not finished:
                    next_endpoint = os.getenv(
                        f"{endpoint}_API_{network}_{counter}".upper()
                    )
                    if next_endpoint:
                        endpoints.append(
                            ENDPOINT_ENV_VARIABLES[endpoint](next_endpoint)
                        )
                        counter += 1
                    else:
                        finished = True
            else:
                defaults_endpoints = ENDPOINT_ENV_VARIABLES[
                    endpoint
                ].get_default_endpoints(network)
                for each in defaults_endpoints:
                    if hasattr(each, "__iter__") and not isinstance(each, str):
                        endpoints.append(ENDPOINT_ENV_VARIABLES[endpoint](*each))
                    else:
                        endpoints.append(ENDPOINT_ENV_VARIABLES[endpoint](each))

    return tuple(endpoints)


@time_cache(max_age=DEFAULT_SANITIZED_ENDPOINTS_CACHE_TIME, cache_size=len(NETWORKS))
def get_sanitized_endpoints_for(network="mainnet"):
    """Gets endpoints sanitized by their blockheights.
    Solves the problem when an endpoint is stuck on an older block.

    :param network: network in ["mainnet", "testnet", "regtest"].
    """
    endpoints = get_endpoints_for(network)

    endpoints_blockheight = [0 for _ in range(len(endpoints))]

    for i, endpoint in enumerate(endpoints):
        try:
            endpoints_blockheight[i] = endpoint.get_blockheight(timeout=DEFAULT_TIMEOUT)
        except NetworkAPI.IGNORED_ERRORS:  # pragma: no cover
            pass

    if sum(endpoints_blockheight) == 0:
        raise ConnectionError("All APIs are unreachable.")  # pragma: no cover

    # remove unreachable or un-synced endpoints
    highest_blockheight = max(endpoints_blockheight)
    pop_indices = []
    for i in range(len(endpoints)):
        if endpoints_blockheight[i] != highest_blockheight:
            pop_indices.append(i)

    if pop_indices:
        endpoints = list(endpoints)
        for i in sorted(pop_indices, reverse=True):
            endpoints.pop(i)
        endpoints = tuple(endpoints)

    return endpoints


class NetworkAPI:
    IGNORED_ERRORS = (
        requests.exceptions.RequestException,
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.ProxyError,
        requests.exceptions.SSLError,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ReadTimeout,
        requests.exceptions.TooManyRedirects,
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.ContentDecodingError,
        requests.exceptions.StreamConsumedError,
    )

    @classmethod
    def get_balance(cls, address, network="mainnet"):
        """Gets the balance of an address in satoshi.

        :param address: The address in question.
        :type address: ``str``
        :raises ConnectionError: If all API services fail.
        :rtype: ``int``
        """
        for endpoint in get_sanitized_endpoints_for(network):
            try:
                return endpoint.get_balance(address, timeout=DEFAULT_TIMEOUT)
            except cls.IGNORED_ERRORS:  # pragma: no cover
                pass

        raise ConnectionError("All APIs are unreachable.")  # pragma: no cover

    @classmethod
    def get_transactions(cls, address, network="mainnet"):
        """Gets the ID of all transactions related to an address.

        :param address: The address in question.
        :type address: ``str``
        :raises ConnectionError: If all API services fail.
        :rtype: ``list`` of ``str``
        """
        for endpoint in get_sanitized_endpoints_for(network):
            try:
                return endpoint.get_transactions(address, timeout=DEFAULT_TIMEOUT)
            except cls.IGNORED_ERRORS:  # pragma: no cover
                pass

        raise ConnectionError("All APIs are unreachable.")  # pragma: no cover

    @classmethod
    def get_transaction(cls, txid, network="mainnet"):
        """Gets the full transaction details.

        :param txid: The transaction id in question.
        :type txid: ``str``
        :raises ConnectionError: If all API services fail.
        :rtype: ``Transaction``
        """

        for endpoint in get_sanitized_endpoints_for(network):
            try:
                return endpoint.get_transaction(txid, timeout=DEFAULT_TIMEOUT)
            except cls.IGNORED_ERRORS:  # pragma: no cover
                pass

        raise ConnectionError("All APIs are unreachable.")  # pragma: no cover

    @classmethod
    def get_tx_amount(cls, txid, txindex, network="mainnet"):
        """Gets the amount of a given transaction output.

        :param txid: The transaction id in question.
        :type txid: ``str``
        :param txindex: The transaction index in question.
        :type txindex: ``int``
        :raises ConnectionError: If all API services fail.
        :rtype: ``Decimal``
        """

        for endpoint in get_sanitized_endpoints_for(network):
            try:
                return endpoint.get_tx_amount(txid, txindex, timeout=DEFAULT_TIMEOUT)
            except cls.IGNORED_ERRORS:  # pragma: no cover
                pass

        raise ConnectionError("All APIs are unreachable.")  # pragma: no cover

    @classmethod
    def get_unspent(cls, address, network="mainnet"):
        """Gets all unspent transaction outputs belonging to an address.

        :param address: The address in question.
        :type address: ``str``
        :raises ConnectionError: If all API services fail.
        :rtype: ``list`` of :class:`~bitcash.network.meta.Unspent`
        """

        for endpoint in get_sanitized_endpoints_for(network):
            try:
                return endpoint.get_unspent(address, timeout=DEFAULT_TIMEOUT)
            except cls.IGNORED_ERRORS:  # pragma: no cover
                pass

        raise ConnectionError("All APIs are unreachable.")  # pragma: no cover

    @classmethod
    def get_raw_transaction(cls, txid, network="mainnet"):
        """Gets the raw, unparsed transaction details.

        :param txid: The transaction id in question.
        :type txid: ``str``
        :raises ConnectionError: If all API services fail.
        :rtype: ``Transaction``
        """

        for endpoint in get_sanitized_endpoints_for(network):
            try:
                return endpoint.get_raw_transaction(txid, timeout=DEFAULT_TIMEOUT)
            except cls.IGNORED_ERRORS:  # pragma: no cover
                pass

        raise ConnectionError("All APIs are unreachable.")  # pragma: no cover

    @classmethod
    def broadcast_tx(cls, tx_hex, network="mainnet"):  # pragma: no cover
        """Broadcasts a transaction to the blockchain.

        :param tx_hex: A signed transaction in hex form.
        :type tx_hex: ``str``
        :raises ConnectionError: If all API services fail.
        """
        success = None

        for endpoint in get_sanitized_endpoints_for(network):
            _ = [end[0] for end in ChaingraphAPI.get_default_endpoints(network)]
            if endpoint in _ and network == "mainnet":
                # Default chaingraph endpoints do not indicate failed broadcast
                # no other testnet api
                continue
            try:
                success = endpoint.broadcast_tx(tx_hex, timeout=DEFAULT_TIMEOUT)
                if not success:
                    continue
                return
            except cls.IGNORED_ERRORS:
                pass

        if not success:
            raise ConnectionError(
                "Transaction broadcast failed, or Unspents were already used."
            )

        raise ConnectionError("All APIs are unreachable.")
