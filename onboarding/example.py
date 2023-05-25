import asyncio
import hashlib
import logging
import os
import time
import traceback
from typing import Dict, List, Optional, Tuple

import aiohttp
from eth_account.messages import encode_structured_data
from starknet_py.common import int_from_bytes
from starknet_py.hash.address import compute_address
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.account.account import Account
from starknet_py.net.gateway_client import GatewayClient
from starknet_py.net.models import StarknetChainId
from starknet_py.net.networks import CustomGatewayUrls, Network
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.utils.typed_data import TypedData
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


def build_onboarding_message(chainId: int) -> TypedData:
    message = {
        "message": {
            "action": "Onboarding",
        },
        "domain": {"name": "Paradex", "chainId": hex(chainId), "version": "1"},
        "primaryType": "Constant",
        "types": {
            "StarkNetDomain": [
                {"name": "name", "type": "felt"},
                {"name": "chainId", "type": "felt"},
                {"name": "version", "type": "felt"},
            ],
            "Constant": [
                {"name": "action", "type": "felt"},
            ],
        },
    }
    return message


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


async def perform_onboarding(
    paradex_config: Dict,
    paradex_http_url: str,
    account_address: str,
    private_key: str,
    ethereum_account: str,
):
    network = network_from_base(paradex_config["starknet_gateway_url"])
    chain = int_from_bytes(paradex_config["starknet_chain_id"].encode())
    account = get_account_client(
        net=network, chain=chain, account_address=account_address, account_key=private_key
    )

    message = build_onboarding_message(chain)
    sig = account.sign_message(message)

    headers = {
        "PARADEX-ETHEREUM-ACCOUNT": ethereum_account,
        "PARADEX-STARKNET-ACCOUNT": account_address,
        "PARADEX-STARKNET-SIGNATURE": f'["{sig[0]}","{sig[1]}"]',
    }

    url = paradex_http_url + '/onboarding'
    body = {'public_key': hex(account.signer.public_key)}

    logging.info(f"POST {url}")
    logging.info(f"Headers: {headers}")
    logging.info(f"Body: {body}")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as response:
            status_code: int = response.status
            if status_code == 200:
                logging.info(f"Success: {response}")
                logging.info("Onboarding successful")
            else:
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
                logging.error("Unable to POST /onboarding")
    return response


def build_auth_message(chainId: int, now: int, expiry: int) -> TypedData:
    # "0x534e5f474f45524c49" - "SN_GOERLI"
    message = {
        "message": {
            "method": "POST",
            "path": "/v1/auth",
            "body": "",
            "timestamp": now,
            "expiration": expiry,
        },
        "domain": {"name": "Paradex", "chainId": hex(chainId), "version": "1"},
        "primaryType": "Request",
        "types": {
            "StarkNetDomain": [
                {"name": "name", "type": "felt"},
                {"name": "chainId", "type": "felt"},
                {"name": "version", "type": "felt"},
            ],
            "Request": [
                {"name": "method", "type": "felt"},
                {"name": "path", "type": "felt"},
                {"name": "body", "type": "felt"},
                {"name": "timestamp", "type": "felt"},
                {"name": "expiration", "type": "felt"},
            ],
        },
    }
    return message


async def get_jwt_token(
    paradex_config: Dict, paradex_http_url: str, account_address: str, private_key: str
) -> str:
    token = ""

    network = network_from_base(paradex_config["starknet_gateway_url"])
    chain = int_from_bytes(paradex_config["starknet_chain_id"].encode())
    account = get_account_client(
        net=network, chain=chain, account_address=account_address, account_key=private_key
    )

    now = int(time.time())
    expiry = now + 24 * 60 * 60
    message = build_auth_message(chain, now, expiry)
    hash = TypedData.from_dict(message).message_hash(account.address)
    sig = account.sign_message(message)

    headers: Dict = {
        "PARADEX-STARKNET-ACCOUNT": account_address,
        "PARADEX-STARKNET-SIGNATURE": f'["{sig[0]}","{sig[1]}"]',
        "PARADEX-STARKNET-MESSAGE-HASH": hex(hash),
        "PARADEX-TIMESTAMP": str(now),
        "PARADEX-SIGNATURE-EXPIRATION": str(expiry),
    }

    url = paradex_http_url + '/auth'

    logging.info(f"POST {url}")
    logging.info(f"Headers: {headers}")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            if status_code == 200:
                logging.info(f"Success: {response}")
                logging.info("Get JWT successful")
            else:
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
                logging.error("Unable to POST /onboarding")
            token = response["jwt_token"]
    return token


async def get_open_orders(
    paradex_http_url: str,
    paradex_jwt: str,
) -> List[Dict]:
    headers = {"Authorization": f"Bearer {paradex_jwt}"}

    url = paradex_http_url + '/orders'

    logging.info(f"GET {url}")
    logging.info(f"Headers: {headers}")

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            if status_code == 200:
                logging.info(f"Success: {response}")
                logging.info("Get Open Orders successful")
                return response["results"]
            else:
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
                logging.error("Unable to POST /onboarding")
    return []


async def main(eth_private_key_hex: str) -> None:
    # Initialize Ethereum account
    w3.eth.account.enable_unaudited_hdwallet_features()
    eth_account = w3.eth.account.from_key(eth_private_key_hex)
    eth_account_address, eth_account_private_key_hex = (
        eth_account.address,
        eth_account.privateKey.hex(),
    )

    # Load Paradex config
    paradex_config = await get_paradex_config()

    # Generate Paradex account (only local)
    paradex_account_address, paradex_account_private_key_hex = generate_paradex_account(
        paradex_config, eth_account_private_key_hex
    )

    # Onboard generated Paradex account
    logging.info("Onboarding...")
    await perform_onboarding(
        paradex_config,
        paradex_http_url,
        paradex_account_address,
        paradex_account_private_key_hex,
        eth_account_address,
    )

    # Get a JWT token to interact with private endpoints
    logging.info("Getting JWT...")
    paradex_jwt = await get_jwt_token(
        paradex_config,
        paradex_http_url,
        paradex_account_address,
        paradex_account_private_key_hex,
    )

    # Get account's open orders using the JWT token
    logging.info("Getting account's open orders...")
    open_orders = await get_open_orders(paradex_http_url, paradex_jwt)

    print(f"Open Orders: {open_orders}")


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
