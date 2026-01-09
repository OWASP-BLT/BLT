import pytest

from bitcash.exceptions import InsufficientFunds
from bitcash.network.meta import Unspent
from bitcash.transaction import (
    TxIn,
    calc_txid,
    create_p2pkh_transaction,
    construct_input_block,
    construct_output_block,
    estimate_tx_fee,
    sanitize_tx_data,
)
from bitcash.op import OpCodes
from bitcash.cashaddress import Address
from bitcash.utils import hex_to_bytes
from bitcash.wallet import PrivateKey
from .samples import (
    WALLET_FORMAT_MAIN,
    BITCOIN_CASHADDRESS,
    BITCOIN_CASHADDRESS_CATKN,
    BITCOIN_CASHADDRESS_COMPRESSED,
    BITCOIN_CASHADDRESS_PAY2SH20,
    BITCOIN_CASHADDRESS_PAY2SH32,
)


RETURN_ADDRESS = BITCOIN_CASHADDRESS

FINAL_TX_1 = (
    "01000000018878399d83ec25c627cfbf753ff9ca3602373eac437ab2676154a"
    "3c2da23adf3010000008a473044022013d0751fb16eb7e1ac75aa799ebbfb55"
    "2bf112174f4a7eea689b8930cf582abc02206bc2082f38019476ecc3dc839fd"
    "eda87a70041f23f0843edd101792109a10c6e4141043d5c2875c9bd116875a7"
    "1a5db64cffcb13396b163d039b1d932782489180433476a4352a2add00ebb0d"
    "5c94c515b72eb10f1fd8f3f03b42f4a2b255bfc9aa9e3ffffffff0250c30000"
    "000000001976a91492461bde6283b461ece7ddf4dbf1e0a48bd113d888ac088"
    "8fc04000000001976a914990ef60d63b5b5964a1c2282061af45123e93fcb88"
    "ac00000000"
)

FINAL_TX_ID = "f7e1086edae26fee6ad5efcf9d2c2ff6126c468ddc3a35ed4df51ad557b56ce0"

INPUTS = [
    TxIn(
        (
            b"G0D\x02 E\xb7C\xdb\xaa\xaa,\xd1\xef\x0b\x914oVD\xe3-\xc7\x0c\xde\x05\t"
            b"\x1b7b\xd4\xca\xbbn\xbdq\x1a\x02 tF\x10V\xc2n\xfe\xac\x0bD\x8e\x7f\xa7"
            b"iw=\xd6\xe4Cl\xdeP\\\x8fl\xa60>\xfe1\xf0\x95\x01A\x04=\\(u\xc9\xbd\x11"
            b"hu\xa7\x1a]\xb6L\xff\xcb\x139k\x16=\x03\x9b\x1d\x93'\x82H\x91\x80C4v"
            b"\xa45**\xdd\x00\xeb\xb0\xd5\xc9LQ[r\xeb\x10\xf1\xfd\x8f?\x03\xb4/J+%["
            b"\xfc\x9a\xa9\xe3"
        ),
        b"\x8a",
        (
            b"\x88x9\x9d\x83\xec%\xc6'\xcf\xbfu?\xf9\xca6\x027>"
            b"\xacCz\xb2gaT\xa3\xc2\xda#\xad\xf3"
        ),
        b"\x01\x00\x00\x00",
        0,
    )
]
INPUT_BLOCK = (
    "8878399d83ec25c627cfbf753ff9ca3602373eac437ab2676154a3c2da23adf30"
    "10000008a473044022045b743dbaaaa2cd1ef0b91346f5644e32dc70cde05091b"
    "3762d4cabb6ebd711a022074461056c26efeac0b448e7fa769773dd6e4436cde5"
    "05c8f6ca6303efe31f0950141043d5c2875c9bd116875a71a5db64cffcb13396b"
    "163d039b1d932782489180433476a4352a2add00ebb0d5c94c515b72eb10f1fd8"
    "f3f03b42f4a2b255bfc9aa9e3ffffffff"
)
UNSPENTS = [
    Unspent(
        83727960,
        15,
        "76a91492461bde6283b461ece7ddf4dbf1e0a48bd113d888ac",
        "f3ad23dac2a3546167b27a43ac3e370236caf93f75bfcf27c625ec839d397888",
        1,
    )
]
OUTPUTS = [
    (
        Address.from_string(BITCOIN_CASHADDRESS).scriptcode,
        50000,
        None,
        None,
        None,
        None,
    ),
    (
        Address.from_string(BITCOIN_CASHADDRESS_COMPRESSED).scriptcode,
        83658760,
        None,
        None,
        None,
        None,
    ),
]
MESSAGES = [
    (OpCodes.OP_RETURN.binary + b"\x05" + b"hello", 0, None, None, None, None),
    (OpCodes.OP_RETURN.binary + b"\x05" + b"there", 0, None, None, None, None),
]
OUTPUT_BLOCK = (
    "50c30000000000001976a91492461bde6283b461ece7ddf4dbf1e0a48bd113d888ac"
    "0888fc04000000001976a914990ef60d63b5b5964a1c2282061af45123e93fcb88ac"
)

