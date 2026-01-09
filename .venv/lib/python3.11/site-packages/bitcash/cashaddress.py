import io
from bitcash.exceptions import InvalidAddress
from bitcash.op import OpCodes
from bitcash.utils import varint_to_int

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def polymod(values):
    chk = 1
    generator = [
        (0x01, 0x98F2BC8E61),
        (0x02, 0x79B76D99E2),
        (0x04, 0xF33E5FB3C4),
        (0x08, 0xAE2EABE2A8),
        (0x10, 0x1E4F43E470),
    ]
    for value in values:
        top = chk >> 35
        chk = ((chk & 0x07FFFFFFFF) << 5) ^ value
        for i in generator:
            if top & i[0] != 0:
                chk ^= i[1]
    return chk ^ 1


def calculate_checksum(prefix, payload):
    poly = polymod(prefix_expand(prefix) + payload + [0, 0, 0, 0, 0, 0, 0, 0])
    out = list()
    for i in range(8):
        out.append((poly >> 5 * (7 - i)) & 0x1F)
    return out


def verify_checksum(prefix, payload):
    return polymod(prefix_expand(prefix) + payload) == 0


def b32decode(inputs):
    out = list()
    for letter in inputs:
        out.append(CHARSET.find(letter))
    return out


def b32encode(inputs):
    out = ""
    for char_code in inputs:
        out += CHARSET[char_code]
    return out


