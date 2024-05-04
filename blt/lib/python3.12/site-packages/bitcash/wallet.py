import json

from bitcash.crypto import ECPrivateKey
from bitcash.cashtoken import Unspents
from bitcash.curve import Point
from bitcash.exceptions import InvalidNetwork
from bitcash.format import (
    bytes_to_wif,
    public_key_to_address,
    public_key_to_coords,
    wif_to_bytes,
    address_to_public_key_hash,
    address_to_cashtokenaddress,
)
from bitcash.network import NetworkAPI, satoshi_to_currency_cached
from bitcash.network.meta import Unspent
from bitcash.op import OpCodes
from bitcash.transaction import calc_txid, create_p2pkh_transaction, sanitize_tx_data


NETWORKS = {"main": "mainnet", "test": "testnet", "regtest": "regtest"}
DEFAULT_FEE = 1


def wif_to_key(wif, regtest=False):
    private_key_bytes, compressed, version = wif_to_bytes(wif, regtest)

    if version == "main":
        if compressed:
            return PrivateKey.from_bytes(private_key_bytes)
        else:
            return PrivateKey(wif)
    elif version == "test":
        if compressed:
            return PrivateKeyTestnet.from_bytes(private_key_bytes)
        else:
            return PrivateKeyTestnet(wif)
    else:  # Regtest
        if compressed:
            return PrivateKeyRegtest.from_bytes(private_key_bytes)
        else:
            return PrivateKeyRegtest(wif)


class BaseKey:
    """This class represents a point on the elliptic curve secp256k1 and
    provides all necessary cryptographic functionality. You shouldn't use
    this class directly.

    :param wif: A private key serialized to the Wallet Import Format. If the
                argument is not supplied, a new private key will be created.
                The WIF compression flag will be adhered to, but the version
                byte is disregarded. Compression will be used by all new keys.
    :type wif: ``str``
    :raises TypeError: If ``wif`` is not a ``str``.
    """

    def __init__(self, wif=None, regtest=False):
        if wif:
            if isinstance(wif, str):
                private_key_bytes, compressed, version = wif_to_bytes(wif, regtest)
                self._pk = ECPrivateKey(private_key_bytes)
            elif isinstance(wif, ECPrivateKey):
                self._pk = wif
                compressed = True
            else:
                raise TypeError("Wallet Import Format must be a string.")
        else:
            self._pk = ECPrivateKey()
            compressed = True

        self._public_point = None
        self._public_key = self._pk.public_key.format(compressed=compressed)

    @property
    def public_key(self):
        """The public point serialized to bytes."""
        return self._public_key

    @property
    def public_point(self):
        """The public point (x, y)."""
        if self._public_point is None:
            self._public_point = Point(*public_key_to_coords(self._public_key))
        return self._public_point

    def sign(self, data):
        """Signs some data which can be verified later by others using
        the public key.

        :param data: The message to sign.
        :type data: ``bytes``
        :returns: A signature compliant with BIP-62.
        :rtype: ``bytes``
        """
        return self._pk.sign(data)

    def verify(self, signature, data):
        """Verifies some data was signed by this private key.

        :param signature: The signature to verify.
        :type signature: ``bytes``
        :param data: The data that was supposedly signed.
        :type data: ``bytes``
        :rtype: ``bool``
        """
        return self._pk.public_key.verify(signature, data)

    def to_hex(self):
        """:rtype: ``str``"""
        return self._pk.to_hex()

    def to_bytes(self):
        """:rtype: ``bytes``"""
        return self._pk.secret

    def to_der(self):
        """:rtype: ``bytes``"""
        return self._pk.to_der()

    def to_pem(self):
        """:rtype: ``bytes``"""
        return self._pk.to_pem()

    def to_int(self):
        """:rtype: ``int``"""
        return self._pk.to_int()

    def is_compressed(self):
        """Returns whether or not this private key corresponds to a compressed
        public key.

        :rtype: ``bool``
        """
        return True if len(self.public_key) == 33 else False

    def __eq__(self, other):
        return self.to_int() == other.to_int()


