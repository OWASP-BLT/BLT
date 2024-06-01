from coincurve import verify_signature as _vs

from bitcash.base58 import b58decode_check, b58encode_check
from bitcash.cashaddress import Address
from bitcash.crypto import ripemd160_sha256
from bitcash.curve import x_to_y
from bitcash.op import OpCodes

MAIN_PUBKEY_HASH = b"\x00"
MAIN_SCRIPT_HASH = b"\x05"
MAIN_PRIVATE_KEY = b"\x80"
MAIN_BIP32_PUBKEY = b"\x04\x88\xb2\x1e"
MAIN_BIP32_PRIVKEY = b"\x04\x88\xad\xe4"

TEST_PUBKEY_HASH = b"\x6f"
TEST_SCRIPT_HASH = b"\xc4"
TEST_PRIVATE_KEY = b"\xef"
TEST_BIP32_PUBKEY = b"\x045\x87\xcf"
TEST_BIP32_PRIVKEY = b"\x045\x83\x94"

REGTEST_PUBKEY_HASH = TEST_PUBKEY_HASH
REGTEST_SCRIPT_HASH = TEST_SCRIPT_HASH
REGTEST_PRIVATE_KEY = TEST_PRIVATE_KEY
REGTEST_BIP32_PUBKEY = TEST_BIP32_PUBKEY
REGTEST_BIP32_PRIVKEY = TEST_BIP32_PRIVKEY

PUBLIC_KEY_UNCOMPRESSED = b"\x04"
PUBLIC_KEY_COMPRESSED_EVEN_Y = b"\x02"
PUBLIC_KEY_COMPRESSED_ODD_Y = b"\x03"
PRIVATE_KEY_COMPRESSED_PUBKEY = b"\x01"


def verify_sig(signature, data, public_key):
    """Verifies some data was signed by the owner of a public key.

    :param signature: The signature to verify.
    :type signature: ``bytes``
    :param data: The data that was supposedly signed.
    :type data: ``bytes``
    :param public_key: The public key.
    :type public_key: ``bytes``
    :returns: ``True`` if all checks pass, ``False`` otherwise.
    """
    return _vs(signature, data, public_key)


def address_to_public_key_hash(address):
    address = Address.from_string(address)

    if "P2PKH" not in address.version and "P2SH" not in address.version:
        # Bitcash currently only supports P2PKH, P2SH transaction outputs
        # others will raise ValueError
        raise ValueError("Bitcash currently only supports" " P2PKH/P2SH addresses")

    return bytes(address.payload)


def bytes_to_wif(private_key, version="main", compressed=False):
    if version == "test":
        prefix = TEST_PRIVATE_KEY
    elif version == "regtest":
        prefix = REGTEST_PRIVATE_KEY
    else:
        prefix = MAIN_PRIVATE_KEY

    if compressed:
        suffix = PRIVATE_KEY_COMPRESSED_PUBKEY
    else:
        suffix = b""

    private_key = prefix + private_key + suffix

    return b58encode_check(private_key)


def wif_to_bytes(wif, regtest=False):
    private_key = b58decode_check(wif)

    version = private_key[:1]

    if version == MAIN_PRIVATE_KEY:
        version = "main"
    elif version == TEST_PRIVATE_KEY:
        # Regtest and testnet WIF formats are identical, so we
        # check the 'regtest' flag and manually set the version
        if regtest:
            version = "regtest"
        else:
            version = "test"
    else:
        raise ValueError(
            f"{version} does not correspond to a mainnet,"
            f"testnet, nor regtest address."
        )

    # Remove version byte and, if present, compression flag.
    if len(wif) == 52 and private_key[-1] == 1:
        private_key, compressed = private_key[1:-1], True
    else:
        private_key, compressed = private_key[1:], False

    return private_key, compressed, version


def wif_checksum_check(wif):
    try:
        decoded = b58decode_check(wif)
    except ValueError:
        return False

    if decoded[:1] in (MAIN_PRIVATE_KEY, TEST_PRIVATE_KEY, REGTEST_PRIVATE_KEY):
        return True

    return False


