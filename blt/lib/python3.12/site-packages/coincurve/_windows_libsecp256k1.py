import os

from cffi import FFI

BASE_DEFINITIONS = """
typedef struct secp256k1_context_struct secp256k1_context;
typedef struct secp256k1_scratch_space_struct secp256k1_scratch_space;

typedef struct {
    unsigned char data[64];
} secp256k1_pubkey;

typedef struct {
    unsigned char data[64];
} secp256k1_ecdsa_signature;

typedef int (*secp256k1_nonce_function)(
    unsigned char *nonce32,
    const unsigned char *msg32,
    const unsigned char *key32,
    const unsigned char *algo16,
    void *data,
    unsigned int attempt
);

#define SECP256K1_CONTEXT_NONE 1
#define SECP256K1_EC_COMPRESSED 258
#define SECP256K1_EC_UNCOMPRESSED 2
#define SECP256K1_TAG_PUBKEY_EVEN 2
#define SECP256K1_TAG_PUBKEY_ODD 3
#define SECP256K1_TAG_PUBKEY_UNCOMPRESSED 4
#define SECP256K1_TAG_PUBKEY_HYBRID_EVEN 6
#define SECP256K1_TAG_PUBKEY_HYBRID_ODD 7

extern const secp256k1_context *secp256k1_context_static;
extern void secp256k1_selftest(void);
extern secp256k1_context *secp256k1_context_create(
    unsigned int flags
);
extern secp256k1_context *secp256k1_context_clone(
    const secp256k1_context *ctx
);
extern void secp256k1_context_destroy(
    secp256k1_context *ctx
);
extern void secp256k1_context_set_illegal_callback(
    secp256k1_context *ctx,
    void (*fun)(const char *message, void *data),
    const void *data
);
extern void secp256k1_context_set_error_callback(
    secp256k1_context *ctx,
    void (*fun)(const char *message, void *data),
    const void *data
);
extern secp256k1_scratch_space *secp256k1_scratch_space_create(
    const secp256k1_context *ctx,
    size_t size
);
extern void secp256k1_scratch_space_destroy(
    const secp256k1_context *ctx,
    secp256k1_scratch_space *scratch
);
extern int secp256k1_ec_pubkey_parse(
    const secp256k1_context *ctx,
    secp256k1_pubkey *pubkey,
    const unsigned char *input,
    size_t inputlen
);
extern int secp256k1_ec_pubkey_serialize(
    const secp256k1_context *ctx,
    unsigned char *output,
    size_t *outputlen,
    const secp256k1_pubkey *pubkey,
    unsigned int flags
);
extern int secp256k1_ec_pubkey_cmp(
    const secp256k1_context *ctx,
    const secp256k1_pubkey *pubkey1,
    const secp256k1_pubkey *pubkey2
);
extern int secp256k1_ecdsa_signature_parse_compact(
    const secp256k1_context *ctx,
    secp256k1_ecdsa_signature *sig,
    const unsigned char *input64
);
extern int secp256k1_ecdsa_signature_parse_der(
    const secp256k1_context *ctx,
    secp256k1_ecdsa_signature *sig,
    const unsigned char *input,
    size_t inputlen
);
extern int secp256k1_ecdsa_signature_serialize_der(
    const secp256k1_context *ctx,
    unsigned char *output,
    size_t *outputlen,
    const secp256k1_ecdsa_signature *sig
);
extern int secp256k1_ecdsa_signature_serialize_compact(
    const secp256k1_context *ctx,
    unsigned char *output64,
    const secp256k1_ecdsa_signature *sig
);
extern int secp256k1_ecdsa_verify(
    const secp256k1_context *ctx,
    const secp256k1_ecdsa_signature *sig,
    const unsigned char *msghash32,
    const secp256k1_pubkey *pubkey
);
extern int secp256k1_ecdsa_signature_normalize(
    const secp256k1_context *ctx,
    secp256k1_ecdsa_signature *sigout,
    const secp256k1_ecdsa_signature *sigin
);

extern const secp256k1_nonce_function secp256k1_nonce_function_rfc6979;

extern const secp256k1_nonce_function secp256k1_nonce_function_default;

extern int secp256k1_ecdsa_sign(
    const secp256k1_context *ctx,
    secp256k1_ecdsa_signature *sig,
    const unsigned char *msghash32,
    const unsigned char *seckey,
    secp256k1_nonce_function noncefp,
    const void *ndata
);
extern int secp256k1_ec_seckey_verify(
    const secp256k1_context *ctx,
    const unsigned char *seckey
);
extern int secp256k1_ec_pubkey_create(
    const secp256k1_context *ctx,
    secp256k1_pubkey *pubkey,
    const unsigned char *seckey
);
extern int secp256k1_ec_seckey_negate(
    const secp256k1_context *ctx,
    unsigned char *seckey
);
extern int secp256k1_ec_pubkey_negate(
    const secp256k1_context *ctx,
    secp256k1_pubkey *pubkey
);
extern int secp256k1_ec_seckey_tweak_add(
    const secp256k1_context *ctx,
    unsigned char *seckey,
    const unsigned char *tweak32
);
extern int secp256k1_ec_pubkey_tweak_add(
    const secp256k1_context *ctx,
    secp256k1_pubkey *pubkey,
    const unsigned char *tweak32
);
extern int secp256k1_ec_seckey_tweak_mul(
    const secp256k1_context *ctx,
    unsigned char *seckey,
    const unsigned char *tweak32
);
extern int secp256k1_ec_pubkey_tweak_mul(
    const secp256k1_context *ctx,
    secp256k1_pubkey *pubkey,
    const unsigned char *tweak32
);
extern int secp256k1_context_randomize(
    secp256k1_context *ctx,
    const unsigned char *seed32
);
extern int secp256k1_ec_pubkey_combine(
    const secp256k1_context *ctx,
    secp256k1_pubkey *out,
    const secp256k1_pubkey * const *ins,
    size_t n
);
extern int secp256k1_tagged_sha256(
    const secp256k1_context *ctx,
    unsigned char *hash32,
    const unsigned char *tag,
    size_t taglen,
    const unsigned char *msg,
    size_t msglen
);
"""

