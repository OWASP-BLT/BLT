import pytest
from bitcash import crypto
from _pytest.monkeypatch import MonkeyPatch

from bitcash.format import (
    address_to_public_key_hash,
    bytes_to_wif,
    coords_to_public_key,
    point_to_public_key,
    public_key_to_coords,
    public_key_to_address,
    verify_sig,
    wif_checksum_check,
    wif_to_bytes,
    hex_to_asm,
    address_to_cashtokenaddress,
    cashtokenaddress_to_address,
)
from .samples import (
    BITCOIN_ADDRESS,
    BITCOIN_ADDRESS_COMPRESSED,
    BITCOIN_CASHADDRESS_CATKN,
    BITCOIN_CASHADDRESS_PAY2SH20,
    BITCOIN_CASHADDRESS_PAY2SH32,
    BITCOIN_ADDRESS_TEST,
    BITCOIN_CASHADDRESS_TEST_CATKN,
    BITCOIN_ADDRESS_TEST_COMPRESSED,
    BITCOIN_ADDRESS_REGTEST,
    BITCOIN_ADDRESS_REGTEST_COMPRESSED,
    BITCOIN_CASHADDRESS_TEST_PAY2SH20,
    BITCOIN_CASHADDRESS_TEST_PAY2SH32,
    BITCOIN_CASHADDRESS_REGTEST,
    BITCOIN_CASHADDRESS_REGTEST_COMPRESSED,
    BITCOIN_CASHADDRESS_REGTEST_PAY2SH20,
    PRIVATE_KEY_BYTES,
    PUBKEY_HASH,
    PUBKEY_HASH_P2SH20,
    PUBKEY_HASH_P2SH32,
    BITCOIN_CASHADDRESS,
    BITCOIN_CASHADDRESS_TEST,
    BITCOIN_CASHADDRESS_TEST_COMPRESSED,
    PUBKEY_HASH_COMPRESSED,
    PUBLIC_KEY_COMPRESSED,
    PUBLIC_KEY_UNCOMPRESSED,
    PUBLIC_KEY_X,
    PUBLIC_KEY_Y,
    BITCOIN_CASHADDRESS_COMPRESSED,
    WALLET_FORMAT_COMPRESSED_MAIN,
    WALLET_FORMAT_COMPRESSED_TEST,
    WALLET_FORMAT_MAIN,
    WALLET_FORMAT_TEST,
    WALLET_FORMAT_REGTEST,
)

VALID_SIGNATURE = (
    b"0E\x02!\x00\xd7y\xe0\xa4\xfc\xea\x88\x18sDit\x9d\x01\xf3"
    b"\x03\xa0\xceO\xab\x80\xe8PY.*\xda\x11w|\x9fq\x02 u\xdaR"
    b"\xd8\x84a\xad\xfamN\xae&\x91\xfd\xd6\xbd\xe1\xb0e\xfe\xf4"
    b"\xc5S\xd9\x02D\x1d\x0b\xba\xe0=@"
)
INVALID_SIGNATURE = (
    b"0D\x02 `\x03D^\xa7\xab\xdc\xa6_\xb6&\xcbN\xc8S\xa4\xcf"
    b"\x9a8\x02\x99\xc4\xe9\x02\xb3\x14k\xfa\x15J\xb9\x03\x02"
    b" !\xfd\xb2\xa0:\xb3\xba\xb1\xdc\x1a]ZWb\xa5\x9d\x8a5\x1c"
    b"\xaeQ.\xa7`\xf6V\x11\xf1\xe0iJ7"
)
SIGNATURE_HIGH_S = (
    b'0E\x02 \x18NeS,"r\x1e\x01?\xa5\xa8C\xe4\xba\x07x \xc9\xf6'
    b"\x8fe\x17\xa3\x03'\xac\xd8\x97\x97\x1b\xd0\x02!\x00\xdc^"
    b"\xf2M\xe7\x0e\xbaz\xd3\xa3\x94\xcc\xef\x17\x04\xb2\xfb0!"
    b"\n\xc3\x1fa3\x83\x01\xc9\xbf\xbd\r)\x82"
)
DATA = b"data"


class TestVerifySig:
    def test_valid(self):
        assert verify_sig(VALID_SIGNATURE, DATA, PUBLIC_KEY_COMPRESSED)

    def test_invalid(self):
        assert not verify_sig(INVALID_SIGNATURE, DATA, PUBLIC_KEY_COMPRESSED)