OUTPUT_BLOCK_TESTNET = (
    "50c30000000000001976a91492461bde6283b461ece7ddf4dbf1e0a48bd113d888ac"
    "0888fc04000000001976a914990ef60d63b5b5964a1c2282061af45123e93fcb88ac"
)

OUTPUT_BLOCK_MESSAGES = (
    "50c30000000000001976a91492461bde6283b461ece7ddf4dbf1e0a48bd113d888ac"
    "0888fc04000000001976a914990ef60d63b5b5964a1c2282061af45123e93fcb88ac"
    "0000000000000000076a0568656c6c6f"
    "0000000000000000076a057468657265"
)

OUTPUT_BLOCK_MESSAGE_PUSHDATA = (
    "50c30000000000001976a91492461bde6283b461ece7ddf4dbf1e0a48bd113d888ac"
    "0888fc04000000001976a914990ef60d63b5b5964a1c2282061af45123e93fcb88ac"
    "0000000000000000076a0568656c6c6f"
)

SIGNED_DATA = (
    b"\x85\xc7\xf6\xc6\x80\x13\xc2g\xd3t\x8e\xb8\xb4\x1f\xcc"
    b"\x92x~\n\x1a\xac\xc0\xf0\xff\xf7\xda\xfe0\xb7!6t"
)


class TestTxIn:
    def test_init(self):
        txin = TxIn(b"script", b"\x06", b"txid", b"\x04", 0, b"a")
        assert txin.script == b"script"
        assert txin.script_len == b"\x06"
        assert txin.txid == b"txid"
        assert txin.txindex == b"\x04"
        assert txin.token_prefix == b"a"

    def test_equality(self):
        txin1 = TxIn(b"script", b"\x06", b"txid", b"\x04", 0)
        txin2 = TxIn(b"script", b"\x06", b"txid", b"\x04", 0)
        txin3 = TxIn(b"script", b"\x06", b"txi", b"\x03", 0)
        assert txin1 == txin2
        assert txin1 != txin3

    def test_repr(self):
        txin = TxIn(b"script", b"\x06", b"txid", b"\x04", 0)
        assert repr(txin) == "TxIn(b'script', {}, b'txid', {}, 0, {})" "".format(
            repr(b"\x06"), repr(b"\x04"), repr(b"")
        )


