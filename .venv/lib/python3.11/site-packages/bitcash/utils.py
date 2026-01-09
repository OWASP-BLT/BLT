import decimal
import functools
import time
from binascii import hexlify


class Decimal(decimal.Decimal):
    def __new__(cls, value):
        return super().__new__(cls, str(value))


def chunk_data(data, size):
    return (data[i : i + size] for i in range(0, len(data), size))


def int_to_unknown_bytes(num, byteorder="big"):
    """Converts an int to the least number of bytes as possible."""
    return num.to_bytes((num.bit_length() + 7) // 8 or 1, byteorder)


def bytes_to_hex(bytestr, upper=False):
    hexed = hexlify(bytestr).decode()
    return hexed.upper() if upper else hexed


def hex_to_bytes(hexed):
    if len(hexed) & 1:
        hexed = "0" + hexed

    return bytes.fromhex(hexed)


def int_to_hex(num, upper=False):
    hexed = hex(num)[2:]
    return hexed.upper() if upper else hexed


def hex_to_int(hexed):
    return int(hexed, 16)


def flip_hex_byte_order(string):
    return bytes_to_hex(hex_to_bytes(string)[::-1])


def int_to_varint(val):
    if val < 253:
        return val.to_bytes(1, "little")
    elif val <= 65535:
        return b"\xfd" + val.to_bytes(2, "little")
    elif val <= 4294967295:
        return b"\xfe" + val.to_bytes(4, "little")
    else:
        return b"\xff" + val.to_bytes(8, "little")


def varint_to_int(val):
    """
    Converts varint to int from incoming bytestream.

    :param val: the bytecode starting with varint
    :type val: ``io.BytesIO``
    :returns: ``int``
    """
    start_byte = val.read(1)
    if start_byte == b"\xff":
        return int.from_bytes(val.read(8), "little")
    if start_byte == b"\xfe":
        return int.from_bytes(val.read(4), "little")
    if start_byte == b"\xfd":
        return int.from_bytes(val.read(2), "little")
    return int.from_bytes(start_byte, "little")


def time_cache(max_age: int, cache_size: int = 32):
    """
    Timed cache decorator to store a value until time-to-live

    :param max_age: Time, in seconds, untill when the value is invalidated.
    :param cache_size: Size of LRU cache.
    """

    class ReturnValue:
        def __init__(self, value, expiry):
            self.value = value
            self.expiry = expiry

    def _decorator(fn):
        @functools.lru_cache(maxsize=cache_size)
        def cache_fn(*args, **kwargs):
            value = fn(*args, **kwargs)
            expiry = time.monotonic() + max_age
            return ReturnValue(value, expiry)

        @functools.wraps(fn)
        def _wrapped(*args, **kwargs):
            return_value = cache_fn(*args, **kwargs)
            if return_value.expiry < time.monotonic():
                # update the reference to the cache
                return_value.value = fn(*args, **kwargs)
                return_value.expiry = time.monotonic() + max_age
            return return_value.value

        return _wrapped

    return _decorator
