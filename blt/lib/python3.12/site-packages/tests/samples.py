BINARY_ADDRESS = b"\x00\x92F\x1b\xdeb\x83\xb4a\xec\xe7\xdd\xf4\xdb\xf1\xe0\xa4\x8b\xd1\x13\xd8&E\xb4\xbf"
BITCOIN_ADDRESS = "1ELReFsTCUY2mfaDTy32qxYiT49z786eFg"
BITCOIN_ADDRESS_COMPRESSED = "1ExJJsNLQDNVVM1s1sdyt1o5P3GC5r32UG"
BITCOIN_ADDRESS_PAY2SH20 = "39SrGQEfFXcTYJhBvjZeQja66Cpz82EEUn"
BITCOIN_ADDRESS_TEST = "mtrNwJxS1VyHYn3qBY1Qfsm3K3kh1mGRMS"
BITCOIN_ADDRESS_TEST_COMPRESSED = "muUFbvTKDEokGTVUjScMhw1QF2rtv5hxCz"
BITCOIN_ADDRESS_TEST_PAY2SH20 = "2NFKbBHzzh32q5DcZJNgZE9sF7gYmtPbawk"
BITCOIN_ADDRESS_REGTEST = "mtrNwJxS1VyHYn3qBY1Qfsm3K3kh1mGRMS"
BITCOIN_ADDRESS_REGTEST_COMPRESSED = "muUFbvTKDEokGTVUjScMhw1QF2rtv5hxCz"
BITCOIN_ADDRESS_REGTEST_PAY2SH20 = "2NFKbBHzzh32q5DcZJNgZE9sF7gYmtPbawk"
BITCOIN_CASHADDRESS = "bitcoincash:qzfyvx77v2pmgc0vulwlfkl3uzjgh5gnmqk5hhyaa6"
BITCOIN_CASHADDRESS_COMPRESSED = (
    "bitcoincash:qzvsaasdvw6mt9j2rs3gyps673gj86flev4sthhcc0"
)
BITCOIN_CASHADDRESS_CATKN = "bitcoincash:zzfyvx77v2pmgc0vulwlfkl3uzjgh5gnmq37yf2mzf"
BITCOIN_CASHADDRESS_PAY2SH20 = "bitcoincash:pp23x8hm0g8d6nrkesamaqeml3v6daeudvpa7zhktf"
BITCOIN_CASHADDRESS_PAY2SH32 = (
    "bitcoincash:pvch8mmxy0rtfrlarg7ucrxxfzds5pamg73h7370aa87d80gyhqxqaw3dsfwg"
)

BITCOIN_CASHADDRESS_TEST = "bchtest:qzfyvx77v2pmgc0vulwlfkl3uzjgh5gnmqjxnsx26x"
BITCOIN_CASHADDRESS_TEST_COMPRESSED = (
    "bchtest:qzvsaasdvw6mt9j2rs3gyps673gj86flev3z0s40ln"
)
BITCOIN_CASHADDRESS_TEST_CATKN = "bchtest:zzfyvx77v2pmgc0vulwlfkl3uzjgh5gnmq4vqwgv94"
BITCOIN_CASHADDRESS_TEST_PAY2SH20 = "bchtest:pp23x8hm0g8d6nrkesamaqeml3v6daeudv90694pv4"
BITCOIN_CASHADDRESS_TEST_PAY2SH32 = (
    "bchtest:pvch8mmxy0rtfrlarg7ucrxxfzds5pamg73h7370aa87d80gyhqxq7fqng6m6"
)

BITCOIN_CASHADDRESS_REGTEST = "bchreg:qzfyvx77v2pmgc0vulwlfkl3uzjgh5gnmqg6939eeq"
BITCOIN_CASHADDRESS_REGTEST_COMPRESSED = (
    "bchreg:qzvsaasdvw6mt9j2rs3gyps673gj86flevt7e3kuu4"
)
BITCOIN_CASHADDRESS_REGTEST_CATKN = "bchreg:zzfyvx77v2pmgc0vulwlfkl3uzjgh5gnmq0sk0tlxn"
BITCOIN_CASHADDRESS_REGTEST_PAY2SH20 = (
    "bchreg:pp23x8hm0g8d6nrkesamaqeml3v6daeudvlnvykj0n"
)