def public_key_to_address(public_key, version="main"):
    # Currently Bitcash only support P2PKH (not P2SH) utxos
    VERSIONS = {"main": "P2PKH", "test": "P2PKH-TESTNET", "regtest": "P2PKH-REGTEST"}

    try:
        version = VERSIONS[version]
    except Exception:
        raise ValueError("Invalid version: {}".format(version))
    # 33 bytes compressed, 65 uncompressed.
    length = len(public_key)
    if length not in (33, 65):
        raise ValueError(f"{length} is an invalid length for a public key.")

    payload = list(ripemd160_sha256(public_key))
    address = Address(payload=payload, version=version)
    return address.cash_address()


def public_key_to_coords(public_key):
    length = len(public_key)

    if length == 33:
        flag, x = int.from_bytes(public_key[:1], "big"), int.from_bytes(
            public_key[1:], "big"
        )
        y = x_to_y(x, flag & 1)
    elif length == 65:
        x, y = int.from_bytes(public_key[1:33], "big"), int.from_bytes(
            public_key[33:], "big"
        )
    else:
        raise ValueError(f"{length} is an invalid length for a public key.")

    return x, y


def coords_to_public_key(x, y, compressed=True):
    if compressed:
        y = PUBLIC_KEY_COMPRESSED_ODD_Y if y & 1 else PUBLIC_KEY_COMPRESSED_EVEN_Y
        return y + x.to_bytes(32, "big")

    return PUBLIC_KEY_UNCOMPRESSED + x.to_bytes(32, "big") + y.to_bytes(32, "big")


def point_to_public_key(point, compressed=True):
    return coords_to_public_key(point.x, point.y, compressed)


def address_to_cashtokenaddress(address):
    """
    Converts regular cashaddress to cashtoken signalling address

    :param address: Cashaddress
    :type address: ``str``
    :returns: Cashtoken signalling cashaddress
    :rtype: ``str``
    """
    address = Address.from_string(address)
    if "CATKN" in address.version:
        return address.cash_address()
    version = address.version.split("-")
    version.insert(1, "CATKN")
    address.version = "-".join(version)
    return address.cash_address()


def cashtokenaddress_to_address(address):
    """
    Converts cashtoken signalling cashaddress to regular cashaddress

    :param address: Cashtoken signalling cashaddress
    :type address: ``str``
    :returns: Cashaddress
    :rtype: ``str``
    """
    address = Address.from_string(address)
    if "CATKN" not in address.version:
        return address.cash_address()
    version = address.version.split("-")
    version.pop(1)
    address.version = "-".join(version)
    return address.cash_address()


def hex_to_asm(data):
    def _add_value(next_len, indx):
        next_len *= 2  # hex byte
        # !TODO: add Signature hash type delineation
        value = data[indx : indx + next_len]
        if len(value) != next_len:
            raise RuntimeError("Data ended prematurely")
        indx += next_len
        return value, indx

    indx = 0
    out = []
    while indx < len(data):
        op_code = data[indx : indx + 2]
        op_code = OpCodes(int(op_code, 16))
        if op_code == OpCodes.OP_PUSHDATA1:
            indx += 2
            next_len = int(data[indx : indx + 2], 16)
            indx += 2
            value, indx = _add_value(next_len, indx)
        elif op_code == OpCodes.OP_PUSHDATA2:
            indx += 2
            a = data[indx : indx + 2]
            indx += 2
            b = data[indx : indx + 2]
            next_len = int(b + a, 16)
            indx += 2
            value, indx = _add_value(next_len, indx)
        elif op_code == OpCodes.OP_PUSHDATA4:
            indx += 2
            a = data[indx : indx + 2]
            indx += 2
            b = data[indx : indx + 2]
            indx += 2
            c = data[indx : indx + 2]
            indx += 2
            d = data[indx : indx + 2]
            next_len = int(d + c + b + a, 16)
            indx += 2
            value, indx = _add_value(next_len, indx)
        elif op_code.name.startswith("OP_DATA"):
            next_len = int(data[indx : indx + 2], 16)
            indx += 2
            value, indx = _add_value(next_len, indx)
            if next_len <= 8:
                # !TODO: check implementation
                value = str(int.from_bytes(bytes.fromhex(value), "little"))
        else:
            indx += 2
            value = op_code.name
        out.append(value)
    return " ".join(out)
