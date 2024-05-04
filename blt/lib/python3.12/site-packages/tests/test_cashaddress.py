import pytest

from bitcash.cashaddress import (
    Address,
    convertbits,
    generate_cashaddress,
    parse_cashaddress,
)
from bitcash.exceptions import InvalidAddress

from .samples import (
    PUBKEY_HASH,
    PUBKEY_HASH_COMPRESSED,
    BITCOIN_ADDRESS,
    BITCOIN_ADDRESS_COMPRESSED,
    BITCOIN_ADDRESS_TEST,
    BITCOIN_ADDRESS_TEST_COMPRESSED,
    BITCOIN_ADDRESS_REGTEST,
    BITCOIN_ADDRESS_REGTEST_COMPRESSED,
    BITCOIN_CASHADDRESS,
    BITCOIN_CASHADDRESS_COMPRESSED,
    BITCOIN_CASHADDRESS_TEST,
    BITCOIN_CASHADDRESS_TEST_COMPRESSED,
    BITCOIN_CASHADDRESS_REGTEST,
    BITCOIN_CASHADDRESS_REGTEST_COMPRESSED,
    CONVERT_BITS_INVALID_DATA_PAYLOAD,
    CONVERT_BITS_NO_PAD_PAYLOAD,
    CONVERT_BITS_NO_PAD_RETURN,
    BITCOIN_CASHADDRESS_PAY2SH20,
    BITCOIN_CASHADDRESS_PAY2SH32,
    BITCOIN_CASHADDRESS_CATKN,
    PREFIX_AMOUNT,
    PREFIX_CAPABILITY,
    PREFIX_CAPABILITY_AMOUNT,
    PREFIX_CAPABILITY_COMMITMENT,
    PREFIX_CAPABILITY_COMMITMENT_AMOUNT,
)


class BadStr:
    # Class needed to raise exception on str()
    def __str__(self):
        raise Exception("Bad string")