EXTRAKEYS_DEFINITIONS = """
typedef struct {
    unsigned char data[64];
} secp256k1_xonly_pubkey;
typedef struct {
    unsigned char data[96];
} secp256k1_keypair;
extern int secp256k1_xonly_pubkey_parse(
    const secp256k1_context *ctx,
    secp256k1_xonly_pubkey *pubkey,
    const unsigned char *input32
);
extern int secp256k1_xonly_pubkey_serialize(
    const secp256k1_context *ctx,
    unsigned char *output32,
    const secp256k1_xonly_pubkey *pubkey
);
extern int secp256k1_xonly_pubkey_cmp(
    const secp256k1_context *ctx,
    const secp256k1_xonly_pubkey *pk1,
    const secp256k1_xonly_pubkey *pk2
);
extern int secp256k1_xonly_pubkey_from_pubkey(
    const secp256k1_context *ctx,
    secp256k1_xonly_pubkey *xonly_pubkey,
    int *pk_parity,
    const secp256k1_pubkey *pubkey
);
extern int secp256k1_xonly_pubkey_tweak_add(
    const secp256k1_context *ctx,
    secp256k1_pubkey *output_pubkey,
    const secp256k1_xonly_pubkey *internal_pubkey,
    const unsigned char *tweak32
);
extern int secp256k1_xonly_pubkey_tweak_add_check(
    const secp256k1_context *ctx,
    const unsigned char *tweaked_pubkey32,
    int tweaked_pk_parity,
    const secp256k1_xonly_pubkey *internal_pubkey,
    const unsigned char *tweak32
);
extern int secp256k1_keypair_create(
    const secp256k1_context *ctx,
    secp256k1_keypair *keypair,
    const unsigned char *seckey
);
extern int secp256k1_keypair_sec(
    const secp256k1_context *ctx,
    unsigned char *seckey,
    const secp256k1_keypair *keypair
);
extern int secp256k1_keypair_pub(
    const secp256k1_context *ctx,
    secp256k1_pubkey *pubkey,
    const secp256k1_keypair *keypair
);
extern int secp256k1_keypair_xonly_pub(
    const secp256k1_context *ctx,
    secp256k1_xonly_pubkey *pubkey,
    int *pk_parity,
    const secp256k1_keypair *keypair
);
extern int secp256k1_keypair_xonly_tweak_add(
    const secp256k1_context *ctx,
    secp256k1_keypair *keypair,
    const unsigned char *tweak32
);
"""

RECOVERY_DEFINITIONS = """
typedef struct {
    unsigned char data[65];
} secp256k1_ecdsa_recoverable_signature;
extern int secp256k1_ecdsa_recoverable_signature_parse_compact(
    const secp256k1_context *ctx,
    secp256k1_ecdsa_recoverable_signature *sig,
    const unsigned char *input64,
    int recid
);
extern int secp256k1_ecdsa_recoverable_signature_convert(
    const secp256k1_context *ctx,
    secp256k1_ecdsa_signature *sig,
    const secp256k1_ecdsa_recoverable_signature *sigin
);
extern int secp256k1_ecdsa_recoverable_signature_serialize_compact(
    const secp256k1_context *ctx,
    unsigned char *output64,
    int *recid,
    const secp256k1_ecdsa_recoverable_signature *sig
);
extern int secp256k1_ecdsa_sign_recoverable(
    const secp256k1_context *ctx,
    secp256k1_ecdsa_recoverable_signature *sig,
    const unsigned char *msghash32,
    const unsigned char *seckey,
    secp256k1_nonce_function noncefp,
    const void *ndata
);
extern int secp256k1_ecdsa_recover(
    const secp256k1_context *ctx,
    secp256k1_pubkey *pubkey,
    const secp256k1_ecdsa_recoverable_signature *sig,
    const unsigned char *msghash32
);
"""

