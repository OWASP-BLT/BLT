from bitcash.network.meta import Unspent


class TestUnspent:
    def test_init(self):
        unspent = Unspent(
            10000, 7, "script", "txid", 0, "category_id", "none", "nft_commitment", 50
        )
        assert unspent.amount == 10000
        assert unspent.confirmations == 7
        assert unspent.script == "script"
        assert unspent.txid == "txid"
        assert unspent.txindex == 0
        assert unspent.category_id == "category_id"
        assert unspent.nft_commitment == "nft_commitment"
        assert unspent.nft_capability == "none"
        assert unspent.token_amount == 50
        # CashToken properties
        assert unspent.has_amount is True
        assert unspent.has_nft is True
        assert unspent.has_cashtoken is True

    def test_dict_conversion(self):
        unspent = Unspent(10000, 7, "script", "txid", 0)

        assert unspent == Unspent.from_dict(unspent.to_dict())

    def test_equality(self):
        unspent1 = Unspent(10000, 7, "script", "txid", 0)
        unspent2 = Unspent(10000, 7, "script", "txid", 0)
        unspent3 = Unspent(50000, 7, "script", "txid", 0)
        assert unspent1 == unspent2
        assert unspent1 != unspent3

    def test_repr(self):
        unspent = Unspent(10000, 7, "script", "txid", 0)

        assert repr(unspent) == (
            "Unspent(amount=10000, confirmations=7, "
            "script='script', txid='txid', txindex=0)"
        )

    def test_gt(self):
        unspent = Unspent(10000, 7, "script", "txid", 0)
        unspent1 = Unspent(20000, 7, "script", "txid", 0)
        unspent2 = Unspent(10000, 7, "script", "txid", 0, "category_id", "none")
        unspent3 = Unspent(30000, 7, "script", "txid", 0, "category_id", "none")
        unspent4 = Unspent(10000, 7, "script", "txid", 0, "category_id", "mutable")
        unspent5 = Unspent(
            20000, 7, "script", "txid", 0, "category_id", token_amount=50
        )
        unspent6 = Unspent(
            20000, 7, "script", "txid", 0, "category_id", token_amount=20
        )
        unspent7 = Unspent(
            30000, 7, "script", "txid", 0, "category_id", token_amount=20
        )

        assert unspent1 > unspent
        assert unspent2 > unspent
        assert unspent4 > unspent2
        assert not unspent2 > unspent4
        assert not unspent > unspent2
        assert unspent3 > unspent2
        assert unspent5 > unspent
        assert not unspent > unspent5
        assert unspent5 > unspent7
        assert not unspent6 > unspent5
        assert unspent7 > unspent6
