import asyncio
import functools
import logging
import os
import traceback

from crypto_cpp_py.cpp_bindings import cpp_hash, get_cpp_lib_file
from typing import cast, Sequence, List, Union

from starknet_py.cairo.felt import encode_shortstring
from starknet_py.common import int_from_bytes
from starknet_py.hash.selector import get_selector_from_name
from starkware.cairo.lang.vm.crypto import pedersen_hash as default_hash

from utils import (
    generate_paradex_account,
    get_l1_eth_account,
)
from shared.api_client import get_paradex_config
paradex_http_url = "https://api.testnet.paradex.trade/v1"
# This is a very stripped down version of message hashing
# Added notes around the code to explain what's going on

# These types are specific to each message
# This one is specifically for onboarding
types = {
    "StarkNetDomain": [
        {"name": "name", "type": "felt"},
        {"name": "chainId", "type": "felt"},
        {"name": "version", "type": "felt"},
    ],
    "Constant": [
        {"name": "action", "type": "felt"},
    ],
}

async def main(eth_private_key_hex: str) -> None:
    # Initialize Ethereum account
    _, eth_account = get_l1_eth_account(eth_private_key_hex)

    # Load Paradex config
    paradex_config = await get_paradex_config(paradex_http_url)
    chain = int_from_bytes(paradex_config["starknet_chain_id"].encode())

    # Generate Paradex account (only local)
    account_address, _ = generate_paradex_account(
        paradex_config, eth_account.key.hex()
    )

    print("--------------------")

    # Domain for all messages - this does not change
    domain = { "name": "Paradex", "chainId": hex(chain), "version": "1" }

    # Other relevant data for this message
    primary_type = "Constant"
    message_data = { "action": "Onboarding" }

    # Message array contains 4 elements
    # 1. Encoded short string to int - "StarkNet Message" (Does not change)
    # 2. Encoded domain struct to int (Does not change)
    # 3. Encoded account address to int (Does not change if using same account)
    # 4. Encoded message data struct to int (Changes for each on message)
    message = [
        encode_shortstring("StarkNet Message"), # 110930206544689809660069706067448260453
        struct_hash("StarkNetDomain", domain), # 3014178702424108121777716632486845591462527404146882043469255095154522182084
        int(account_address, 16),
        struct_hash(primary_type, message_data),
    ]
    print("Encoded message:", message)

    message_hash = compute_hash_on_elements(message)
    print("Message hash:", message_hash)

    print("--------------------")


def struct_hash(type_name: str, data: dict) -> int:
    """
    Computes the hash of a struct.
    """
    return compute_hash_on_elements(
        [type_hash(type_name), *_encode_data(type_name, data)]
    )


def type_hash(type_name: str) -> int:
    """
    Returns the selector of a contract's function name.
    Uses a variant of eth-keccak that computes a value that fits in a StarkNet field element.
    """
    return get_selector_from_name(_encode_type(type_name))


def _encode_data(type_name: str, data: dict) -> List[int]:
    """
    Encodes the data for a struct
    """
    values = []
    for param in types[type_name]:
        encoded_value = _encode_value(param["type"], data[param["name"]])
        values.append(encoded_value)

    return values


def _encode_value(type_name: str, value: Union[int, str, dict, list]) -> int:
    """
    Computes a hash chain over the data, in the following order:
        h(h(h(h(0, data[0]), data[1]), ...), data[n-1]), n).

    The hash is initialized with 0 and ends with the data length appended.
    The length is appended in order to avoid collisions of the following kind:
    H([x,y,z]) = h(h(x,y),z) = H([w, z]) where w = h(x,y).
    """
    if is_pointer(type_name) and isinstance(value, list):
        type_name = strip_pointer(type_name)

        if _is_struct(type_name):
            return compute_hash_on_elements(
                [struct_hash(type_name, data) for data in value]
            )
        return compute_hash_on_elements([int(get_hex(val), 16) for val in value])

    if _is_struct(type_name) and isinstance(value, dict):
        return struct_hash(type_name, value)

    value = cast(Union[int, str], value)
    return int(get_hex(value), 16)


def get_hex(value: Union[int, str]) -> str:
    if isinstance(value, int):
        return hex(value)
    if value[:2] == "0x":
        return value
    if value.isnumeric():
        return hex(int(value))
    return hex(encode_shortstring(value))


def _is_struct(type_name: str) -> bool:
    """
    Checks if a type is a message `types`.
    """
    return type_name in types


def is_pointer(value: str) -> bool:
    return len(value) > 0 and value[-1] == "*"


def strip_pointer(value: str) -> str:
    if is_pointer(value):
        return value[:-1]
    return value


def _encode_type(type_name: str) -> str:
    """
    Examples:
    - StarkNetDomain(name:felt,chainId:felt,version:felt)
    - Constant(action:felt)
    """
    primary, *dependencies = _get_dependencies(type_name)
    d_types = [primary, *sorted(dependencies)]

    def make_dependency_str(dependency):
        lst = [f"{t['name']}:{t['type']}" for t in types[dependency]]
        return f"{dependency}({','.join(lst)})"

    return "".join([make_dependency_str(x) for x in d_types])


def _get_dependencies(type_name: str) -> List[str]:
    if type_name not in types:
        # type_name is a primitive type, has no dependencies
        return []

    dependencies = set()

    def collect_deps(type_name: str) -> None:
        for param in types[type_name]:
            fixed_type = strip_pointer(param["type"])
            if fixed_type in types and fixed_type not in dependencies:
                dependencies.add(fixed_type)
                # recursive call
                collect_deps(fixed_type)

    # collect dependencies into a set
    collect_deps(type_name)
    return [type_name, *list(dependencies)]


def compute_hash_on_elements(data: Sequence) -> int:
    """
    Computes a hash chain over the data, in the following order:
        h(h(h(h(0, data[0]), data[1]), ...), data[n-1]), n).

    The hash is initialized with 0 and ends with the data length appended.
    The length is appended in order to avoid collisions of the following kind:
    H([x,y,z]) = h(h(x,y),z) = H([w, z]) where w = h(x,y).
    """
    return functools.reduce(pedersen_hash, [*data, len(data)], 0)


def pedersen_hash(left: int, right: int) -> int:
    """
    One of two hash functions (along with _starknet_keccak) used throughout StarkNet.
    """
    if use_cpp_variant():
        return cpp_hash(left, right)
    return default_hash(left, right)


def use_cpp_variant() -> bool:
    force_disable_ext = (
        os.getenv("DISABLE_CRYPTO_C_EXTENSION", "false").lower() == "true"
    )
    cpp_lib_file = get_cpp_lib_file()
    return not force_disable_ext and bool(cpp_lib_file)


if __name__ == "__main__":
    # Logging
    logging.basicConfig(
        level=os.getenv("LOGGING_LEVEL", "INFO"),
        format="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Load environment variables
    eth_private_key_hex = os.getenv('ETHEREUM_PRIVATE_KEY', "")

    # Run main
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(eth_private_key_hex))
    except Exception as e:
        logging.error("Local Main Error")
        logging.error(e)
        traceback.print_exc()
