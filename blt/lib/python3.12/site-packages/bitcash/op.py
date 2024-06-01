from enum import IntEnum


# Derived from Bitcoin Cash Node src/script/script.h
# as implemented in Electron cash wallet, electroncash/bitcoin.py
# ref: reference.cash/protocol/blockchain/script
class OpCodes(IntEnum):
    # push value
    OP_0 = 0x00
    OP_FALSE = OP_0
    OP_PUSHDATA1 = 0x4C
    OP_PUSHDATA2 = 0x4D
    OP_PUSHDATA4 = 0x4E
    OP_1NEGATE = 0x4F
    OP_RESERVED = 0x50
    OP_1 = 0x51
    OP_TRUE = OP_1
    OP_2 = 0x52
    OP_3 = 0x53
    OP_4 = 0x54
    OP_5 = 0x55
    OP_6 = 0x56
    OP_7 = 0x57
    OP_8 = 0x58
    OP_9 = 0x59
    OP_10 = 0x5A
    OP_11 = 0x5B
    OP_12 = 0x5C
    OP_13 = 0x5D
    OP_14 = 0x5E
    OP_15 = 0x5F
    OP_16 = 0x60
    OP_DATA_1 = 0x01
    OP_DATA_2 = 0x02
    OP_DATA_3 = 0x03
    OP_DATA_4 = 0x04
    OP_DATA_5 = 0x05
    OP_DATA_6 = 0x06
    OP_DATA_7 = 0x07
    OP_DATA_8 = 0x08
    OP_DATA_9 = 0x09
    OP_DATA_10 = 0x0A
    OP_DATA_11 = 0x0B
    OP_DATA_12 = 0x0C
    OP_DATA_13 = 0x0D
    OP_DATA_14 = 0x0E
    OP_DATA_15 = 0x0F
    OP_DATA_16 = 0x10
    OP_DATA_17 = 0x11
    OP_DATA_18 = 0x12
    OP_DATA_19 = 0x13
    OP_DATA_20 = 0x14
    OP_DATA_21 = 0x15
    OP_DATA_22 = 0x16
    OP_DATA_23 = 0x17
    OP_DATA_24 = 0x18
    OP_DATA_25 = 0x19
    OP_DATA_26 = 0x1A
    OP_DATA_27 = 0x1B
    OP_DATA_28 = 0x1C
    OP_DATA_29 = 0x1D
    OP_DATA_30 = 0x1E
    OP_DATA_31 = 0x1F
    OP_DATA_32 = 0x20
    OP_DATA_33 = 0x21
    OP_DATA_34 = 0x22
    OP_DATA_35 = 0x23
    OP_DATA_36 = 0x24
    OP_DATA_37 = 0x25
    OP_DATA_38 = 0x26
    OP_DATA_39 = 0x27
    OP_DATA_40 = 0x28
    OP_DATA_41 = 0x29
    OP_DATA_42 = 0x2A
    OP_DATA_43 = 0x2B
    OP_DATA_44 = 0x2C
    OP_DATA_45 = 0x2D
    OP_DATA_46 = 0x2E
    OP_DATA_47 = 0x2F
    OP_DATA_48 = 0x30
    OP_DATA_49 = 0x31
    OP_DATA_50 = 0x32
    OP_DATA_51 = 0x33
    OP_DATA_52 = 0x34
    OP_DATA_53 = 0x35
    OP_DATA_54 = 0x36
    OP_DATA_55 = 0x37
    OP_DATA_56 = 0x38
    OP_DATA_57 = 0x39
    OP_DATA_58 = 0x3A
    OP_DATA_59 = 0x3B
    OP_DATA_60 = 0x3C
    OP_DATA_61 = 0x3D
    OP_DATA_62 = 0x3E
    OP_DATA_63 = 0x3F
    OP_DATA_64 = 0x40
    OP_DATA_65 = 0x41
    OP_DATA_66 = 0x42
    OP_DATA_67 = 0x43
    OP_DATA_68 = 0x44
    OP_DATA_69 = 0x45
    OP_DATA_70 = 0x46
    OP_DATA_71 = 0x47
    OP_DATA_72 = 0x48
    OP_DATA_73 = 0x49
    OP_DATA_74 = 0x4A
    OP_DATA_75 = 0x4B

    # control
    OP_NOP = 0x61
    OP_VER = 0x62
    OP_IF = 0x63
    OP_NOTIF = 0x64
    OP_VERIF = 0x65
    OP_VERNOTIF = 0x66
    OP_ELSE = 0x67
    OP_ENDIF = 0x68
    OP_VERIFY = 0x69
    OP_RETURN = 0x6A

    # stack ops
    OP_TOALTSTACK = 0x6B
    OP_FROMALTSTACK = 0x6C
    OP_2DROP = 0x6D
    OP_2DUP = 0x6E
    OP_3DUP = 0x6F
    OP_2OVER = 0x70
    OP_2ROT = 0x71
    OP_2SWAP = 0x72
    OP_IFDUP = 0x73
    OP_DEPTH = 0x74
    OP_DROP = 0x75
    OP_DUP = 0x76
    OP_NIP = 0x77
    OP_OVER = 0x78
    OP_PICK = 0x79
    OP_ROLL = 0x7A
    OP_ROT = 0x7B
    OP_SWAP = 0x7C
    OP_TUCK = 0x7D

    # splice ops
    OP_CAT = 0x7E
    OP_SPLIT = 0x7F  # after monolith upgrade (May 2018)
    OP_NUM2BIN = 0x80  # after monolith upgrade (May 2018)
    OP_BIN2NUM = 0x81  # after monolith upgrade (May 2018)
    OP_SIZE = 0x82

    # bit logic
    OP_INVERT = 0x83
    OP_AND = 0x84
    OP_OR = 0x85
    OP_XOR = 0x86
    OP_EQUAL = 0x87
    OP_EQUALVERIFY = 0x88
    OP_RESERVED1 = 0x89
    OP_RESERVED2 = 0x8A

    # numeric
    OP_1ADD = 0x8B
    OP_1SUB = 0x8C
    OP_2MUL = 0x8D
    OP_2DIV = 0x8E
    OP_NEGATE = 0x8F
    OP_ABS = 0x90
    OP_NOT = 0x91
    OP_0NOTEQUAL = 0x92

    OP_ADD = 0x93
    OP_SUB = 0x94
    OP_MUL = 0x95
    OP_DIV = 0x96
    OP_MOD = 0x97
    OP_LSHIFT = 0x98
    OP_RSHIFT = 0x99

    OP_BOOLAND = 0x9A
    OP_BOOLOR = 0x9B
    OP_NUMEQUAL = 0x9C
    OP_NUMEQUALVERIFY = 0x9D
    OP_NUMNOTEQUAL = 0x9E
    OP_LESSTHAN = 0x9F
    OP_GREATERTHAN = 0xA0
    OP_LESSTHANOREQUAL = 0xA1
    OP_GREATERTHANOREQUAL = 0xA2
    OP_MIN = 0xA3
    OP_MAX = 0xA4

    OP_WITHIN = 0xA5

    # crypto
    OP_RIPEMD160 = 0xA6
    OP_SHA1 = 0xA7
    OP_SHA256 = 0xA8
    OP_HASH160 = 0xA9
    OP_HASH256 = 0xAA
    OP_CODESEPARATOR = 0xAB
    OP_CHECKSIG = 0xAC
    OP_CHECKSIGVERIFY = 0xAD
    OP_CHECKMULTISIG = 0xAE
    OP_CHECKMULTISIGVERIFY = 0xAF

    # expansion
    OP_NOP1 = 0xB0
    OP_CHECKLOCKTIMEVERIFY = 0xB1
    OP_NOP2 = OP_CHECKLOCKTIMEVERIFY
    OP_CHECKSEQUENCEVERIFY = 0xB2
    OP_NOP3 = OP_CHECKSEQUENCEVERIFY
    OP_NOP4 = 0xB3
    OP_NOP5 = 0xB4
    OP_NOP6 = 0xB5
    OP_NOP7 = 0xB6
    OP_NOP8 = 0xB7
    OP_NOP9 = 0xB8
    OP_NOP10 = 0xB9

    # More crypto
    OP_CHECKDATASIG = 0xBA
    OP_CHECKDATASIGVERIFY = 0xBB

    # additional byte string operations
    OP_REVERSEBYTES = 0xBC

    # Native Introspection opcodes
    OP_INPUTINDEX = 0xC0
    OP_ACTIVEBYTECODE = 0xC1
    OP_TXVERSION = 0xC2
    OP_TXINPUTCOUNT = 0xC3
    OP_TXOUTPUTCOUNT = 0xC4
    OP_TXLOCKTIME = 0xC5
    OP_UTXOVALUE = 0xC6
    OP_UTXOBYTECODE = 0xC7
    OP_OUTPOINTTXHASH = 0xC8
    OP_OUTPOINTINDEX = 0xC9
    OP_INPUTBYTECODE = 0xCA
    OP_INPUTSEQUENCENUMBER = 0xCB
    OP_OUTPUTVALUE = 0xCC
    OP_OUTPUTBYTECODE = 0xCD

    # CashTokens opcodes
    OP_UTXOTOKENCATEGORY = 0xCE
    OP_UTXOTOKENCOMMITMENT = 0xCF
    OP_UTXOTOKENAMOUNT = 0xD0
    OP_OUTPUTTOKENCATEGORY = 0xD1
    OP_OUTPUTTOKENCOMMITMENT = 0xD2
    OP_OUTPUTTOKENAMOUNT = 0xD3
    OP_TOKENPREFIX = 0xEF

    @property
    def binary(self):
        """
        Adds easy way to convert to binary

        >>> OpCodes.OP_0.b
        b"\x00"
        """
        return self.value.to_bytes(1, "little")

    @property
    def hex(self):
        """
        Adds easy way to convert to hex
        >>> OpCodes.OP_0.h
        "00"
        """
        # converty from binary to preserve 8 bit hex
        return self.b.hex()