class PrivateKey(BaseKey):
    """This class represents a BitcoinCash private key. ``Key`` is an alias.

    :param wif: A private key serialized to the Wallet Import Format. If the
                argument is not supplied, a new private key will be created.
                The WIF compression flag will be adhered to, but the version
                byte is disregarded. Compression will be used by all new keys.
    :type wif: ``str``
    :raises TypeError: If ``wif`` is not a ``str``.
    """

    def __init__(self, wif=None, network="main"):
        super().__init__(wif=wif)

        self._address = None
        self._scriptcode = None
        if network in NETWORKS.keys():
            self._network = network
        else:
            raise InvalidNetwork
        self.balance = 0
        self.cashtoken_balance = {}
        self.unspents = []
        self.transactions = []

    @property
    def address(self):
        """The public address you share with others to receive funds."""
        if self._address is None:
            self._address = public_key_to_address(
                self._public_key, version=self._network
            )

        return self._address

    @property
    def cashtoken_address(self):
        """The public address you share with others to receive cashtokens."""
        return address_to_cashtokenaddress(self.address)

    @property
    def scriptcode(self):
        self._scriptcode = (
            OpCodes.OP_DUP.binary
            + OpCodes.OP_HASH160.binary
            + OpCodes.OP_DATA_20.binary
            + address_to_public_key_hash(self.address)
            + OpCodes.OP_EQUALVERIFY.binary
            + OpCodes.OP_CHECKSIG.binary
        )
        return self._scriptcode

    def to_wif(self):
        return bytes_to_wif(
            self._pk.secret, version=self._network, compressed=self.is_compressed()
        )

    def balance_as(self, currency):
        """Returns your balance as a formatted string in a particular currency.

        :param currency: One of the :ref:`supported currencies`.
        :type currency: ``str``
        :rtype: ``str``
        """
        return satoshi_to_currency_cached(self.balance, currency)

    def get_balance(self, currency="satoshi"):
        """Fetches the current balance by calling
        :func:`~bitcash.PrivateKey.get_balance` and returns it using
        :func:`~bitcash.PrivateKey.balance_as`.

        :param currency: One of the :ref:`supported currencies`.
        :type currency: ``str``
        :rtype: ``str``
        """
        _ = self.get_unspents()
        return self.balance_as(currency)

    def get_cashtokenbalance(self):
        """Fetches the current cashtoken balance by calling
        :func:`~bitcash.PrivateKey.get_balance` and returns it as
        a token dictionary.

        :rtype: ``dict``
        """
        _ = self.get_unspents()
        return self.cashtoken_balance

    def get_unspents(self):
        """Fetches all available unspent transaction outputs.

        :rtype: ``list`` of :class:`~bitcash.network.meta.Unspent`
        """
        self.unspents[:] = NetworkAPI.get_unspent(
            self.address, network=NETWORKS[self._network]
        )
        _ = Unspents(self.unspents)
        self.balance = _.amount
        self.cashtoken_balance = _.tokendata
        return self.unspents

    def get_transactions(self):
        """Fetches transaction history.

        :rtype: ``list`` of ``str`` transaction IDs
        """
        self.transactions[:] = NetworkAPI.get_transactions(
            self.address, network=NETWORKS[self._network]
        )
        return self.transactions

    def create_transaction(
        self,
        outputs,
        fee=None,
        leftover=None,
        combine=True,
        message=None,
        unspents=None,
        custom_pushdata=False,
    ):  # pragma: no cover
        """Creates a signed P2PKH transaction.

        :param outputs: A sequence of outputs you wish to send in the form
                        ``(destination, amount, currency)``. The amount can
                        be either an int, float, or string as long as it is
                        a valid input to ``decimal.Decimal``. The currency
                        must be :ref:`supported <supported currencies>`.
                        To send CashToken, the list of output is made in the
                        form ``(destination, amount, currency, category_id,
                        nft_capability, nft_commitment, token_amount)``. The category_id
                        is hex of tx-id as ``str``. The nft_capability is the capability
                        of non-fungible token in ("none", "mutable", "minting"). The
                        nft_commitment is the commitment of the non-fungible token in
                        ``bytes``.
                        The CashToken property nft_capability, nft_commitment, or
                        the token_amount can be None if not to be sent. If
                        category_id is tx-id of unspent with tx-index 0, then
                        tx is treated as a genesis tx.
        :type outputs: ``list`` of ``tuple``
        :param fee: The number of satoshi per byte to pay to miners. By default
                    Bitcash will poll `<https://bitcoincashfees.earn.com>`_ and use a fee
                    that will allow your transaction to be confirmed as soon as
                    possible.
        :type fee: ``int``
        :param leftover: The destination that will receive any change from the
                         transaction. By default Bitcash will send any change to
                         the same address you sent from.
        :type leftover: ``str``
        :param combine: Whether or not Bitcash should use all available UTXOs to
                        make future transactions smaller and therefore reduce
                        fees. By default Bitcash will consolidate UTXOs.
        :type combine: ``bool``
        :param message: A message to include in the transaction. This will be
                        stored in the blockchain forever. Due to size limits,
                        each message will be stored in chunks of 220 bytes.
        :type message: ``str``
        :param unspents: The UTXOs to use as the inputs. By default Bitcash will
                         communicate with the blockchain itself.
        :type unspents: ``list`` of :class:`~bitcash.network.meta.Unspent`
        :returns: The signed transaction as hex.
        :rtype: ``str``
        """

        unspents, outputs = sanitize_tx_data(
            unspents or self.get_unspents(),
            outputs,
            fee or DEFAULT_FEE,
            leftover or self.cashtoken_address,
            combine=combine,
            message=message,
            compressed=self.is_compressed(),
            custom_pushdata=custom_pushdata,
        )

        return create_p2pkh_transaction(self, unspents, outputs)

    def send(
        self,
        outputs,
        fee=None,
        leftover=None,
        combine=True,
        message=None,
        unspents=None,
    ):  # pragma: no cover
        """Creates a signed P2PKH transaction and attempts to broadcast it on
        the blockchain. This accepts the same arguments as
        :func:`~bitcash.PrivateKey.create_transaction`.

        :param outputs: A sequence of outputs you wish to send in the form
                        ``(destination, amount, currency)``. The amount can
                        be either an int, float, or string as long as it is
                        a valid input to ``decimal.Decimal``. The currency
                        must be :ref:`supported <supported currencies>`.
                        To send CashToken, the list of output is made in the
                        form ``(destination, amount, currency, category_id,
                        nft_capability, nft_commitment, token_amount)``. The category_id
                        is hex of tx-id as ``str``. The nft_capability is the capability
                        of non-fungible token in ("none", "mutable", "minting"). The
                        nft_commitment is the commitment of the non-fungible token in
                        ``bytes``.
                        The CashToken property nft_capability, nft_commitment, or
                        the token_amount can be None if not to be sent. If
                        category_id is tx-id of unspent with tx-index 0, then
                        tx is treated as a genesis tx.
        :type outputs: ``list`` of ``tuple``
        :param fee: The number of satoshi per byte to pay to miners. By default
                    Bitcash will poll `<https://bitcoincashfees.earn.com>`_ and use a fee
                    that will allow your transaction to be confirmed as soon as
                    possible.
        :type fee: ``int``
        :param leftover: The destination that will receive any change from the
                         transaction. By default Bitcash will send any change to
                         the same address you sent from.
        :type leftover: ``str``
        :param combine: Whether or not Bitcash should use all available UTXOs to
                        make future transactions smaller and therefore reduce
                        fees. By default Bitcash will consolidate UTXOs.
        :type combine: ``bool``
        :param message: A message to include in the transaction. This will be
                        stored in the blockchain forever. Due to size limits,
                        each message will be stored in chunks of 220 bytes.
        :type message: ``str``
        :param unspents: The UTXOs to use as the inputs. By default Bitcash will
                         communicate with the blockchain itself.
        :type unspents: ``list`` of :class:`~bitcash.network.meta.Unspent`
        :returns: The transaction ID.
        :rtype: ``str``
        """

        tx_hex = self.create_transaction(
            outputs,
            fee=fee,
            leftover=leftover,
            combine=combine,
            message=message,
            unspents=unspents,
        )

        NetworkAPI.broadcast_tx(tx_hex, network=NETWORKS[self._network])

        return calc_txid(tx_hex)

    @classmethod
    def prepare_transaction(
        cls,
        address,
        outputs,
        compressed=True,
        fee=None,
        leftover=None,
        combine=True,
        message=None,
        unspents=None,
    ):  # pragma: no cover
        """Prepares a P2PKH transaction for offline signing.

        :param address: The address the funds will be sent from.
        :type address: ``str``
        :param outputs: A sequence of outputs you wish to send in the form
                        ``(destination, amount, currency)``. The amount can
                        be either an int, float, or string as long as it is
                        a valid input to ``decimal.Decimal``. The currency
                        must be :ref:`supported <supported currencies>`.
                        To send CashToken, the list of output is made in the
                        form ``(destination, amount, currency, category_id,
                        nft_capability, nft_commitment, token_amount)``. The category_id
                        is hex of tx-id as ``str``. The nft_capability is the capability
                        of non-fungible token in ("none", "mutable", "minting"). The
                        nft_commitment is the commitment of the non-fungible token in
                        ``bytes``.
                        The CashToken property nft_capability, nft_commitment, or
                        the token_amount can be None if not to be sent. If
                        category_id is tx-id of unspent with tx-index 0, then
                        tx is treated as a genesis tx.
        :type outputs: ``list`` of ``tuple``
        :param compressed: Whether or not the ``address`` corresponds to a
                           compressed public key. This influences the fee.
        :type compressed: ``bool``
        :param fee: The number of satoshi per byte to pay to miners. By default
                    Bitcash will poll `<https://bitcoincashfees.earn.com>`_ and use a fee
                    that will allow your transaction to be confirmed as soon as
                    possible.
        :type fee: ``int``
        :param leftover: The destination that will receive any change from the
                         transaction. By default Bitcash will send any change to
                         the same address you sent from.
        :type leftover: ``str``
        :param combine: Whether or not Bitcash should use all available UTXOs to
                        make future transactions smaller and therefore reduce
                        fees. By default Bitcash will consolidate UTXOs.
        :type combine: ``bool``
        :param message: A message to include in the transaction. This will be
                        stored in the blockchain forever. Due to size limits,
                        each message will be stored in chunks of 220 bytes.
        :type message: ``str``
        :param unspents: The UTXOs to use as the inputs. By default Bitcash will
                         communicate with the blockchain itself.
        :type unspents: ``list`` of :class:`~bitcash.network.meta.Unspent`
        :returns: JSON storing data required to create an offline transaction.
        :rtype: ``str``
        """
        unspents, outputs = sanitize_tx_data(
            unspents or NetworkAPI.get_unspent(address),
            outputs,
            fee or DEFAULT_FEE,
            leftover or address,
            combine=combine,
            message=message,
            compressed=compressed,
        )

        outputs = list(map(list, outputs))
        for output in outputs:
            # script
            output[0] = output[0].hex()
            # nft_commitment
            if output[4] is not None:
                output[4] = output[4].hex()

        data = {
            "unspents": [unspent.to_dict() for unspent in unspents],
            "outputs": outputs,
        }

        return json.dumps(data, separators=(",", ":"))

    def sign_transaction(self, tx_data):  # pragma: no cover
        """Creates a signed P2PKH transaction using previously prepared
        transaction data.

        :param tx_data: Output of :func:`~bitcash.PrivateKey.prepare_transaction`.
        :type tx_data: ``str``
        :returns: The signed transaction as hex.
        :rtype: ``str``
        """
        data = json.loads(tx_data)

        unspents = [Unspent.from_dict(unspent) for unspent in data["unspents"]]
        outputs = data["outputs"]
        for output in outputs:
            # script
            output[0] = bytes.fromhex(output[0])
            # nft_commitment
            if output[4] is not None:
                output[4] = bytes.fromhex(output[4])
        outputs = list(map(tuple, outputs))

        return create_p2pkh_transaction(self, unspents, outputs)

    @classmethod
    def from_hex(cls, hexed):
        """
        :param hexed: A private key previously encoded as hex.
        :type hexed: ``str``
        :rtype: :class:`~bitcash.PrivateKey`
        """
        return PrivateKey(ECPrivateKey.from_hex(hexed))

    @classmethod
    def from_bytes(cls, bytestr):
        """
        :param bytestr: A private key previously encoded as hex.
        :type bytestr: ``bytes``
        :rtype: :class:`~bitcash.PrivateKey`
        """
        return PrivateKey(ECPrivateKey(bytestr))

    @classmethod
    def from_der(cls, der):
        """
        :param der: A private key previously encoded as DER.
        :type der: ``bytes``
        :rtype: :class:`~bitcash.PrivateKey`
        """
        return PrivateKey(ECPrivateKey.from_der(der))

    @classmethod
    def from_pem(cls, pem):
        """
        :param pem: A private key previously encoded as PEM.
        :type pem: ``bytes``
        :rtype: :class:`~bitcash.PrivateKey`
        """
        return PrivateKey(ECPrivateKey.from_pem(pem))

    @classmethod
    def from_int(cls, num):
        """
        :param num: A private key in raw integer form.
        :type num: ``int``
        :rtype: :class:`~bitcash.PrivateKey`
        """
        return PrivateKey(ECPrivateKey.from_int(num))

    def __repr__(self):
        return f"<PrivateKey: {self.address}>"