class TestBytesToWIF:
    def test_mainnet(self):
        assert bytes_to_wif(PRIVATE_KEY_BYTES) == WALLET_FORMAT_MAIN

    def test_testnet(self):
        assert bytes_to_wif(PRIVATE_KEY_BYTES, version="test") == WALLET_FORMAT_TEST

    def test_regtest(self):
        assert (
            bytes_to_wif(PRIVATE_KEY_BYTES, version="regtest") == WALLET_FORMAT_REGTEST
        )

    def test_compressed(self):
        assert (
            bytes_to_wif(PRIVATE_KEY_BYTES, compressed=True)
            == WALLET_FORMAT_COMPRESSED_MAIN
        )

    def test_compressed_testnet(self):
        assert (
            bytes_to_wif(PRIVATE_KEY_BYTES, version="test", compressed=True)
            == WALLET_FORMAT_COMPRESSED_TEST
        )


class TestWIFToBytes:
    def test_mainnet(self):
        assert wif_to_bytes(WALLET_FORMAT_MAIN) == (PRIVATE_KEY_BYTES, False, "main")

    def test_testnet(self):
        assert wif_to_bytes(WALLET_FORMAT_TEST) == (PRIVATE_KEY_BYTES, False, "test")

    def test_regtest(self):
        assert wif_to_bytes(WALLET_FORMAT_REGTEST, regtest=True) == (
            PRIVATE_KEY_BYTES,
            False,
            "regtest",
        )

    def test_compressed(self):
        assert wif_to_bytes(WALLET_FORMAT_COMPRESSED_MAIN) == (
            PRIVATE_KEY_BYTES,
            True,
            "main",
        )

    def test_testnet_compressed(self):
        assert wif_to_bytes(WALLET_FORMAT_COMPRESSED_TEST) == (
            PRIVATE_KEY_BYTES,
            True,
            "test",
        )

    def test_invalid_network(self):
        with pytest.raises(ValueError):
            wif_to_bytes(BITCOIN_ADDRESS)


class TestWIFChecksumCheck:
    def test_wif_checksum_check_main_success(self):
        assert wif_checksum_check(WALLET_FORMAT_MAIN)

    def test_wif_checksum_check_test_success(self):
        assert wif_checksum_check(WALLET_FORMAT_TEST)

    def test_wif_checksum_check_regtest_success(self):
        assert wif_checksum_check(WALLET_FORMAT_REGTEST)

    def test_wif_checksum_check_compressed_success(self):
        assert wif_checksum_check(WALLET_FORMAT_COMPRESSED_MAIN)

    def test_wif_checksum_check_test_compressed_success(self):
        assert wif_checksum_check(WALLET_FORMAT_COMPRESSED_TEST)

    def test_wif_checksum_check_decode_failure(self):
        assert not wif_checksum_check(BITCOIN_ADDRESS[:-1])

    def test_wif_checksum_check_other_failure(self):
        assert not wif_checksum_check(BITCOIN_ADDRESS)


class TestPublicKeyToCoords:
    def test_public_key_to_coords_compressed(self):
        assert public_key_to_coords(PUBLIC_KEY_COMPRESSED) == (
            PUBLIC_KEY_X,
            PUBLIC_KEY_Y,
        )

    def test_public_key_to_coords_uncompressed(self):
        assert public_key_to_coords(PUBLIC_KEY_UNCOMPRESSED) == (
            PUBLIC_KEY_X,
            PUBLIC_KEY_Y,
        )

    def test_public_key_to_coords_incorrect_length(self):
        with pytest.raises(ValueError):
            public_key_to_coords(PUBLIC_KEY_COMPRESSED[1:])


class TestPublicKeyToAddress:
    def test_public_key_to_address_compressed(self):
        assert (
            public_key_to_address(PUBLIC_KEY_COMPRESSED)
            == BITCOIN_CASHADDRESS_COMPRESSED
        )

    def test_public_key_to_address_uncompressed(self):
        assert public_key_to_address(PUBLIC_KEY_UNCOMPRESSED) == BITCOIN_CASHADDRESS

    def test_public_key_to_address_incorrect_length(self):
        with pytest.raises(ValueError):
            public_key_to_address(PUBLIC_KEY_COMPRESSED[:-1])

    def test_public_key_to_address_incorrect_version(self):
        with pytest.raises(ValueError):
            public_key_to_address(PUBLIC_KEY_COMPRESSED, "incorrect-version")

    def test_public_key_to_address_test_compressed(self):
        assert (
            public_key_to_address(PUBLIC_KEY_COMPRESSED, version="test")
            == BITCOIN_CASHADDRESS_TEST_COMPRESSED
        )

    def test_public_key_to_address_test_uncompressed(self):
        assert (
            public_key_to_address(PUBLIC_KEY_UNCOMPRESSED, version="test")
            == BITCOIN_CASHADDRESS_TEST
        )

    def test_public_key_to_address_regtest_compressed(self):
        assert (
            public_key_to_address(PUBLIC_KEY_COMPRESSED, version="regtest")
            == BITCOIN_CASHADDRESS_REGTEST_COMPRESSED
        )

    def test_public_key_to_address_regtest_uncompressed(self):
        assert (
            public_key_to_address(PUBLIC_KEY_UNCOMPRESSED, version="regtest")
            == BITCOIN_CASHADDRESS_REGTEST
        )