VALID_ENDPOINT_URLS = [
    "https://rest.bch.actorforth.org/v2/",
    "https://rest.bitcoin.com/v2/",
]

INVALID_ENDPOINT_URLS = ["htp://fakesite.com/v2", "https://bitcom.org/", 42]

PRIVATE_KEY_BYTES = b"\xc2\x8a\x9f\x80s\x8fw\rRx\x03\xa5f\xcfo\xc3\xed\xf6\xce\xa5\x86\xc4\xfcJR#\xa5\xady~\x1a\xc3"
PRIVATE_KEY_DER = (
    b"0\x81\x84\x02\x01\x000\x10\x06\x07*\x86H\xce=\x02\x01\x06"
    b"\x05+\x81\x04\x00\n\x04m0k\x02\x01\x01\x04 \xc2\x8a\x9f"
    b"\x80s\x8fw\rRx\x03\xa5f\xcfo\xc3\xed\xf6\xce\xa5\x86\xc4"
    b"\xfcJR#\xa5\xady~\x1a\xc3\xa1D\x03B\x00\x04=\\(u\xc9\xbd"
    b"\x11hu\xa7\x1a]\xb6L\xff\xcb\x139k\x16=\x03\x9b\x1d\x93'"
    b"\x82H\x91\x80C4v\xa45**\xdd\x00\xeb\xb0\xd5\xc9LQ[r\xeb"
    b"\x10\xf1\xfd\x8f?\x03\xb4/J+%[\xfc\x9a\xa9\xe3"
)
PRIVATE_KEY_HEX = "c28a9f80738f770d527803a566cf6fc3edf6cea586c4fc4a5223a5ad797e1ac3"
PRIVATE_KEY_NUM = (
    87993618360805341115891506172036624893404292644470266399436498750715784469187
)
PRIVATE_KEY_PEM = (
    b"-----BEGIN PRIVATE KEY-----\n"
    b"MIGEAgEAMBAGByqGSM49AgEGBSuBBAAKBG0wawIBAQQgwoqfgHOPdw1SeAOlZs9v\n"
    b"w+32zqWGxPxKUiOlrXl+GsOhRANCAAQ9XCh1yb0RaHWnGl22TP/LEzlrFj0Dmx2T\n"
    b"J4JIkYBDNHakNSoq3QDrsNXJTFFbcusQ8f2PPwO0L0orJVv8mqnj\n"
    b"-----END PRIVATE KEY-----\n"
)

PUBKEY_HASH = b"\x92F\x1b\xdeb\x83\xb4a\xec\xe7\xdd\xf4\xdb\xf1\xe0\xa4\x8b\xd1\x13\xd8"
PUBKEY_HASH_COMPRESSED = b'\x99\x0e\xf6\rc\xb5\xb5\x96J\x1c"\x82\x06\x1a\xf4Q#\xe9?\xcb'
PUBKEY_HASH_P2SH20 = b"U\x13\x1e\xfbz\x0e\xddLv\xcc;\xbe\x83;\xfcY\xa6\xf7<k"
PUBKEY_HASH_P2SH32 = b"1s\xeff#\xc6\xb4\x8f\xfd\x1a=\xcc\x0c\xc6H\x9b\n\x07\xbbG\xa3\x7fG\xcf\xefO\xe6\x9d\xe8%\xc0`"
PUBLIC_KEY_COMPRESSED = b"\x03=\\(u\xc9\xbd\x11hu\xa7\x1a]\xb6L\xff\xcb\x139k\x16=\x03\x9b\x1d\x93'\x82H\x91\x80C4"
PUBLIC_KEY_UNCOMPRESSED = (
    b"\x04=\\(u\xc9\xbd\x11hu\xa7\x1a]\xb6L\xff\xcb\x139k\x16=\x03"
    b"\x9b\x1d\x93'\x82H\x91\x80C4v\xa45**\xdd\x00\xeb\xb0\xd5\xc9"
    b"LQ[r\xeb\x10\xf1\xfd\x8f?\x03\xb4/J+%[\xfc\x9a\xa9\xe3"
)
PUBLIC_KEY_X = (
    27753912938952041417634381842191885283234814940840273460372041880794577257268
)
PUBLIC_KEY_Y = (
    53663045980837260634637807506183816949039230809110041985901491152185762425315
)