class PrivateKeyTestnet(PrivateKey):
    """This class represents a testnet BitcoinCash private key. **Note:** coins
    on the test network have no monetary value!

    :param wif: A private key serialized to the Wallet Import Format. If the
                argument is not supplied, a new private key will be created.
                The WIF compression flag will be adhered to, but the version
                byte is disregarded. Compression will be used by all new keys.
    :type wif: ``str``
    :raises TypeError: If ``wif`` is not a ``str``.
    """

    def __init__(self, wif=None, network="test"):
        super().__init__(wif=wif, network=network)

    @classmethod
    def from_hex(cls, hexed):
        """
        :param hexed: A private key previously encoded as hex.
        :type hexed: ``str``
        :rtype: :class:`~bitcash.PrivateKeyTestnet`
        """
        return PrivateKeyTestnet(ECPrivateKey.from_hex(hexed))

    @classmethod
    def from_bytes(cls, bytestr):
        """
        :param bytestr: A private key previously encoded as hex.
        :type bytestr: ``bytes``
        :rtype: :class:`~bitcash.PrivateKeyTestnet`
        """
        return PrivateKeyTestnet(ECPrivateKey(bytestr))

    @classmethod
    def from_der(cls, der):
        """
        :param der: A private key previously encoded as DER.
        :type der: ``bytes``
        :rtype: :class:`~bitcash.PrivateKeyTestnet`
        """
        return PrivateKeyTestnet(ECPrivateKey.from_der(der))

    @classmethod
    def from_pem(cls, pem):
        """
        :param pem: A private key previously encoded as PEM.
        :type pem: ``bytes``
        :rtype: :class:`~bitcash.PrivateKeyTestnet`
        """
        return PrivateKeyTestnet(ECPrivateKey.from_pem(pem))

    @classmethod
    def from_int(cls, num):
        """
        :param num: A private key in raw integer form.
        :type num: ``int``
        :rtype: :class:`~bitcash.PrivateKeyTestnet`
        """
        return PrivateKeyTestnet(ECPrivateKey.from_int(num))

    def __repr__(self):
        return f"<PrivateKeyTestnet: {self.address}>"


