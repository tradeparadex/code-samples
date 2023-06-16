import asyncio
import logging
import os
import time
import traceback
from typing import Dict, List

import aiohttp
from starknet_py.common import int_from_bytes
from starknet_py.utils.typed_data import TypedData
from web3.auto import w3
from utils import (
    generate_paradex_account,
    get_paradex_config,
    network_from_base,
    get_account,
)

paradex_http_url = "https://api.testnet.paradex.trade/v1"


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


async def perform_onboarding(
    paradex_config: Dict,
    paradex_http_url: str,
    account_address: str,
    private_key: str,
    ethereum_account: str,
):
    network = network_from_base(paradex_config["starknet_gateway_url"])
    chain = int_from_bytes(paradex_config["starknet_chain_id"].encode())
    account = get_account(
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
    account = get_account(
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