class TestSanitizeTxData:
    def test_no_input(self):
        with pytest.raises(ValueError):
            sanitize_tx_data([], [], 70, BITCOIN_CASHADDRESS)

    def test_message(self):
        unspents_original = [Unspent(10000, 0, "", "", 0), Unspent(10000, 0, "", "", 0)]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 1000, "satoshi")]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=5,
            leftover=RETURN_ADDRESS,
            combine=True,
            message="hello",
        )

        assert len(outputs) == 3
        assert outputs[2][0] == OpCodes.OP_RETURN.binary + b"\x05" + b"hello"
        assert outputs[2][1] == 0

    def test_message_pushdata(self):
        unspents_original = [Unspent(10000, 0, "", "", 0), Unspent(10000, 0, "", "", 0)]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 1000, "satoshi")]

        BYTES = len(b"hello").to_bytes(1, byteorder="little") + b"hello"

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=5,
            leftover=RETURN_ADDRESS,
            combine=True,
            message=BYTES,
            custom_pushdata=True,
        )

        assert len(outputs) == 3
        assert outputs[2][0] == OpCodes.OP_RETURN.binary + b"\x05" + b"hello"
        assert outputs[2][1] == 0

    def test_fee_applied(self):
        unspents_original = [Unspent(1000, 0, "", "", 0), Unspent(1000, 0, "", "", 0)]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 2000, "satoshi")]

        with pytest.raises(InsufficientFunds):
            sanitize_tx_data(
                unspents_original,
                outputs_original,
                fee=1,
                leftover=RETURN_ADDRESS,
                combine=True,
                message=None,
            )

    def test_zero_remaining(self):
        unspents_original = [Unspent(1000, 0, "", "", 0), Unspent(1000, 0, "", "", 0)]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 2000, "satoshi")]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=0,
            leftover=RETURN_ADDRESS,
            combine=True,
            message=None,
        )

        assert unspents == unspents_original
        _ = Address.from_string(BITCOIN_CASHADDRESS_COMPRESSED).scriptcode
        assert outputs == [(_, 2000, None, None, None, None)]

    def test_combine_remaining(self):
        unspents_original = [Unspent(1000, 0, "", "", 0), Unspent(1000, 0, "", "", 0)]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 600, "satoshi")]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=0,
            leftover=RETURN_ADDRESS,
            combine=True,
            message=None,
        )

        assert unspents == unspents_original
        assert len(outputs) == 2
        assert outputs[1][0] == Address.from_string(RETURN_ADDRESS).scriptcode
        assert outputs[1][1] == 1400

    def test_combine_insufficient_funds(self):
        unspents_original = [Unspent(1000, 0, "", "", 0), Unspent(1000, 0, "", "", 0)]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 2500, "satoshi")]

        with pytest.raises(InsufficientFunds):
            sanitize_tx_data(
                unspents_original,
                outputs_original,
                fee=50,
                leftover=RETURN_ADDRESS,
                combine=True,
                message=None,
            )

    def test_no_combine_remaining(self):
        unspents_original = [Unspent(7000, 0, "", "", 0), Unspent(3000, 0, "", "", 0)]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 2000, "satoshi")]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=0,
            leftover=RETURN_ADDRESS,
            combine=False,
            message=None,
        )

        assert unspents == [Unspent(3000, 0, "", "", 0)]
        assert len(outputs) == 2
        assert outputs[1][0] == Address.from_string(RETURN_ADDRESS).scriptcode
        assert outputs[1][1] == 1000

    def test_no_combine_remaining_small_inputs(self):
        unspents_original = [
            Unspent(1500, 0, "", "", 0),
            Unspent(1600, 0, "", "", 0),
            Unspent(1700, 0, "", "", 0),
        ]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 2000, "satoshi")]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=0,
            leftover=RETURN_ADDRESS,
            combine=False,
            message=None,
        )
        assert unspents == [Unspent(1500, 0, "", "", 0), Unspent(1600, 0, "", "", 0)]
        assert len(outputs) == 2
        assert outputs[1][0] == Address.from_string(RETURN_ADDRESS).scriptcode
        assert outputs[1][1] == 1100

    def test_no_combine_with_fee(self):
        """
        Verify that unused unspents do not increase fee.
        """
        unspents_single = [Unspent(5000, 0, "", "", 0)]
        unspents_original = [Unspent(5000, 0, "", "", 0), Unspent(5000, 0, "", "", 0)]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 1000, "satoshi")]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=1,
            leftover=RETURN_ADDRESS,
            combine=False,
            message=None,
        )

        unspents_single, outputs_single = sanitize_tx_data(
            unspents_single,
            outputs_original,
            fee=1,
            leftover=RETURN_ADDRESS,
            combine=False,
            message=None,
        )

        assert unspents == [Unspent(5000, 0, "", "", 0)]
        assert unspents_single == [Unspent(5000, 0, "", "", 0)]
        assert len(outputs) == 2
        assert len(outputs_single) == 2
        assert outputs[1][0] == Address.from_string(RETURN_ADDRESS).scriptcode
        assert outputs_single[1][0] == Address.from_string(RETURN_ADDRESS).scriptcode
        assert outputs[1][1] == outputs_single[1][1]

    def test_no_combine_insufficient_funds(self):
        unspents_original = [Unspent(1000, 0, "", "", 0), Unspent(1000, 0, "", "", 0)]
        outputs_original = [(BITCOIN_CASHADDRESS_COMPRESSED, 2500, "satoshi")]

        with pytest.raises(InsufficientFunds):
            sanitize_tx_data(
                unspents_original,
                outputs_original,
                fee=50,
                leftover=RETURN_ADDRESS,
                combine=False,
                message=None,
            )

    def test_with_P2SH20_outputs(self):
        # tx:af386b52b9804c4d37d0bcf9ca124b34264d2f0a306ea11ee74c90d939402cb7
        unspents_original = [
            Unspent(5691944, 0, "", "", 0),
            Unspent(17344, 0, "", "", 0),
        ]
        outputs_original = [
            (BITCOIN_CASHADDRESS_PAY2SH20, 11065, "satoshi"),
        ]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=1,
            leftover=RETURN_ADDRESS,
            combine=True,
            message=None,
        )

        assert outputs[1][1] == 5697851

        # multi PAY2SH20 test
        outputs_original = [
            (BITCOIN_CASHADDRESS_PAY2SH20, 11065, "satoshi"),
            (BITCOIN_CASHADDRESS_PAY2SH20, 11065, "satoshi"),
        ]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=1,
            leftover=RETURN_ADDRESS,
            combine=True,
            message=None,
        )

        assert outputs[2][1] == 5686754

    def test_with_P2SH32_outputs(self):
        # based on
        # tx:af386b52b9804c4d37d0bcf9ca124b34264d2f0a306ea11ee74c90d939402cb7
        unspents_original = [
            Unspent(5691944, 0, "", "", 0),
            Unspent(17344, 0, "", "", 0),
        ]
        outputs_original = [
            (BITCOIN_CASHADDRESS_PAY2SH32, 11065, "satoshi"),
        ]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=1,
            leftover=RETURN_ADDRESS,
            combine=True,
            message=None,
        )

        assert outputs[1][1] == 5697839

        # multi PAY2SH32 test
        outputs_original = [
            (BITCOIN_CASHADDRESS_PAY2SH32, 11065, "satoshi"),
            (BITCOIN_CASHADDRESS_PAY2SH32, 11065, "satoshi"),
        ]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            fee=1,
            leftover=RETURN_ADDRESS,
            combine=True,
            message=None,
        )

        assert outputs[2][1] == 5686730


