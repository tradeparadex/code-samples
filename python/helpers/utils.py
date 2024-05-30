import functools
from typing import List, Optional, Sequence
from starknet_py.constants import EC_ORDER
from starkware.crypto.signature.signature import generate_k_rfc6979

from starknet_crypto_py import (
    get_public_key as rs_get_public_key,
    pedersen_hash as rs_pedersen_hash,
    sign as rs_sign,
    verify as rs_verify,
)


# ###
# Override functions in starknet_py.hash.utils that use cpp
# to use the starknet_crypto_py library
# ###


def private_to_stark_key(priv_key: int) -> int:
    """
    Deduces the public key given a private key.
    """
    return rs_get_public_key(priv_key)


def pedersen_hash(left: int, right: int) -> int:
    """
    One of two hash functions (along with _starknet_keccak) used throughout Starknet.
    """
    # return cpp_hash(left, right)
    return rs_pedersen_hash(left, right)


def compute_hash_on_elements(data: Sequence) -> int:
    """
    Computes a hash chain over the data, in the following order:
        h(h(h(h(0, data[0]), data[1]), ...), data[n-1]), n).

    The hash is initialized with 0 and ends with the data length appended.
    The length is appended in order to avoid collisions of the following kind:
    H([x,y,z]) = h(h(x,y),z) = H([w, z]) where w = h(x,y).
    """
    return functools.reduce(pedersen_hash, [*data, len(data)], 0)


def message_signature(
    msg_hash: int, priv_key: int, seed: Optional[int] = None
) -> tuple[int, int]:
    """
    Signs the message with private key.
    """
    # k should be a strong cryptographical random
    # See: https://tools.ietf.org/html/rfc6979
    k = generate_k_rfc6979(msg_hash, priv_key, seed)
    return rs_sign(private_key=priv_key, msg_hash=msg_hash, k=k)


def verify_message_signature(
    msg_hash: int, signature: List[int], public_key: int
) -> bool:
    """
    Verifies ECDSA signature of a given message hash with a given public key.
    Returns true if public_key signs the message.
    """
    r, s = signature
    return rs_verify(msg_hash=msg_hash, r=r, s=s, public_key=public_key)
