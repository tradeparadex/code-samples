import aiohttp
import asyncio
import hashlib
import logging
import random
import re
import time
from enum import IntEnum
from typing import Callable, Dict, Optional, Tuple

from eth_account.messages import encode_structured_data
from eth_account.signers.local import LocalAccount
from web3.auto import Web3, w3
from web3.middleware import construct_sign_and_send_raw_middleware

from starknet_py.common import int_from_bytes
from starknet_py.constants import RPC_CONTRACT_ERROR
from starknet_py.hash.address import compute_address
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.client import Client
from starknet_py.net.client_errors import ClientError
from starknet_py.net.client_models import Call, Hash, TransactionExecutionStatus, TransactionFinalityStatus
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.models import Address
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.proxy.contract_abi_resolver import ProxyConfig
from starknet_py.proxy.proxy_check import ArgentProxyCheck, OpenZeppelinProxyCheck, ProxyCheck
from starknet_py.transaction_errors import (
    TransactionRevertedError,
    TransactionNotReceivedError,
)
from starknet_py.utils.typed_data import TypedData
from starkware.crypto.signature.signature import EC_ORDER

from helpers.account import Account


paradex_http_url = "https://api.testnet.paradex.trade/v1"


def build_auth_message(chainId: int, now: int, expiry: int) -> TypedData:
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


def build_stark_key_message(chain_id: int) -> TypedData:
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


def sign_stark_key_message(eth_private_key: int, stark_key_message) -> str:
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


def get_paradex_account_address(paradex_config: Dict, paradex_account_private_key_hex: str) -> str:
    paradex_key_pair = KeyPair.from_private_key(hex_to_int(paradex_account_private_key_hex))
    paradex_account_address = get_acc_contract_address_and_call_data(
        paradex_config['paraclear_account_proxy_hash'],
        paradex_config['paraclear_account_hash'],
        hex(paradex_key_pair.public_key),
    )
    return paradex_account_address


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


def get_chain_id(chain_id: str):
    class CustomStarknetChainId(IntEnum):
        PRIVATE_TESTNET = int_from_bytes(chain_id.encode("UTF-8"))
    return CustomStarknetChainId.PRIVATE_TESTNET


def get_account(account_address: str, account_key: str, paradex_config: dict):
    client = FullNodeClient(node_url=paradex_config["starknet_fullnode_rpc_url"])
    key_pair = KeyPair.from_private_key(key=hex_to_int(account_key))
    chain = get_chain_id(paradex_config["starknet_chain_id"])
    account = Account(
        client=client,
        address=account_address,
        key_pair=key_pair,
        chain=chain,
    )
    return account


def get_random_max_fee(start=1e18, end=1e19) -> int:
    return random.randint(start, end)


def get_proxy_config():
    return ProxyConfig(
        max_steps=5,
        proxy_checks=[StarkwareETHProxyCheck(), ArgentProxyCheck(), OpenZeppelinProxyCheck()],
    )


class StarkwareETHProxyCheck(ProxyCheck):
    async def implementation_address(self, address: Address, client: Client) -> Optional[int]:
        return await self.get_implementation(
            address=address,
            client=client,
            get_class_func=client.get_class_hash_at,
            regex_err_msg=r"(is not deployed)",
        )

    async def implementation_hash(self, address: Address, client: Client) -> Optional[int]:
        return await self.get_implementation(
            address=address,
            client=client,
            get_class_func=client.get_class_by_hash,
            regex_err_msg=r"(is not declared)",
        )

    @staticmethod
    async def get_implementation(
        address: Address, client: Client, get_class_func: Callable, regex_err_msg: str
    ) -> Optional[int]:
        call = StarkwareETHProxyCheck._get_implementation_call(address=address)
        err_msg = r"(Entry point 0x[0-9a-f]+ not found in contract)|" + regex_err_msg
        try:
            (implementation,) = await client.call_contract(call=call)
            await get_class_func(implementation)
        except ClientError as err:
            if (re.search(err_msg, err.message, re.IGNORECASE) or err.code == RPC_CONTRACT_ERROR):
                return None
            raise err
        return implementation

    @staticmethod
    def _get_implementation_call(address: Address) -> Call:
        return Call(
            to_addr=address,
            selector=get_selector_from_name("implementation"),
            calldata=[],
        )


# Forked from https://github.com/software-mansion/starknet.py/blob/development/starknet_py/net/client.py#L134
# Method tweaked to wait for `ACCEPTED_ON_L1` status
async def wait_for_tx(
    client: Client, tx_hash: Hash, check_interval=5
) -> Tuple[int, TransactionFinalityStatus]:
    """
    Awaits for transaction to get accepted or at least pending by polling its status

    :param client: Instance of Client
    :param tx_hash: Transaction's hash
    :param check_interval: Defines interval between checks
    :return: Tuple containing block number and transaction status
    """
    if check_interval <= 0:
        raise ValueError("Argument check_interval has to be greater than 0.")

    try:
        while True:
            result = await client.get_transaction_receipt(tx_hash=tx_hash)

            if result.execution_status == TransactionExecutionStatus.REVERTED:
                raise TransactionRevertedError(
                    message=result.revert_reason,
                )

            if result.finality_status == TransactionFinalityStatus.ACCEPTED_ON_L1:
                assert result.block_number is not None
                return result.block_number, result.finality_status

            await asyncio.sleep(check_interval)
    except asyncio.CancelledError as exc:
        raise TransactionNotReceivedError from exc


def get_l1_eth_account(eth_private_key_hex: str) -> Tuple[Web3, LocalAccount]:
    w3.eth.account.enable_unaudited_hdwallet_features()
    account: LocalAccount = w3.eth.account.from_key(eth_private_key_hex)
    w3.eth.default_account = account.address
    w3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
    return w3, account


def hex_to_int(val: str):
    return int(val, 16)


async def get_jwt_token(
    paradex_config: Dict, paradex_http_url: str, account_address: str, private_key: str
) -> str:
    token = ""

    chain_id = int_from_bytes(paradex_config["starknet_chain_id"].encode())
    account = get_account(account_address, private_key, paradex_config)

    now = int(time.time())
    expiry = now + 24 * 60 * 60
    message = build_auth_message(chain_id, now, expiry)
    sig = account.sign_message(message)

    headers: Dict = {
        "PARADEX-STARKNET-ACCOUNT": account_address,
        "PARADEX-STARKNET-SIGNATURE": f'["{sig[0]}","{sig[1]}"]',
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