WALLET_FORMAT_COMPRESSED_MAIN = "L3jsepcttyuJK3HKezD4qqRKGtwc8d2d1Nw6vsoPDX9cMcUxqqMv"
WALLET_FORMAT_COMPRESSED_TEST = "cU6s7jckL3bZUUkb3Q2CD9vNu8F1o58K5R5a3JFtidoccMbhEGKZ"
WALLET_FORMAT_COMPRESSED_REGTEST = WALLET_FORMAT_COMPRESSED_TEST

WALLET_FORMAT_MAIN = "5KHxtARu5yr1JECrYGEA2YpCPdh1i9ciEgQayAF8kcqApkGzT9s"
WALLET_FORMAT_TEST = "934bTuFSgCv9GHi9Ac84u9NA3J3isK9uadGY3nbe6MaDbnQdcbn"
WALLET_FORMAT_REGTEST = WALLET_FORMAT_TEST

CONVERT_BITS_INVALID_DATA_PAYLOAD = [
    0,
    146,
    70,
    27,
    222,
    98,
    131,
    256,
    97,
    236,
    231,
    221,
    244,
    219,
    241,
    224,
    164,
    139,
    209,
    19,
    216,
]
CONVERT_BITS_NO_PAD_PAYLOAD = [
    0,
    146,
    70,
    27,
    222,
    98,
    131,
    25,
    97,
    236,
    231,
    221,
    244,
    219,
    241,
    224,
    164,
    139,
    209,
    19,
    216,
]
CONVERT_BITS_NO_PAD_RETURN = [
    0,
    2,
    9,
    4,
    12,
    6,
    30,
    30,
    12,
    10,
    1,
    17,
    18,
    24,
    15,
    12,
    28,
    31,
    14,
    31,
    9,
    22,
    31,
    17,
    28,
    2,
    18,
    8,
    23,
    20,
    8,
    19,
    27,
]


# CashToken prefixes
CASHTOKEN_CATAGORY_ID = (
    "00fb7b8704f843caf33c436e3386a469e1d004403c388a8b054282d02034f598"
)
CASHTOKEN_CAPABILITY = "none"
CASHTOKEN_COMMITMENT = b"commitment"
CASHTOKEN_AMOUNT = 50
PREFIX_CAPABILITY = b"\xef\x98\xf54 \xd0\x82B\x05\x8b\x8a8<@\x04\xd0\xe1i\xa4\x863nC<\xf3\xcaC\xf8\x04\x87{\xfb\x00 "
PREFIX_CAPABILITY_AMOUNT = b"\xef\x98\xf54 \xd0\x82B\x05\x8b\x8a8<@\x04\xd0\xe1i\xa4\x863nC<\xf3\xcaC\xf8\x04\x87{\xfb\x0002"
PREFIX_CAPABILITY_COMMITMENT = b"\xef\x98\xf54 \xd0\x82B\x05\x8b\x8a8<@\x04\xd0\xe1i\xa4\x863nC<\xf3\xcaC\xf8\x04\x87{\xfb\x00`\ncommitment"
PREFIX_CAPABILITY_COMMITMENT_AMOUNT = b"\xef\x98\xf54 \xd0\x82B\x05\x8b\x8a8<@\x04\xd0\xe1i\xa4\x863nC<\xf3\xcaC\xf8\x04\x87{\xfb\x00p\ncommitment2"
PREFIX_AMOUNT = b"\xef\x98\xf54 \xd0\x82B\x05\x8b\x8a8<@\x04\xd0\xe1i\xa4\x863nC<\xf3\xcaC\xf8\x04\x87{\xfb\x00\x102"
