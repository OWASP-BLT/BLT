import os
import time

import pytest
import bitcash
from _pytest.monkeypatch import MonkeyPatch
from bitcash.exceptions import InvalidEndpointURLProvided
from bitcash.network import services as _services
from bitcash.network.meta import Unspent
from bitcash.network.services import (
    BitcoinDotComAPI,
    ChaingraphAPI,
    NetworkAPI,
    get_endpoints_for,
    get_sanitized_endpoints_for,
    set_service_timeout,
)
from bitcash.network.transaction import Transaction
from tests.samples import VALID_ENDPOINT_URLS, INVALID_ENDPOINT_URLS
from tests.utils import (
    catch_errors_raise_warnings,
    decorate_methods,
    raise_connection_error,
)

MAIN_ADDRESS_USED1 = "bitcoincash:qrg2nw20kxhspdlec82qxrgdegrq23hyuyjx2h29sy"
MAIN_ADDRESS_USED2 = "bitcoincash:qpr270a5sxphltdmggtj07v4nskn9gmg9yx4m5h7s4"
MAIN_ADDRESS_UNUSED = "bitcoincash:qzxumj0tjwwrep698rv4mnwa5ek3ddsgxuvcunqnjx"
MAIN_TX = "9bccb8d6adf53ca49cea02118871e29d3b4e5cb157dc3a475dd364e30fb20993"
MAIN_TX2 = "10961ec0534bd9751371bfbab4af57cf3a6c7410df9c71c51665c75fca92f33c"
TEST_ADDRESS_USED1 = "bchtest:qrnuzdzleru8c6qhpva20x9f2mp0u657luhfyxjep5"
TEST_ADDRESS_USED2 = "bchtest:qprralpnpx6zrx3w2aet97u0c6rcfrlp8v6jenepj5"
TEST_ADDRESS_USED3 = "bchtest:qpjm4n7m4r6aufkxxy5nqm5letejdm4f5sn6an6rsl"
TEST_ADDRESS_UNUSED = "bchtest:qpwn6qz29s5rv2uf0cxd7ygnwdttsuschczaz38yc5"
TEST_TX = "09d0c9773c56fac218ae084226e9db8480d9b5c6f60cc0466431d6820d344adc"
TEST_TX2 = "3c26deab2df023a8dbee15bf47701332f6661323ea117a58362b0ea9605129fd"


def test_set_service_timeout():
    original = bitcash.network.services.DEFAULT_TIMEOUT
    set_service_timeout(3)
    updated = bitcash.network.services.DEFAULT_TIMEOUT

    assert original != updated
    assert updated == 3

    set_service_timeout(original)


class MockBackend(NetworkAPI):
    IGNORED_ERRORS = NetworkAPI.IGNORED_ERRORS

    @classmethod
    def get_balance(cls, *args, **kwargs):
        raise_connection_error()

    @classmethod
    def get_transactions(cls, *args, **kwargs):
        raise_connection_error()

    @classmethod
    def get_transaction(cls, *args, **kwargs):
        raise_connection_error()

    @classmethod
    def get_unspent(cls, *args, **kwargs):
        raise_connection_error()

    @classmethod
    def get_tx_amount(cls, *args, **kwargs):
        raise_connection_error()

    @classmethod
    def get_raw_transaction(cls, *args, **kwargs):
        raise_connection_error()


class MockEndpoint:
    def __init__(self, blockheight):
        self.blockheight = blockheight

    def get_blockheight(self, *args, **kwargs):
        if self.blockheight < 0:
            raise NetworkAPI.IGNORED_ERRORS[0]
        return self.blockheight


def mock_get_endpoints_for(network):
    return (
        MockEndpoint(4),
        MockEndpoint(-1),
        MockEndpoint(0),
        MockEndpoint(4),
        MockEndpoint(4),
        MockEndpoint(4),
        MockEndpoint(3),
    )


def test_get_ordered_endpoints_for():
    monkeypatch = MonkeyPatch()
    monkeypatch.setattr(_services, "get_endpoints_for", mock_get_endpoints_for)
    endpoints = get_sanitized_endpoints_for("mock_mainnet")
    assert len(endpoints) == 4
    for endpoint in endpoints:
        assert endpoint.get_blockheight() == 4
    # monkeypatch doesn't unset the attribute
    # this fails the rest of the tests
    monkeypatch.setattr(_services, "get_endpoints_for", get_endpoints_for)


