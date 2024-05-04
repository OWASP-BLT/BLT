from hashlib import new, sha256 as _sha256
from bitcash._ripemd160 import ripemd160

from coincurve import PrivateKey as ECPrivateKey, PublicKey as ECPublicKey


def sha256(bytestr):
    return _sha256(bytestr).digest()


def double_sha256(bytestr):
    return _sha256(_sha256(bytestr).digest()).digest()


def double_sha256_checksum(bytestr):
    return double_sha256(bytestr)[:4]


def ripemd160_sha256(bytestr):
    try:
        return new("ripemd160", sha256(bytestr)).digest()
    except ValueError:
        return ripemd160(sha256(bytestr))


hash160 = ripemd160_sha256