def convertbits(data, frombits, tobits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def prefix_expand(prefix):
    return [ord(x) & 0x1F for x in prefix] + [0]


class Address:
    """
    Class to handle CashAddr.

    :param version: Version of CashAddr
    :type version: ``str``
    :param payload: Payload of CashAddr as int list of the bytearray
    :type payload: ``list`` of ``int``
    """

    VERSIONS = {
        "P2SH20": {"prefix": "bitcoincash", "version_bit": 8, "network": "mainnet"},
        "P2SH32": {"prefix": "bitcoincash", "version_bit": 11, "network": "mainnet"},
        "P2PKH": {"prefix": "bitcoincash", "version_bit": 0, "network": "mainnet"},
        "P2SH20-TESTNET": {"prefix": "bchtest", "version_bit": 8, "network": "testnet"},
        "P2SH32-TESTNET": {
            "prefix": "bchtest",
            "version_bit": 11,
            "network": "testnet",
        },
        "P2PKH-TESTNET": {"prefix": "bchtest", "version_bit": 0, "network": "testnet"},
        "P2SH20-REGTEST": {"prefix": "bchreg", "version_bit": 8, "network": "regtest"},
        "P2SH32-REGTEST": {"prefix": "bchreg", "version_bit": 11, "network": "regtest"},
        "P2PKH-REGTEST": {"prefix": "bchreg", "version_bit": 0, "network": "regtest"},
        "P2SH20-CATKN": {
            "prefix": "bitcoincash",
            "version_bit": 24,
            "network": "mainnet",
        },
        "P2SH32-CATKN": {
            "prefix": "bitcoincash",
            "version_bit": 27,
            "network": "mainnet",
        },
        "P2PKH-CATKN": {
            "prefix": "bitcoincash",
            "version_bit": 16,
            "network": "mainnet",
        },
        "P2SH20-CATKN-TESTNET": {
            "prefix": "bchtest",
            "version_bit": 24,
            "network": "testnet",
        },
        "P2SH32-CATKN-TESTNET": {
            "prefix": "bchtest",
            "version_bit": 27,
            "network": "testnet",
        },
        "P2PKH-CATKN-TESTNET": {
            "prefix": "bchtest",
            "version_bit": 16,
            "network": "testnet",
        },
        "P2SH20-CATKN-REGTEST": {
            "prefix": "bchreg",
            "version_bit": 24,
            "network": "regtest",
        },
        "P2SH32-CATKN-REGTEST": {
            "prefix": "bchreg",
            "version_bit": 27,
            "network": "regtest",
        },
        "P2PKH-CATKN-REGTEST": {
            "prefix": "bchreg",
            "version_bit": 16,
            "network": "regtest",
        },
    }

    VERSION_SUFFIXES = {"bitcoincash": "", "bchtest": "-TESTNET", "bchreg": "-REGTEST"}

    ADDRESS_TYPES = {
        0: "P2PKH",
        8: "P2SH20",
        11: "P2SH32",
        16: "P2PKH-CATKN",
        24: "P2SH20-CATKN",
        27: "P2SH32-CATKN",
    }

    def __init__(self, version, payload):
        if version not in Address.VERSIONS:
            raise ValueError("Invalid address version provided")

        self.version = version
        self.payload = payload
        self.prefix = Address.VERSIONS[self.version]["prefix"]

    def __str__(self):
        return (
            f"version: {self.version}\npayload: {self.payload}\nprefix: {self.prefix}"
        )

    def __repr__(self):
        return f"Address('{self.cash_address()}')"

    def __eq__(self, other):
        if isinstance(other, str):
            return self.cash_address() == other
        elif isinstance(other, Address):
            return self.cash_address() == other.cash_address()
        else:
            raise ValueError(
                "Address can be compared to a string address"
                " or an instance of Address"
            )

    def cash_address(self):
        """
        Generate CashAddr of the Address

        :rtype: ``str``
        """
        version_bit = Address.VERSIONS[self.version]["version_bit"]
        payload = [version_bit] + self.payload
        payload = convertbits(payload, 8, 5)
        checksum = calculate_checksum(self.prefix, payload)
        return self.prefix + ":" + b32encode(payload + checksum)

    @property
    def scriptcode(self):
        """
        Generate the locking script of the Address

        :rtype: ``bytes``
        """
        if "P2PKH" in self.version:
            return (
                OpCodes.OP_DUP.binary
                + OpCodes.OP_HASH160.binary
                + OpCodes.OP_DATA_20.binary
                + bytes(self.payload)
                + OpCodes.OP_EQUALVERIFY.binary
                + OpCodes.OP_CHECKSIG.binary
            )
        if "P2SH20" in self.version:
            return (
                OpCodes.OP_HASH160.binary
                + OpCodes.OP_DATA_20.binary
                + bytes(self.payload)
                + OpCodes.OP_EQUAL.binary
            )
        if "P2SH32" in self.version:
            return (
                OpCodes.OP_HASH256.binary
                + OpCodes.OP_DATA_32.binary
                + bytes(self.payload)
                + OpCodes.OP_EQUAL.binary
            )

    @classmethod
    def from_script(cls, scriptcode):
        """
        Generate Address from a locking script

        :param scriptcode: The locking script
        :type scriptcode: ``bytes``
        :returns: Instance of :class:~bitcash.cashaddress.Address
        """
        # cashtoken suffix
        catkn = ""
        if scriptcode.startswith(OpCodes.OP_TOKENPREFIX.binary):
            catkn = "-CATKN"
            stream = io.BytesIO(scriptcode[33:])

            token_bitfield = stream.read(1).hex()
            # 4 bit prefix
            _ = bin(int(token_bitfield[0], 16))[2:]
            _ = "0" * (4 - len(_)) + _
            prefix_structure = [bit == "1" for bit in _]
            if prefix_structure[1]:
                # has commitment length
                length = varint_to_int(stream)
                _ = stream.read(length)
            if prefix_structure[3]:
                # has amount
                _ = varint_to_int(stream)
            # only use locking script for the rest
            scriptcode = stream.read()

        # P2PKH
        if len(scriptcode) == 25:
            if scriptcode.startswith(
                OpCodes.OP_DUP.binary
                + OpCodes.OP_HASH160.binary
                + OpCodes.OP_DATA_20.binary
            ) and scriptcode.endswith(
                OpCodes.OP_EQUALVERIFY.binary + OpCodes.OP_CHECKSIG.binary
            ):
                return cls("P2PKH" + catkn, list(scriptcode[3:23]))
        # P2SH20
        if len(scriptcode) == 23:
            if scriptcode.startswith(
                OpCodes.OP_HASH160.binary + OpCodes.OP_DATA_20.binary
            ) and scriptcode.endswith(OpCodes.OP_EQUAL.binary):
                return cls("P2SH20" + catkn, list(scriptcode[2:22]))
        # P2SH32
        if len(scriptcode) == 35:
            if scriptcode.startswith(
                OpCodes.OP_HASH256.binary + OpCodes.OP_DATA_32.binary
            ) and scriptcode.endswith(OpCodes.OP_EQUAL.binary):
                return cls("P2SH32" + catkn, list(scriptcode[2:34]))
        raise ValueError("Unknown script")

    @staticmethod
    def from_string(address):
        """
        Generate Address from a cashadress string

        :param scriptcode: The cashaddress string
        :type scriptcode: ``str``
        :returns: Instance of :class:~bitcash.cashaddress.Address
        """
        try:
            address = str(address)
        except Exception:
            raise InvalidAddress("Expected string as input")

        if address.upper() != address and address.lower() != address:
            raise InvalidAddress(
                "Cash address contains uppercase and lowercase characters"
            )

        address = address.lower()
        colon_count = address.count(":")
        if colon_count == 0:
            raise InvalidAddress("Cash address is missing prefix")
        if colon_count > 1:
            raise InvalidAddress("Cash address contains more than one colon character")

        prefix, base32string = address.split(":")
        decoded = b32decode(base32string)

        if not verify_checksum(prefix, decoded):
            raise InvalidAddress(
                "Bad cash address checksum for address {}".format(address)
            )
        converted = convertbits(decoded, 5, 8)

        try:
            version = Address.ADDRESS_TYPES[converted[0]]
        except Exception:
            raise InvalidAddress("Could not determine address version")

        version += Address.VERSION_SUFFIXES[prefix]

        payload = converted[1:-6]
        return Address(version, payload)


def parse_cashaddress(data):
    """Parse CashAddress address URI, with params attached

    :param data: Cashaddress uri to be parsed
    :type data: `str`
    :returns: cashaddress address, and parameters
    :rtype: (`str`, `dict`)

    >>> parse_cashaddress(
            'bchtest:qzvsaasdvw6mt9j2rs3gyps673gj86flev3z0s40ln?'
            'amount=0.1337&label=Satoshi-Nakamoto&message=Donation%20xyz'
        )
    (<bitcash.cashaddress.Address>,
     {'amount': '0.1337',
      'label': 'Satoshi-Nakamoto',
      'message': 'Donation xyz'
     }
    )
    >>> parse_cashaddress(
            'bchtest:?label=Satoshi-Nakamoto&message=Donation%20xyz'
        )
    (None,
     {'label': 'Satoshi-Nakamoto',
      'message': 'Donation xyz'
     }
    )
    """
    import urllib

    uri = urllib.parse.urlparse(data)
    if uri.scheme not in Address.VERSION_SUFFIXES:
        raise InvalidAddress("Invalid address scheme")

    if uri.path == "":
        address = None
    else:
        address = Address.from_string(f"{uri.scheme}:{uri.path}")
    query = urllib.parse.parse_qs(uri.query)

    for key, values in query.items():
        if len(values) == 1:
            query[key] = values[0]

    return address, query


def generate_cashaddress(address, params=None):
    """Generates cashaddress uri from address and params

    :param address: cashaddress
    :type address: `str`
    :param params: dictionary of parameters to be attached
    :type params: `dict`
    :returns: cashaddress uri
    :rtype: str

    >>> generate_cashaddress(
            "bitcoincash:qzfyvx77v2pmgc0vulwlfkl3uzjgh5gnmqk5hhyaa6",
            {
                "amount": 0.1,
            }
    )
    "bitcoincash:qzfyvx77v2pmgc0vulwlfkl3uzjgh5gnmqk5hhyaa6?amount=0.1"
    >>> generate_cashaddress(
            "bitcoincash:",
            {"message": "Satoshi Nakamoto"}
    )
    "bitcoincash:?message=Satoshi%20Nakamoto"
    """
    import urllib

    uri = urllib.parse.urlparse(address)
    if uri.path != "":
        # testing address
        _ = Address.from_string(f"{uri.scheme}:{uri.path}")
    elif uri.scheme not in Address.VERSION_SUFFIXES:
        raise InvalidAddress("Invalid address scheme")

    if params is None:
        return uri.geturl()

    param_list = []
    for key, values in params.items():
        if isinstance(values, str) or not hasattr(values, "__iter__"):
            values = [values]
        for value in values:
            param_list.append((key, value))

    query = urllib.parse.urlencode(param_list)
    uri = uri._replace(query=query)

    return uri.geturl()