def mock_hashlib(name, data):
    """Force ValueError from hashlib.new to fallback to pythonic ripemd160"""
    raise ValueError()


class TestPublicKeyToAddress_pythonic_ripemd:
    def setup_method(self):
        self.monkeypatch = MonkeyPatch()

    def test_public_key_to_address_compressed(self):
        self.monkeypatch.setattr(crypto, "new", mock_hashlib)
        assert (
            public_key_to_address(PUBLIC_KEY_COMPRESSED)
            == BITCOIN_CASHADDRESS_COMPRESSED
        )

    def test_public_key_to_address_uncompressed(self):
        self.monkeypatch.setattr(crypto, "new", mock_hashlib)
        assert public_key_to_address(PUBLIC_KEY_UNCOMPRESSED) == BITCOIN_CASHADDRESS

    def test_public_key_to_address_incorrect_length(self):
        self.monkeypatch.setattr(crypto, "new", mock_hashlib)
        with pytest.raises(ValueError):
            public_key_to_address(PUBLIC_KEY_COMPRESSED[:-1])

    def test_public_key_to_address_incorrect_version(self):
        self.monkeypatch.setattr(crypto, "new", mock_hashlib)
        with pytest.raises(ValueError):
            public_key_to_address(PUBLIC_KEY_COMPRESSED, "incorrect-version")

    def test_public_key_to_address_test_compressed(self):
        self.monkeypatch.setattr(crypto, "new", mock_hashlib)
        assert (
            public_key_to_address(PUBLIC_KEY_COMPRESSED, version="test")
            == BITCOIN_CASHADDRESS_TEST_COMPRESSED
        )

    def test_public_key_to_address_test_uncompressed(self):
        self.monkeypatch.setattr(crypto, "new", mock_hashlib)
        assert (
            public_key_to_address(PUBLIC_KEY_UNCOMPRESSED, version="test")
            == BITCOIN_CASHADDRESS_TEST
        )

    def test_public_key_to_address_regtest_compressed(self):
        self.monkeypatch.setattr(crypto, "new", mock_hashlib)
        assert (
            public_key_to_address(PUBLIC_KEY_COMPRESSED, version="regtest")
            == BITCOIN_CASHADDRESS_REGTEST_COMPRESSED
        )

    def test_public_key_to_address_regtest_uncompressed(self):
        self.monkeypatch.setattr(crypto, "new", mock_hashlib)
        assert (
            public_key_to_address(PUBLIC_KEY_UNCOMPRESSED, version="regtest")
            == BITCOIN_CASHADDRESS_REGTEST
        )


class TestCoordsToPublicKey:
    def test_coords_to_public_key_compressed(self):
        assert coords_to_public_key(PUBLIC_KEY_X, PUBLIC_KEY_Y) == PUBLIC_KEY_COMPRESSED

    def test_coords_to_public_key_uncompressed(self):
        assert (
            coords_to_public_key(PUBLIC_KEY_X, PUBLIC_KEY_Y, compressed=False)
            == PUBLIC_KEY_UNCOMPRESSED
        )


def test_point_to_public_key():
    class Point:
        x = PUBLIC_KEY_X
        y = PUBLIC_KEY_Y

    assert point_to_public_key(Point) == coords_to_public_key(Point.x, Point.y)