SCHNORRSIG_DEFINITIONS = """
typedef int (*secp256k1_nonce_function_hardened)(
    unsigned char *nonce32,
    const unsigned char *msg,
    size_t msglen,
    const unsigned char *key32,
    const unsigned char *xonly_pk32,
    const unsigned char *algo,
    size_t algolen,
    void *data
);
extern const secp256k1_nonce_function_hardened secp256k1_nonce_function_bip340;
typedef struct {
    unsigned char magic[4];
    secp256k1_nonce_function_hardened noncefp;
    void *ndata;
} secp256k1_schnorrsig_extraparams;
extern int secp256k1_schnorrsig_sign32(
    const secp256k1_context *ctx,
    unsigned char *sig64,
    const unsigned char *msg32,
    const secp256k1_keypair *keypair,
    const unsigned char *aux_rand32
);
extern int secp256k1_schnorrsig_sign_custom(
    const secp256k1_context *ctx,
    unsigned char *sig64,
    const unsigned char *msg,
    size_t msglen,
    const secp256k1_keypair *keypair,
    secp256k1_schnorrsig_extraparams *extraparams
);
extern int secp256k1_schnorrsig_verify(
    const secp256k1_context *ctx,
    const unsigned char *sig64,
    const unsigned char *msg,
    size_t msglen,
    const secp256k1_xonly_pubkey *pubkey
);
"""

ECDH_DEFINITIONS = """
typedef int (*secp256k1_ecdh_hash_function)(
  unsigned char *output,
  const unsigned char *x32,
  const unsigned char *y32,
  void *data
);
extern const secp256k1_ecdh_hash_function secp256k1_ecdh_hash_function_sha256;
extern const secp256k1_ecdh_hash_function secp256k1_ecdh_hash_function_default;
extern int secp256k1_ecdh(
  const secp256k1_context *ctx,
  unsigned char *output,
  const secp256k1_pubkey *pubkey,
  const unsigned char *seckey,
  secp256k1_ecdh_hash_function hashfp,
  void *data
);
"""

ELLSWIFT_DEFINITIONS = """
typedef int (*secp256k1_ellswift_xdh_hash_function)(
    unsigned char *output,
    const unsigned char *x32,
    const unsigned char *ell_a64,
    const unsigned char *ell_b64,
    void *data
);
extern const secp256k1_ellswift_xdh_hash_function secp256k1_ellswift_xdh_hash_function_prefix;
extern const secp256k1_ellswift_xdh_hash_function secp256k1_ellswift_xdh_hash_function_bip324;
extern int secp256k1_ellswift_encode(
    const secp256k1_context *ctx,
    unsigned char *ell64,
    const secp256k1_pubkey *pubkey,
    const unsigned char *rnd32
);
extern int secp256k1_ellswift_decode(
    const secp256k1_context *ctx,
    secp256k1_pubkey *pubkey,
    const unsigned char *ell64
);
extern int secp256k1_ellswift_create(
    const secp256k1_context *ctx,
    unsigned char *ell64,
    const unsigned char *seckey32,
    const unsigned char *auxrnd32
);
extern int secp256k1_ellswift_xdh(
  const secp256k1_context *ctx,
  unsigned char *output,
  const unsigned char *ell_a64,
  const unsigned char *ell_b64,
  const unsigned char *seckey32,
  int party,
  secp256k1_ellswift_xdh_hash_function hashfp,
  void *data
);
"""

PREALLOCATED_DEFINITIONS = """
extern size_t secp256k1_context_preallocated_size(
    unsigned int flags
);
extern secp256k1_context *secp256k1_context_preallocated_create(
    void *prealloc,
    unsigned int flags
);
extern size_t secp256k1_context_preallocated_clone_size(
    const secp256k1_context *ctx
);
extern secp256k1_context *secp256k1_context_preallocated_clone(
    const secp256k1_context *ctx,
    void *prealloc
);
extern void secp256k1_context_preallocated_destroy(
    secp256k1_context *ctx
);
"""

ffi = FFI()

ffi.cdef(BASE_DEFINITIONS)
ffi.cdef(EXTRAKEYS_DEFINITIONS)
ffi.cdef(RECOVERY_DEFINITIONS)
ffi.cdef(SCHNORRSIG_DEFINITIONS)
ffi.cdef(ECDH_DEFINITIONS)

here = os.path.dirname(os.path.abspath(__file__))
lib = ffi.dlopen(os.path.join(here, 'libsecp256k1.dll'))