class TestSanitizeTxDataCashToken:
    def test_combine(self):
        unspents_original = [
            Unspent(1000, 0, "script", "txid", 0),
            Unspent(1000, 0, "script", "txid", 1, "caff", "none"),
            Unspent(1000, 0, "script", "txid", 1, "caff", "minting"),
            Unspent(1000, 0, "script", "txid", 1, "caf2", "minting"),
        ]
        outputs_original = [
            [BITCOIN_CASHADDRESS_CATKN, 1000, "satoshi", "caff", "none", None, None]
        ]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            0,
            BITCOIN_CASHADDRESS_CATKN,
            combine=True,
        )
        assert unspents == unspents_original

        assert len(outputs) == 3
        assert outputs[0][1:] == (1000, "caff", "none", None, None)
        assert outputs[1][1:] == (558, "caff", "minting", None, None)
        assert outputs[2][1:] == (2442, "caf2", "minting", None, None)

    def test_no_combine(self):
        unspents_original = [
            Unspent(1000, 0, "script", "txid", 0),
            Unspent(1000, 0, "script", "txid", 1, "caff", "none"),
            Unspent(1000, 0, "script", "txid", 1, "caff", "minting"),
        ]
        outputs_original = [
            [BITCOIN_CASHADDRESS_CATKN, 1100, "satoshi", "caff", "none", None, None]
        ]
        script = Address.from_string(BITCOIN_CASHADDRESS_CATKN).scriptcode

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            0,
            BITCOIN_CASHADDRESS_CATKN,
            combine=False,
        )

        assert len(unspents) == 2
        assert len(outputs) == 2
        assert outputs[0][1:] == (1100, "caff", "none", None, None)
        assert outputs[1] == (script, 900, None, None, None, None)

    def test_genesis(self):
        unspents_original = [
            Unspent(1000, 0, "script", "cafe", 0),
            Unspent(1000, 0, "script", "caca", 1, "caff", "none"),
            Unspent(1000, 0, "script", "txid", 1, "caff", "minting"),
        ]
        outputs_original = [
            [BITCOIN_CASHADDRESS_CATKN, 800, "satoshi", "cafe", "none", None, None]
        ]

        unspents, outputs = sanitize_tx_data(
            unspents_original,
            outputs_original,
            0,
            BITCOIN_CASHADDRESS_CATKN,
            combine=False,
        )

        assert len(unspents) == 2
        assert unspents[0] == unspents_original[0]
        assert len(outputs) == 2
        assert outputs[0][1:] == (800, "cafe", "none", None, None)
        assert outputs[1][1:] == (1200, "caff", "none", None, None)

        # fail genesis
        outputs_original = [
            [BITCOIN_CASHADDRESS_CATKN, 800, "satoshi", "caca", "none", None, None]
        ]

        # caca is not genesis, since txindex = 1. Thus it is treated as
        # normal cashtoken output. But unspents don't have caca cashtoken
        with pytest.raises(InsufficientFunds):
            unspents, outputs = sanitize_tx_data(
                unspents_original,
                outputs_original,
                0,
                BITCOIN_CASHADDRESS_CATKN,
                combine=False,
            )