class TestAddress:
    def test_from_string_mainnet(self):
        # Test decoding from cashaddress into public hash
        assert bytes(Address.from_string(BITCOIN_CASHADDRESS).payload) == PUBKEY_HASH
        assert (
            bytes(Address.from_string(BITCOIN_CASHADDRESS_COMPRESSED).payload)
            == PUBKEY_HASH_COMPRESSED
        )

        # Legacy addresses
        with pytest.raises(InvalidAddress):
            Address.from_string(BITCOIN_ADDRESS)
        with pytest.raises(InvalidAddress):
            Address.from_string(BITCOIN_ADDRESS_COMPRESSED)

    def test_from_string_testnet(self):
        assert (
            bytes(Address.from_string(BITCOIN_CASHADDRESS_TEST).payload) == PUBKEY_HASH
        )
        assert (
            bytes(Address.from_string(BITCOIN_CASHADDRESS_TEST_COMPRESSED).payload)
            == PUBKEY_HASH_COMPRESSED
        )

        # Legacy addresses
        with pytest.raises(InvalidAddress):
            Address.from_string(BITCOIN_ADDRESS_TEST)
        with pytest.raises(InvalidAddress):
            Address.from_string(BITCOIN_ADDRESS_TEST_COMPRESSED)

    def test_from_string_regtest(self):
        assert (
            bytes(Address.from_string(BITCOIN_CASHADDRESS_REGTEST).payload)
            == PUBKEY_HASH
        )
        assert (
            bytes(Address.from_string(BITCOIN_CASHADDRESS_REGTEST_COMPRESSED).payload)
            == PUBKEY_HASH_COMPRESSED
        )

        # Legacy addresses
        with pytest.raises(InvalidAddress):
            Address.from_string(BITCOIN_ADDRESS_REGTEST)
        with pytest.raises(InvalidAddress):
            Address.from_string(BITCOIN_ADDRESS_REGTEST_COMPRESSED)

    def test_from_string_unexpected(self):
        # Test unexpected values
        with pytest.raises(InvalidAddress):
            Address.from_string(42)
        with pytest.raises(InvalidAddress):
            Address.from_string(0.999)
        with pytest.raises(InvalidAddress):
            Address.from_string(True)
        with pytest.raises(InvalidAddress):
            Address.from_string(False)
        with pytest.raises(InvalidAddress):
            Address.from_string(
                "bitcoincash:qzFyVx77v2pmgc0vulwlfkl3Uzjgh5gnMqk5hhyaa6"
            )
        with pytest.raises(InvalidAddress):
            Address.from_string(
                "bitcoincash:qzfyvx77v2pmgc0vulwlfkl3uzjgh5gnmqk5hhyba6"
            )
        with pytest.raises(InvalidAddress):
            Address.from_string("Hello world!")
        with pytest.raises(InvalidAddress, match="Expected string as input"):
            Address.from_string(BadStr())
        with pytest.raises(InvalidAddress):
            Address.from_string("bchreg::1234")
        with pytest.raises(InvalidAddress, match="Could not determine address version"):
            Address.from_string(
                "bitcoincash:qxfyvx77v2pmgc0vulwlfkl3uzjgh5gnmqedjjrtq6"
            )

    def test_address_mainnet(self):
        assert Address(payload=list(PUBKEY_HASH), version="P2PKH").payload == list(
            PUBKEY_HASH
        )
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH").prefix == "bitcoincash"
        )
        assert Address(payload=list(PUBKEY_HASH), version="P2PKH").version == "P2PKH"

    def test_address_testnet(self):
        assert Address(
            payload=list(PUBKEY_HASH), version="P2PKH-TESTNET"
        ).payload == list(PUBKEY_HASH)
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-TESTNET").prefix
            == "bchtest"
        )
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-TESTNET").version
            == "P2PKH-TESTNET"
        )

    def test_address_regtest(self):
        assert Address(
            payload=list(PUBKEY_HASH), version="P2PKH-REGTEST"
        ).payload == list(PUBKEY_HASH)
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-REGTEST").prefix
            == "bchreg"
        )
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-REGTEST").version
            == "P2PKH-REGTEST"
        )

    def test_address_unexpected(self):
        with pytest.raises(ValueError):
            assert (
                Address(payload=list(PUBKEY_HASH), version="P2KPH").cash_address()
                == BITCOIN_CASHADDRESS
            )

    def test_cashaddress_mainnet(self):
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH").cash_address()
            == BITCOIN_CASHADDRESS
        )

    def test_cashaddress_testnet(self):
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-TESTNET").cash_address()
            == BITCOIN_CASHADDRESS_TEST
        )

    def test_cashaddress_regtest(self):
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-REGTEST").cash_address()
            == BITCOIN_CASHADDRESS_REGTEST
        )

    def test_cashaddress_incorrect_network(self):
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH").cash_address()
            != BITCOIN_CASHADDRESS_TEST
        )
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH").cash_address()
            != BITCOIN_CASHADDRESS_REGTEST
        )
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-TESTNET").cash_address()
            != BITCOIN_CASHADDRESS
        )
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-TESTNET").cash_address()
            != BITCOIN_CASHADDRESS_REGTEST
        )
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-REGTEST").cash_address()
            != BITCOIN_CASHADDRESS
        )
        assert (
            Address(payload=list(PUBKEY_HASH), version="P2PKH-REGTEST").cash_address()
            != BITCOIN_CASHADDRESS_TEST
        )

    def test_convert_bits_invalid_data(self):
        assert convertbits(CONVERT_BITS_INVALID_DATA_PAYLOAD, 8, 5) is None

    def test_convert_bits_no_data(self):
        assert convertbits([], 8, 5) == []

    def test_convert_bits_no_data_no_pad(self):
        assert convertbits([], 0, 1, pad=False) is None

    def test_convert_bits_no_pad(self):
        assert (
            convertbits(CONVERT_BITS_NO_PAD_PAYLOAD, 8, 5, pad=False)
            == CONVERT_BITS_NO_PAD_RETURN
        )

    def test_address_str(self):
        assert (
            str(Address(version="P2PKH", payload=[]))
            == "version: P2PKH\npayload: []\nprefix: bitcoincash"
        )

    def test_eq(self):
        address = Address.from_string(BITCOIN_CASHADDRESS)
        assert address == BITCOIN_CASHADDRESS
        assert address == address
        with pytest.raises(ValueError):
            address == 1

    def test_to_from_script(self):
        address = Address.from_string(BITCOIN_CASHADDRESS)
        assert address == Address.from_script(address.scriptcode)

        address = Address.from_string(BITCOIN_CASHADDRESS_PAY2SH20)
        assert address == Address.from_script(address.scriptcode)

        address = Address.from_string(BITCOIN_CASHADDRESS_PAY2SH32)
        assert address == Address.from_script(address.scriptcode)

        # cashtoken
        address = Address.from_string(BITCOIN_CASHADDRESS)
        address_catkn = Address.from_string(BITCOIN_CASHADDRESS_CATKN)
        # no cashtoken data
        assert address == Address.from_script(address_catkn.scriptcode)
        # with cashtoken data
        for script in [
            PREFIX_AMOUNT,
            PREFIX_CAPABILITY,
            PREFIX_CAPABILITY_AMOUNT,
            PREFIX_CAPABILITY_COMMITMENT,
            PREFIX_CAPABILITY_COMMITMENT_AMOUNT,
        ]:
            assert address_catkn == Address.from_script(
                script + address_catkn.scriptcode
            )