def test_address_to_public_key_hash():
    assert address_to_public_key_hash(BITCOIN_CASHADDRESS) == PUBKEY_HASH
    assert address_to_public_key_hash(BITCOIN_CASHADDRESS_TEST) == PUBKEY_HASH
    assert (
        address_to_public_key_hash(BITCOIN_CASHADDRESS_COMPRESSED)
        == PUBKEY_HASH_COMPRESSED
    )
    assert (
        address_to_public_key_hash(BITCOIN_CASHADDRESS_TEST_COMPRESSED)
        == PUBKEY_HASH_COMPRESSED
    )
    assert address_to_public_key_hash(BITCOIN_CASHADDRESS_REGTEST) == PUBKEY_HASH
    assert (
        address_to_public_key_hash(BITCOIN_CASHADDRESS_REGTEST_COMPRESSED)
        == PUBKEY_HASH_COMPRESSED
    )
    assert (
        address_to_public_key_hash(BITCOIN_CASHADDRESS_PAY2SH20) == PUBKEY_HASH_P2SH20
    )
    assert (
        address_to_public_key_hash(BITCOIN_CASHADDRESS_TEST_PAY2SH20)
        == PUBKEY_HASH_P2SH20
    )
    assert (
        address_to_public_key_hash(BITCOIN_CASHADDRESS_PAY2SH32) == PUBKEY_HASH_P2SH32
    )
    assert (
        address_to_public_key_hash(BITCOIN_CASHADDRESS_TEST_PAY2SH32)
        == PUBKEY_HASH_P2SH32
    )
    assert (
        address_to_public_key_hash(BITCOIN_CASHADDRESS_REGTEST_PAY2SH20)
        == PUBKEY_HASH_P2SH20
    )


def test_to_and_from_cashtokenaddress():
    cashtokenaddress = address_to_cashtokenaddress(BITCOIN_CASHADDRESS)
    assert cashtokenaddress == BITCOIN_CASHADDRESS_CATKN
    assert cashtokenaddress_to_address(cashtokenaddress) == BITCOIN_CASHADDRESS
    cashtokenaddress = address_to_cashtokenaddress(BITCOIN_CASHADDRESS_TEST)
    assert cashtokenaddress == BITCOIN_CASHADDRESS_TEST_CATKN
    assert cashtokenaddress_to_address(cashtokenaddress) == BITCOIN_CASHADDRESS_TEST

    # test vectors from https://github.com/bitjson/cashtokens
    address = address_to_cashtokenaddress(
        "bitcoincash:qr7fzmep8g7h7ymfxy74lgc0v950j3r2959lhtxxsl"
    )
    assert "bitcoincash:zr7fzmep8g7h7ymfxy74lgc0v950j3r295z4y4gq0v" == address
    address = address_to_cashtokenaddress(
        "bchtest:qr7fzmep8g7h7ymfxy74lgc0v950j3r295pdnvy3hr"
    )
    assert "bchtest:zr7fzmep8g7h7ymfxy74lgc0v950j3r295x8qj2hgs" == address
    address = address_to_cashtokenaddress(
        "bchreg:qr7fzmep8g7h7ymfxy74lgc0v950j3r295m39d8z59"
    )
    assert "bchreg:zr7fzmep8g7h7ymfxy74lgc0v950j3r295umknfytk" == address
    address = address_to_cashtokenaddress(
        "bitcoincash:ppawqn2h74a4t50phuza84kdp3794pq3ccvm92p8sh"
    )
    assert "bitcoincash:rpawqn2h74a4t50phuza84kdp3794pq3cct3k50p0y" == address
    address = address_to_cashtokenaddress(
        "bitcoincash:pvqqqqqqqqqqqqqqqqqqqqqqzg69v7ysqqqqqqqqqqqqqqqqqqqqqpkp7fqn0"
    )
    assert (
        "bitcoincash:rvqqqqqqqqqqqqqqqqqqqqqqzg69v7ysqqqqqqqqqqqqqqqqqqqqqn9alsp2y"
        == address
    )


def test_hex_to_asm():
    asm = hex_to_asm("76a9147ff07a9532d16a3fe14112e8c856093b81c25a6a88ac")
    assert asm == (
        "OP_DUP OP_HASH160 7ff07a9532d16a3fe14112e8c856093b81c25a6a"
        " OP_EQUALVERIFY OP_CHECKSIG"
    )
    asm = hex_to_asm(
        "6a0442434d52206b2000be5ce5527cd653c49cdba486e2fd0ec4214"
        "da2f71d7e56ad027b2139f448676973742e67697468756275736572"
        "636f6e74656e742e636f6d2f6d722d7a776574732f3834623030353"
        "7383038616632306466333932383135666232376434613636312f72"
        "6177"
    )
    assert asm == (
        "OP_RETURN 1380795202 6b2000be5ce5527cd653c49cdba486e2fd0"
        "ec4214da2f71d7e56ad027b2139f4 676973742e6769746875627573"
        "6572636f6e74656e742e636f6d2f6d722d7a776574732f3834623030"
        "3537383038616632306466333932383135666232376434613636312f"
        "726177"
    )
    # empty test
    asm = hex_to_asm("6a4c00147ff07a9532d16a3fe14112e8c856093b81c25a6a")
    assert asm == ("OP_RETURN  7ff07a9532d16a3fe14112e8c856093b81c25a6a")