class TestNetworkAPI:
    # Mainnet
    def test_get_balance_mainnet(self):
        time.sleep(1)
        results = NetworkAPI.get_balance(MAIN_ADDRESS_USED2, network="mainnet")
        assert isinstance(results, int)

    def test_get_balance_mainnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_balance(MAIN_ADDRESS_USED2, network="mainnet")

    def test_get_transactions_mainnet(self):
        time.sleep(1)
        results = NetworkAPI.get_transactions(MAIN_ADDRESS_USED1, network="mainnet")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_get_transactions_mainnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_transactions(MAIN_ADDRESS_USED1, network="mainnet")

    def test_get_transaction_mainnet(self):
        time.sleep(1)
        assert isinstance(
            NetworkAPI.get_transaction(MAIN_TX, network="mainnet"), Transaction
        )

    # FIXME: enable this when testnet APIs are fixed/replaced
    # def test_get_transaction_testnet(self):
    #     assert isinstance(NetworkAPI.get_transaction_testnet(TEST_TX), Transaction) == True

    def test_get_tx_amount_mainnet(self):
        time.sleep(1)
        assert NetworkAPI.get_tx_amount(MAIN_TX, 2, network="mainnet") == 0

    # FIXME: enable this when testnet APIs are fixed/replaced
    # def test_get_tx_amount_testnet(self):
    #     assert NetworkAPI.get_tx_amount_testnet(TEST_TX, 2) == 0

    def test_get_unspent_mainnet(self):
        time.sleep(1)
        results = NetworkAPI.get_unspent(MAIN_ADDRESS_USED2, network="mainnet")
        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, Unspent)

    def test_get_unspent_mainnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_unspent(MAIN_ADDRESS_USED1, network="mainnet")

    def test_get_raw_transaction_mainnet(self):
        time.sleep(1)
        results = NetworkAPI.get_raw_transaction(MAIN_TX, network="mainnet")
        assert isinstance(results, dict)
        # assert len(results) == 16  # BitcoinDotCOM
        assert len(results) == 7  # Chaingraph

    # Testnet
    @pytest.mark.skip
    def test_get_balance_testnet(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        time.sleep(1)
        results = NetworkAPI.get_balance(TEST_ADDRESS_USED2, network="testnet")
        assert isinstance(results, int)

    def test_get_balance_testnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_balance(TEST_ADDRESS_USED2, network="testnet")

    # FIXME: Bitcore.io only returns 10 elements
    # def test_get_transactions_test_equal(self):
    # results = [call(TEST_ADDRESS_USED2, network='testnet')[:100] for call in NetworkAPI.GET_TRANSACTIONS]
    # assert all_items_common(results)

    def test_get_transactions_test_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_transactions(TEST_ADDRESS_USED2, network="testnet")

    @pytest.mark.skip
    def test_get_unspent_testnet(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        time.sleep(1)
        results = NetworkAPI.get_unspent(TEST_ADDRESS_USED3, network="testnet")
        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, Unspent)

    def test_get_unspent_testnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_unspent(TEST_ADDRESS_USED2, network="testnet")


class TestBitcoinDotComAPI:
    # Mainnet
    # Note: There are 1 second sleeps because the default mainnet API has
    # rate limiting and will return 503 if we query it too quickly.

    def test_invalid_endpoint_url_mainnet(self):
        for url in INVALID_ENDPOINT_URLS:
            with pytest.raises(InvalidEndpointURLProvided):
                BitcoinDotComAPI(url)

    def test_get_single_endpoint_for_env_variable_bitcoincom(self, reset_environ):
        os.environ["BITCOINCOM_API_MAINNET"] = VALID_ENDPOINT_URLS[0]
        os.environ["CHAINGRAPH_API_MAINNET"] = "%mainnet"
        endpoints = get_endpoints_for("mainnet")
        assert len(endpoints) == 3
        assert isinstance(endpoints[0], ChaingraphAPI)  # default
        assert isinstance(endpoints[1], ChaingraphAPI)  # default
        assert isinstance(endpoints[2], BitcoinDotComAPI)  # env

    def test_get_single_endpoint_for_env_variable_chaingraph(self, reset_environ):
        os.environ["CHAINGRAPH_API"] = VALID_ENDPOINT_URLS[0]
        os.environ["CHAINGRAPH_API_MAINNET"] = "%mainnet"
        endpoints = get_endpoints_for("mainnet")
        assert len(endpoints) == 2
        assert isinstance(endpoints[0], ChaingraphAPI)  # env
        assert isinstance(endpoints[1], BitcoinDotComAPI)  # default
        assert endpoints[0].node_like == "%mainnet"

    def test_get_multiple_endpoint_for_env_variable_bitcoincom(self, reset_environ):
        os.environ["BITCOINCOM_API_MAINNET_1"] = VALID_ENDPOINT_URLS[0]
        os.environ["BITCOINCOM_API_MAINNET_2"] = VALID_ENDPOINT_URLS[1]
        endpoints = get_endpoints_for("mainnet")
        assert len(endpoints) == 4
        assert isinstance(endpoints[0], ChaingraphAPI)  # default
        assert isinstance(endpoints[1], ChaingraphAPI)  # default
        assert isinstance(endpoints[2], BitcoinDotComAPI)  # env
        assert isinstance(endpoints[3], BitcoinDotComAPI)  # env

    def test_get_multiple_endpoint_for_env_variable_chaingraph(self, reset_environ):
        os.environ["CHAINGRAPH_API_1"] = "https://demo.chaingraph.cash/v1/graphql"
        os.environ["CHAINGRAPH_API_2"] = "https://demo.chaingraph.cash/v1/graphql"
        os.environ["CHAINGRAPH_API_MAINNET_2"] = "%mainnet"
        endpoints = get_endpoints_for("mainnet")
        assert len(endpoints) == 3
        assert isinstance(endpoints[0], ChaingraphAPI)  # default
        assert isinstance(endpoints[1], ChaingraphAPI)  # default
        assert isinstance(endpoints[2], BitcoinDotComAPI)  # env
        assert endpoints[0].node_like == "%"
        assert endpoints[1].node_like == "%mainnet"

    def test_get_balance_mainnet_return_type(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert isinstance(this_endpoint.get_balance(MAIN_ADDRESS_USED1), int)

    def test_get_balance_mainnet_used(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert this_endpoint.get_balance(MAIN_ADDRESS_USED1) > 0

    def test_get_balance_mainnet_unused(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert this_endpoint.get_balance(MAIN_ADDRESS_UNUSED) == 0

    def test_get_balance_mainnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_balance(MAIN_ADDRESS_USED2)

    def test_get_transactions_mainnet_return_type(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert iter(this_endpoint.get_transactions(MAIN_ADDRESS_USED1))

    def test_get_transactions_mainnet_used(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert len(this_endpoint.get_transactions(MAIN_ADDRESS_USED1)) >= 218

    def test_get_transactions_mainnet_unused(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert len(this_endpoint.get_transactions(MAIN_ADDRESS_UNUSED)) == 0

    def test_get_transactions_mainnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_transactions(MAIN_ADDRESS_USED1)

    def test_get_transaction_mainnet(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert len(str(this_endpoint.get_transaction(MAIN_TX))) >= 156

    def test_get_transaction_mainnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_transaction(MAIN_TX)

    def test_get_tx_amount_mainnet(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert this_endpoint.get_tx_amount(MAIN_TX2, 1) == 546

    def test_get_tx_amount_mainnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_tx_amount(MAIN_TX2, 1)

    def test_get_unspent_mainnet_return_type(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert iter(this_endpoint.get_unspent(MAIN_ADDRESS_USED1))

    def test_get_unspent_mainnet_used(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert len(this_endpoint.get_unspent(MAIN_ADDRESS_USED2)) >= 1

    # def test_get_unspent_mainnet_unused(self):
    #     # TODO: This test returns a 400. Find out why and fix
    #     time.sleep(1)
    #     endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
    #     for endpoint in endpoints:
    #         this_endpoint = BitcoinDotComAPI(endpoint)
    #         assert len(this_endpoint.get_unspent(MAIN_ADDRESS_UNUSED)) == 0

    def test_get_unspent_mainnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_unspent(MAIN_ADDRESS_UNUSED)

    def test_get_raw_transaction_mainnet(self):
        time.sleep(1)
        endpoints = BitcoinDotComAPI.get_default_endpoints("mainnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert this_endpoint.get_raw_transaction(MAIN_TX)["txid"] == MAIN_TX

    def test_get_raw_transaction_mainnet_failure(self):
        with pytest.raises(ConnectionError):
            MockBackend.get_raw_transaction(MAIN_TX)

    # Testnet

    # @pytest.mark.skip
    def test_get_balance_testnet_used(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        endpoints = BitcoinDotComAPI.get_default_endpoints("testnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert this_endpoint.get_balance(TEST_ADDRESS_USED2) > 0

    # @pytest.mark.skip
    def test_get_balance_testnet_unused(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        endpoints = BitcoinDotComAPI.get_default_endpoints("testnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert this_endpoint.get_balance(TEST_ADDRESS_UNUSED) == 0

    # @pytest.mark.skip
    def test_get_transaction_testnet(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        endpoints = BitcoinDotComAPI.get_default_endpoints("testnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert len(str(this_endpoint.get_transaction(TEST_TX2))) >= 156

    # @pytest.mark.skip
    def test_get_transactions_testnet_used(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        endpoints = BitcoinDotComAPI.get_default_endpoints("testnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert len(this_endpoint.get_transactions(TEST_ADDRESS_USED2)) >= 444

    # @pytest.mark.skip
    def test_get_transactions_testnet_unused(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        endpoints = BitcoinDotComAPI.get_default_endpoints("testnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert len(this_endpoint.get_transactions(TEST_ADDRESS_UNUSED)) == 0

    # @pytest.mark.skip
    def test_get_unspent_testnet_used(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        endpoints = BitcoinDotComAPI.get_default_endpoints("testnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert len(this_endpoint.get_unspent(TEST_ADDRESS_USED2)) >= 194

    # @pytest.mark.skip
    def test_get_unspent_testnet_unused(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        endpoints = BitcoinDotComAPI.get_default_endpoints("testnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert len(this_endpoint.get_unspent(TEST_ADDRESS_UNUSED)) == 0

    # @pytest.mark.skip
    def test_get_raw_transaction_testnet(self):
        # Marking as skip because BitcoinCom Testnet is currently unreliable
        # TODO: Remove once a new Testnet endpoint is added
        endpoints = BitcoinDotComAPI.get_default_endpoints("testnet")
        for endpoint in endpoints:
            this_endpoint = BitcoinDotComAPI(endpoint)
            assert this_endpoint.get_raw_transaction(TEST_TX)["txid"] == TEST_TX
