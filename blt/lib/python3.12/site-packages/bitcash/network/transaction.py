from bitcash.format import hex_to_asm


class Transaction:
    """
    Representation of a transaction returned from the network.
    """

    def __init__(self, txid, block, amount_in, amount_out, amount_fee):
        self.txid = txid
        self.block = block

        if amount_in != amount_out + amount_fee:
            raise ArithmeticError("the amounts just don't add up!")

        self.amount_in = amount_in
        self.amount_out = amount_out
        self.amount_fee = amount_fee

        self.inputs = []
        self.outputs = []

    def to_dict(self):
        return {
            "txid": self.txid,
            "block": self.block,
            "amount_in": self.amount_in,
            "amount_out": self.amount_out,
            "amount_fee": self.amount_fee,
            "inputs": [input_.to_dict() for input_ in self.inputs],
            "outputs": [output.to_dict() for output in self.outputs],
        }

    def __eq__(self, other):
        return self.to_dict() == other.to_dict()

    def add_input(self, part):
        self.inputs.append(part)

    def add_output(self, part):
        self.outputs.append(part)

    def __repr__(self):
        return "{} in block {} for {:.0f} satoshi ({:.0f} sent + {:.0f} fee) with {} input{} and {} output{}".format(
            self.txid,
            self.block,
            self.amount_in,
            self.amount_out,
            self.amount_fee,
            len(self.inputs),
            "" if len(self.inputs) == 1 else "s",
            len(self.outputs),
            "" if len(self.outputs) == 1 else "s",
        )


class TxPart:
    """
    Representation of a single input or output.
    """

    def __init__(
        self,
        address,
        amount,
        category_id=None,
        nft_capability=None,
        nft_commitment=None,
        token_amount=None,
        asm=None,
        data_hex=None,
    ):
        self.address = address
        self.amount = amount
        self.category_id = category_id
        self.nft_capability = nft_capability
        self.nft_commitment = nft_commitment
        self.token_amount = token_amount
        self.op_return = None

        if data_hex is not None:
            asm = hex_to_asm(data_hex)

        if address is None and asm is not None:
            if asm.startswith("OP_RETURN "):
                self.op_return = asm[10:]
            elif asm.startswith("return ["):
                self.op_return = asm[8:-1]

    def to_dict(self):
        return {
            "address": self.address,
            "amount": self.amount,
            "category_id": self.category_id,
            "nft_capability": self.nft_capability,
            "nft_commitment": self.nft_commitment,
            "token_amount": self.token_amount,
            "op_return": self.op_return,
        }

    def message(self):
        """Attempt to decode the op_return value (if there is one) as a UTF-8 string."""

        if self.op_return is None:
            return None

        return bytearray.fromhex(self.op_return).decode("utf-8")

    def __repr__(self):
        if self.address is None and self.op_return is not None:
            return "OP_RETURN data with {:.0f} satoshi burned".format(self.amount)
        else:
            return "{} with {:.0f} satoshi".format(self.address, self.amount)
