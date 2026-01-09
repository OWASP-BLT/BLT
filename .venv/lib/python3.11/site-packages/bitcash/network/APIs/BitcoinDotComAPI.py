from bitcash.network.http import session
from decimal import Decimal
from bitcash.exceptions import InvalidEndpointURLProvided
from bitcash.network import currency_to_satoshi
from bitcash.network.APIs import BaseAPI
from bitcash.network.meta import Unspent
from bitcash.network.transaction import Transaction, TxPart
from bitcash.format import cashtokenaddress_to_address

# This class is the interface for Bitcash to interact with
# Bitcoin.com based RESTful interfaces.

BCH_TO_SAT_MULTIPLIER = 100000000
# TODO: Refactor constant above into a 'constants.py' file


class BitcoinDotComAPI(BaseAPI):
    """rest.bitcoin.com API"""

    def __init__(self, network_endpoint: str):
        try:
            assert isinstance(network_endpoint, str)
            assert network_endpoint[:4] == "http"
            assert network_endpoint[-4:] == "/v2/"
        except AssertionError:
            raise InvalidEndpointURLProvided(
                f"Provided endpoint '{network_endpoint}' is not a valid URL for a "
                f"Bitcoin.com-based REST endpoint"
            )

        self.network_endpoint = network_endpoint

    # Default endpoints to use for this interface
    DEFAULT_ENDPOINTS = {
        "mainnet": ["https://rest.bch.actorforth.org/v2/"],
        "testnet": [],
        "regtest": ["http://localhost:12500/v2/"],
    }

    # Paths specific to rest.bitcoin.com-based endpoints
    PATHS = {
        "unspent": "address/utxo/{}",
        "address": "address/details/{}",
        "raw-tx": "rawtransactions/sendRawTransaction",
        "tx-details": "transaction/details/{}",
        "block-height": "blockchain/getBlockCount",
    }

    @classmethod
    def get_default_endpoints(cls, network):
        return cls.DEFAULT_ENDPOINTS[network]

    def make_endpoint_url(self, path):
        return self.network_endpoint + self.PATHS[path]

    def get_blockheight(self, *args, **kwargs):
        api_url = self.make_endpoint_url("block-height")
        r = session.get(api_url, *args, **kwargs)
        r.raise_for_status()
        return r.json()

    def get_balance(self, address, *args, **kwargs):
        address = cashtokenaddress_to_address(address)
        api_url = self.make_endpoint_url("address").format(address)
        r = session.get(api_url, *args, **kwargs)
        r.raise_for_status()
        data = r.json()
        return data["balanceSat"] + data["unconfirmedBalanceSat"]

    def get_transactions(self, address, *args, **kwargs):
        address = cashtokenaddress_to_address(address)
        api_url = self.make_endpoint_url("address").format(address)
        r = session.get(api_url, *args, **kwargs)
        r.raise_for_status()
        return r.json()["transactions"]

    def get_transaction(self, txid, *args, **kwargs):
        api_url = self.make_endpoint_url("tx-details").format(txid)
        r = session.get(api_url, *args, **kwargs)
        r.raise_for_status()
        response = r.json(parse_float=Decimal)

        tx = Transaction(
            response["txid"],
            response.get("blockheight", None),
            int(
                (
                    Decimal(response["valueIn"]) * BCH_TO_SAT_MULTIPLIER
                ).to_integral_value()
            ),
            int(
                (
                    Decimal(response["valueOut"]) * BCH_TO_SAT_MULTIPLIER
                ).to_integral_value()
            ),
            int(
                (Decimal(response["fees"]) * BCH_TO_SAT_MULTIPLIER).to_integral_value()
            ),
        )

        for txin in response["vin"]:
            part = TxPart(
                txin["cashAddress"],
                int(
                    (Decimal(txin["value"]) * BCH_TO_SAT_MULTIPLIER).to_integral_value()
                ),
                asm=txin["scriptSig"]["asm"],
            )
            tx.add_input(part)

        for txout in response["vout"]:
            addr = None
            if (
                "cashAddrs" in txout["scriptPubKey"]
                and txout["scriptPubKey"]["cashAddrs"] is not None
            ):
                addr = txout["scriptPubKey"]["cashAddrs"][0]

            category_id = None
            nft_capability = None
            nft_commitment = None
            token_amount = None
            if "tokenData" in txout:
                token_data = txout["tokenData"]
                category_id = token_data["category"]
                token_amount = int(token_data["amount"]) or None
                if "nft" in token_data:
                    nft_capability = token_data["nft"]["capability"]
                    nft_commitment = token_data["nft"]["commitment"] or None
            part = TxPart(
                addr,
                int(
                    (
                        Decimal(txout["value"]) * BCH_TO_SAT_MULTIPLIER
                    ).to_integral_value()
                ),
                category_id,
                nft_capability,
                nft_commitment,
                token_amount,
                asm=txout["scriptPubKey"]["asm"],
            )
            tx.add_output(part)

        return tx

    def get_tx_amount(self, txid, txindex, *args, **kwargs):
        api_url = self.make_endpoint_url("tx-details").format(txid)
        r = session.get(api_url, *args, **kwargs)
        r.raise_for_status()
        response = r.json(parse_float=Decimal)
        return int(
            (
                Decimal(response["vout"][txindex]["value"]) * BCH_TO_SAT_MULTIPLIER
            ).to_integral_value()
        )

    def get_unspent(self, address, *args, **kwargs):
        return self._get_unspent_cashtoken(address, *args, **kwargs)
        address = cashtokenaddress_to_address(address)
        api_url = self.make_endpoint_url("unspent").format(address)
        r = session.get(api_url, *args, **kwargs)
        r.raise_for_status()
        unspents = []
        for tx in r.json()["utxos"]:
            category_id = None
            nft_capability = None
            nft_commitment = None
            token_amount = None
            if "tokenData" in tx:
                token_data = tx["tokenData"]
                category_id = token_data["category"]
                token_amount = int(token_data["amount"]) or None
                if "nft" in token_data:
                    nft_capability = token_data["nft"]["capability"]
                    _ = token_data["nft"]["commitment"]
                    nft_commitment = bytes.fromhex(_) or None
            unspents.append(
                Unspent(
                    currency_to_satoshi(tx["amount"], "bch"),
                    tx["confirmations"],
                    r.json()["scriptPubKey"],
                    tx["txid"],
                    tx["vout"],
                    category_id,
                    nft_capability,
                    nft_commitment,
                    token_amount,
                )
            )
        return unspents

    def _get_unspent_cashtoken(self, address, *args, **kwargs):
        """
        Makeshift function to get cashtoken info in unspents by querying tx details.
        Should be deprecated once BitcoinDotComAPI supports cashtokens in unspents
        """
        address = cashtokenaddress_to_address(address)
        api_url = self.make_endpoint_url("unspent").format(address)
        r = session.get(api_url, *args, **kwargs)
        r.raise_for_status()
        unspents = [
            Unspent(
                currency_to_satoshi(tx["amount"], "bch"),
                tx["confirmations"],
                r.json()["scriptPubKey"],
                tx["txid"],
                tx["vout"],
            )
            for tx in r.json()["utxos"]
        ]
        api_url = self.make_endpoint_url("tx-details").format("")
        r = session.post(
            api_url, {"txids": [unspent.txid for unspent in unspents]}, *args, **kwargs
        )
        r.raise_for_status()
        response = r.json(parse_float=Decimal)
        for i, unspent in enumerate(unspents):
            txout = response[i]["vout"][unspent.txindex]
            if "tokenData" in txout:
                token_data = txout["tokenData"]
                unspent.category_id = token_data["category"]
                unspent.token_amount = int(token_data["amount"]) or None
                if "nft" in token_data:
                    unspent.nft_capability = token_data["nft"]["capability"]
                    _ = bytes.fromhex(token_data["nft"]["commitment"])
                    unspent.nft_commitment = _ or None
        return unspents

    def get_raw_transaction(self, txid, *args, **kwargs):
        api_url = self.make_endpoint_url("tx-details").format(txid)
        r = session.get(api_url, *args, **kwargs)
        r.raise_for_status()
        return r.json(parse_float=Decimal)

    def broadcast_tx(self, tx_hex, *args, **kwargs):  # pragma: no cover
        api_url = self.make_endpoint_url("raw-tx")
        r = session.post(api_url, json={"hexes": [tx_hex]}, *args, **kwargs)
        return r.status_code == 200