class TestCreateSignedTransaction:
    def test_matching(self):
        private_key = PrivateKey(WALLET_FORMAT_MAIN)
        tx = create_p2pkh_transaction(private_key, UNSPENTS, OUTPUTS)
        print(tx)
        assert tx[-288:] == FINAL_TX_1[-288:]


class TestEstimateTxFee:
    def test_accurate_compressed(self):
        # 2 p2pkh
        output_script_list = [b"\x00" * 25] * 2
        assert estimate_tx_fee(1, output_script_list, 70, True) == 15820
        # 2 p2pkh 2 p2sh20
        output_script_list = [b"\x00" * 25] * 2 + [b"\x00" * 23] * 2
        assert estimate_tx_fee(1, output_script_list, 70, True) == 20300
        # 2 p2sh20
        output_script_list = [b"\x00" * 23] * 2
        assert estimate_tx_fee(1, output_script_list, 70, True) == 15540
        # 2 p2sh32
        output_script_list = [b"\x00" * 35] * 2
        assert estimate_tx_fee(1, output_script_list, 70, True) == 17220

    def test_accurate_uncompressed(self):
        # 2 p2pkh
        output_script_list = [b"\x00" * 25] * 2
        assert estimate_tx_fee(1, output_script_list, 70, False) == 18060

    def test_none(self):
        # 5 p2pkh
        output_script_list = [b"\x00" * 34] * 5
        assert estimate_tx_fee(5, output_script_list, 0, True) == 0


class TestConstructOutputBlock:
    def test_no_message(self):
        assert construct_output_block(OUTPUTS) == hex_to_bytes(OUTPUT_BLOCK)

    def test_message(self):
        assert construct_output_block(OUTPUTS + MESSAGES) == hex_to_bytes(
            OUTPUT_BLOCK_MESSAGES
        )

    def test_long_message(self):
        amount = b"\x00\x00\x00\x00\x00\x00\x00\x00"
        _, outputs = sanitize_tx_data(
            UNSPENTS,
            [
                (Address.from_script(out[0]).cash_address(), out[1], "satoshi")
                for out in OUTPUTS
            ],
            0,
            RETURN_ADDRESS,
            message="hello" * 50,
        )
        print(outputs)
        assert construct_output_block(outputs).count(amount) == 2

    def test_pushdata_message(self):
        BYTES = (
            OpCodes.OP_RETURN.binary
            + len(b"hello").to_bytes(1, byteorder="little")
            + b"hello"
        )
        assert construct_output_block(
            OUTPUTS + [(BYTES, 0, None, None, None, None)]
        ) == hex_to_bytes(OUTPUT_BLOCK_MESSAGE_PUSHDATA)

    def test_long_pushdata(self):
        BYTES = (
            len(b"hello").to_bytes(1, byteorder="little") + b"hello"
        )  # 6 bytes each * 40 = 240 bytes

        with pytest.raises(ValueError):
            sanitize_tx_data(
                UNSPENTS,
                [
                    (Address.from_script(out[0]).cash_address(), out[1], "satoshi")
                    for out in OUTPUTS
                ],
                0,
                RETURN_ADDRESS,
                message=BYTES * 40,
                custom_pushdata=True,
            )

    def test_string_pushdata(self):
        # Preferable to raise TypeError if string input with custom_pushdata=True.
        with pytest.raises(TypeError):
            construct_output_block(OUTPUTS + [("hello", 0)], custom_pushdata=True)


def test_construct_input_block():
    assert construct_input_block(INPUTS) == hex_to_bytes(INPUT_BLOCK)


def test_calc_txid():
    assert calc_txid(FINAL_TX_1) == FINAL_TX_ID