def test_parse_cashaddress():
    # good address
    address, params = parse_cashaddress(
        BITCOIN_CASHADDRESS + "?amount=0.1337&label=Satoshi"
    )
    assert address.cash_address() == BITCOIN_CASHADDRESS
    assert params == {"amount": "0.1337", "label": "Satoshi"}

    address, params = parse_cashaddress(
        BITCOIN_CASHADDRESS + "?amount=0.1337&label=Satoshi%20a&label=Satoshi%20b"
    )
    assert address.cash_address() == BITCOIN_CASHADDRESS
    assert params == {"amount": "0.1337", "label": ["Satoshi a", "Satoshi b"]}

    address, params = parse_cashaddress(BITCOIN_CASHADDRESS + "")
    assert address.cash_address() == BITCOIN_CASHADDRESS
    assert params == {}

    address, _ = parse_cashaddress("bchtest:")
    assert address is None

    # bad address
    with pytest.raises(InvalidAddress):
        address, params = parse_cashaddress(
            "bchtest:abc" + "?amount=0.1337&label=Satoshi&label=Satoshi"
        )

    with pytest.raises(InvalidAddress):
        address, params = parse_cashaddress(
            "bch:" + "?amount=0.1337&label=Satoshi&label=Satoshi"
        )


def test_generate_cashaddress():
    assert generate_cashaddress(BITCOIN_CASHADDRESS) == BITCOIN_CASHADDRESS

    cashaddress = generate_cashaddress("bitcoincash:", {"message": "Satoshi Nakamoto"})
    assert cashaddress == "bitcoincash:?message=Satoshi+Nakamoto"
    cashaddress = generate_cashaddress(
        BITCOIN_CASHADDRESS,
        {"amount": 0.1337, "data": ["a", 1], "message": "Satoshi Nakamoto"},
    )
    assert cashaddress == (
        BITCOIN_CASHADDRESS + "?amount=0.1337&data=a&data=1&message=Satoshi+Nakamoto"
    )

    with pytest.raises(InvalidAddress):
        generate_cashaddress("bch:")

    with pytest.raises(InvalidAddress):
        generate_cashaddress(BITCOIN_CASHADDRESS[:-1])
