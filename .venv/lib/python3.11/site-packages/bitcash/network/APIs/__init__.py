from abc import ABC, abstractmethod


class BaseAPI(ABC):
    """
    Abstract class for API classes

    :param network_endpoint: Network endpoint to send requests
    :type network_endpoint: ``str``
    """

    def __init__(self, network_endpoint: str):
        self.network_endpoint = network_endpoint

    @abstractmethod
    def get_default_endpoints(self, network):
        """
        Return default endpoints for a network

        :param network: network in ["mainnet", "testnet", "regtest"]
        :type network: ``str``
        :returns: List of endpoints
        :rtype: ``list`` of ``str``
        """

    @abstractmethod
    def get_blockheight(self, *args, **kwargs):
        """
        Return the block height.

        :returns: Blockheight
        :rtype: ``int``
        """

    @abstractmethod
    def get_balance(self, address, *args, **kwargs):
        """
        Returns balance of an address

        :param address: Cashaddress of the locking script
        :type address: ``str``
        :returns: BCH amount in satoshis
        :rtype: ``int``
        """

    @abstractmethod
    def get_transactions(self, address, *args, **kwargs):
        """Gets the ID of all transactions related to an address.

        :param address: The address in question.
        :type address: ``str``
        :rtype: ``list`` of ``str``
        """

    @abstractmethod
    def get_tx_amount(self, txid, txindex, *args, **kwargs):
        """Gets the amount of a given transaction output.

        :param txid: The transaction id in question.
        :type txid: ``str``
        :param txindex: The transaction index in question.
        :type txindex: ``int``
        :rtype: ``Decimal``
        """

    @abstractmethod
    def get_transaction(self, txid, *args, **kwargs):
        """
        Returns transaction data of a transaction

        :param txid: Transaction id hex
        :type txid: ``str``
        :returns: Instance of class Transaction
        :rtype: ``Transaction``
        """

    @abstractmethod
    def get_unspent(self, address, *args, **kwargs):
        """
        Returns list of unspent outputs associated with an address

        :param address: Cashaddress of the locking script
        :type address: ``str``
        :returns: List of unspents
        :rtype: ``list``
        """

    @abstractmethod
    def get_raw_transaction(self, txid, *args, **kwargs):
        """Gets the raw, unparsed transaction details.

        :param txid: The transaction id in question.
        :type txid: ``str``
        :rtype: ``Transaction``
        """

    @abstractmethod
    def broadcast_tx(self, tx_hex, *args, **kwargs):
        """
        Broadcast a raw transaction

        :param tx_hex: The hex representaion of the transaction to be
                       broadcasted.
        :type tx_hex: ``str``
        :return: Boolean indicating if the tx is broadcasted
        :rtype: ``bool``
        """
