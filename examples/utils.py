import hashlib
import logging
from typing import Dict, Optional, Tuple

import aiohttp
from eth_account.messages import encode_structured_data
from starknet_py.hash.address import compute_address
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.account.account import Account
from starknet_py.net.gateway_client import GatewayClient
from starknet_py.net.models import StarknetChainId
from starknet_py.net.networks import CustomGatewayUrls, Network
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starkware.crypto.signature.signature import EC_ORDER
from web3.auto import w3

paradex_http_url = "https://api.testnet.paradex.trade/v1"


async def get_paradex_config() -> Dict:
    logging.info("GET /system/config")
    url = paradex_http_url + "/system/config"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            if status_code == 200:
                logging.info(f"Success: {response}")
            else:
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
                logging.error("Unable to GET /system/config")
    return response


def build_stark_key_message(chain_id: int):
    message = {
        "domain": {"name": "Paradex", "version": "1", "chainId": chain_id},
        "primaryType": "Constant",
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            "Constant": [
                {"name": "action", "type": "string"},
            ],
        },
        "message": {
            "action": "STARK Key",
        },
    }
    return message


def sign_stark_key_message(eth_private_key: int, stark_key_message) -> str:
    w3.eth.account.enable_unaudited_hdwallet_features()
    encoded = encode_structured_data(primitive=stark_key_message)
    signed = w3.eth.account.sign_message(encoded, eth_private_key)
    return signed.signature.hex()


def grind_key(key_seed: int, key_value_limit: int) -> int:
    max_allowed_value = 2**256 - (2**256 % key_value_limit)
    current_index = 0

    def indexed_sha256(seed: int, index: int) -> int:
        def padded_hex(x: int) -> str:
            # Hex string should have an even
            # number of characters to convert to bytes.
            hex_str = hex(x)[2:]
            return hex_str if len(hex_str) % 2 == 0 else "0" + hex_str

        digest = hashlib.sha256(bytes.fromhex(padded_hex(seed) + padded_hex(index))).hexdigest()
        return int(digest, 16)

    key = indexed_sha256(seed=key_seed, index=current_index)
    while key >= max_allowed_value:
        current_index += 1
        key = indexed_sha256(seed=key_seed, index=current_index)

    return key % key_value_limit


def get_private_key_from_eth_signature(eth_signature_hex: str) -> int:
    r = eth_signature_hex[2 : 64 + 2]
    return grind_key(int(r, 16), EC_ORDER)


def derive_stark_key_from_eth_key(msg: str, eth_private_key: str) -> int:
    message_signature = sign_stark_key_message(eth_private_key, msg)
    private_key = get_private_key_from_eth_signature(message_signature)
    return private_key


def get_acc_contract_address_and_call_data(
    proxy_contract_hash: str, account_class_hash: str, public_key: str
) -> str:
    calldata = [
        int(account_class_hash, 16),
        get_selector_from_name("initialize"),
        2,
        int(public_key, 16),
        0,
    ]

    address = compute_address(
        class_hash=int(proxy_contract_hash, 16),
        constructor_calldata=calldata,
        salt=int(public_key, 16),
    )
    return hex(address)


def generate_paradex_account(
    paradex_config: Dict, eth_account_private_key_hex: str
) -> Tuple[str, str]:
    eth_chain_id = int(paradex_config['l1_chain_id'])
    stark_key_msg = build_stark_key_message(eth_chain_id)
    paradex_private_key = derive_stark_key_from_eth_key(stark_key_msg, eth_account_private_key_hex)
    paradex_key_pair = KeyPair.from_private_key(paradex_private_key)
    paradex_account_private_key_hex = hex(paradex_private_key)
    paradex_account_address = get_acc_contract_address_and_call_data(
        paradex_config['paraclear_account_proxy_hash'],
        paradex_config['paraclear_account_hash'],
        hex(paradex_key_pair.public_key),
    )
    return paradex_account_address, paradex_account_private_key_hex


# Network
def network_from_base(base: str) -> Network:
    return CustomGatewayUrls(
        feeder_gateway_url=f'{base}/feeder_gateway', gateway_url=f'{base}/gateway'
    )


def get_account_client(
    net: Network, chain: Optional[StarknetChainId], account_address: str, account_key: str
):
    client = GatewayClient(net=net)
    key_pair = KeyPair.from_private_key(key=int(account_key, 16))
    account_client = Account(
        client=client,
        address=account_address,
        key_pair=key_pair,
        chain=chain,
    )
    return account_client