class PrivateKeyRegtest(PrivateKey):
    """This class represents a regtest BitcoinCash private key. **Note:** coins
    on the regtest network have no monetary value!

    :param wif: A private key serialized to the Wallet Import Format. If the
                argument is not supplied, a new private key will be created.
                The WIF compression flag will be adhered to, but the version
                byte is disregarded. Compression will be used by all new keys.
    :type wif: ``str``
    :raises TypeError: If ``wif`` is not a ``str``.
    """

    def __init__(self, wif=None, network="regtest"):
        super().__init__(wif, network)

    @classmethod
    def from_hex(cls, hexed):
        """
        :param hexed: A private key previously encoded as hex.
        :type hexed: ``str``
        :rtype: :class:`~bitcash.PrivateKeyRegtest`
        """
        return PrivateKeyRegtest(ECPrivateKey.from_hex(hexed))

    @classmethod
    def from_bytes(cls, bytestr):
        """
        :param bytestr: A private key previously encoded as hex.
        :type bytestr: ``bytes``
        :rtype: :class:`~bitcash.PrivateKeyRegtest`
        """
        return PrivateKeyRegtest(ECPrivateKey(bytestr))

    @classmethod
    def from_der(cls, der):
        """
        :param der: A private key previously encoded as DER.
        :type der: ``bytes``
        :rtype: :class:`~bitcash.PrivateKeyRegtest`
        """
        return PrivateKeyRegtest(ECPrivateKey.from_der(der))

    @classmethod
    def from_pem(cls, pem):
        """
        :param pem: A private key previously encoded as PEM.
        :type pem: ``bytes``
        :rtype: :class:`~bitcash.PrivateKeyRegtest`
        """
        return PrivateKeyRegtest(ECPrivateKey.from_pem(pem))

    @classmethod
    def from_int(cls, num):
        """
        :param num: A private key in raw integer form.
        :type num: ``int``
        :rtype: :class:`~bitcash.PrivateKeyRegtest`
        """
        return PrivateKeyRegtest(ECPrivateKey.from_int(num))

    def __repr__(self):
        return f"<PrivateKeyRegtest: {self.address}>"


Key = PrivateKey
