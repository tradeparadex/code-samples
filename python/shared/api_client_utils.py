import hashlib
import json
import logging
import os
from decimal import Decimal
from enum import IntEnum
from typing import Optional, Tuple

from eth_account.hdaccount import generate_mnemonic
from eth_account.messages import encode_structured_data
from .paradex_api_utils import Order
from starknet_py.hash.address import compute_address
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.common import int_from_bytes
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.utils.typed_data import TypedData
from starkware.crypto.signature.signature import EC_ORDER
from web3.auto import w3

from helpers.account import Account


class TokenExpired(Exception):
    "V2: Raised when jwt token expired on RestAPI call"
    pass


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def is_token_expired(status_code: int, response: dict) -> bool:
    return (
        True
        if (
            status_code == 401
            and response["message"].startswith("invalid bearer jwt: token is expired by")
        )
        else False
    )


def get_chain_id(chain_id: str):
    class CustomStarknetChainId(IntEnum):
        PRIVATE_TESTNET = int_from_bytes(chain_id.encode("UTF-8"))
    return CustomStarknetChainId.PRIVATE_TESTNET


def get_account(account_address: str, account_key: str, paradex_config: dict):
    client = FullNodeClient(node_url=paradex_config["starknet_fullnode_rpc_url"])
    key_pair = KeyPair.from_private_key(key=int(account_key, 16))
    chain = get_chain_id(paradex_config["starknet_chain_id"])
    account = Account(
        client=client,
        address=account_address,
        key_pair=key_pair,
        chain=chain,
    )
    return account


# Messages
def auth_message(chainId: int, now: int, expiry: int) -> TypedData:
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


def onboarding_message(chainId: int) -> TypedData:
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


def stark_key_message(chainId: int):
    message = {
        "domain": {"name": "Paradex", "version": "1", "chainId": chainId},
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


def order_sign_message(chainId: int, o: Order):
    message = {
        "domain": {"name": "Paradex", "chainId": hex(chainId), "version": "1"},
        "primaryType": "Order",
        "types": {
            "StarkNetDomain": [
                {"name": "name", "type": "felt"},
                {"name": "chainId", "type": "felt"},
                {"name": "version", "type": "felt"},
            ],
            "Order": [
                {
                    "name": "timestamp",
                    "type": "felt",
                },  # Time of signature request in ms since epoch; Acts as a nonce;
                {"name": "market", "type": "felt"},  # E.g.: "ETH-USD-PERP"
                {"name": "side", "type": "felt"},  # Buy or Sell
                {"name": "orderType", "type": "felt"},  # Limit or Market
                {"name": "size", "type": "felt"},  # Quantum value with 8 decimals;
                {
                    "name": "price",
                    "type": "felt",
                },  # Quantum value with 8 decimals; Limit price or 0 at the moment of signature
            ],
        },
        "message": {
            "timestamp": str(o.signature_timestamp),
            "market": o.market,  # As encoded short string
            "side": o.order_side.chain_side(),  # 1: BUY, 2: SELL
            "orderType": o.order_type.value,  # As encoded short string
            "size": o.chain_size(),
            "price": o.chain_price(),
        },
    }
    return message


def flatten_signature(sig: list[str]) -> str:
    return f'["{sig[0]}","{sig[1]}"]'


# Network
def get_acc_contract_address_and_call_data(
    proxy_contract_hash: str, account_class_hash: str, public_key: str
) -> str:
    # call_data = {
    #     'implementation': account_class_hash,
    #     'selector': get_selector_from_name("initialize"),
    #     'calldata': {
    #         'signer':int(public_key,16),
    #         'guardian':0,
    #     }
    # }
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


def gen_and_save_recovery_phrase() -> str:
    if os.path.exists("recovery_phrase.txt"):
        with open("recovery_phrase.txt", "r") as f:
            recovery_phrase = f.read()
        return recovery_phrase
    recovery_phrase = generate_mnemonic(lang="english", num_words=12)
    with open("recovery_phrase.txt", "w") as f:
        f.write(recovery_phrase)
    return recovery_phrase


def get_recovery_phrase_dict(config: dict) -> str:
    if config.get("paradex_environment") and config.get("paradex_environment") == "local":
        return gen_and_save_recovery_phrase()
    else:
        return config.get("ethereum_hd_phrase")


def generate_keys(menmonic: str, address_index: str) -> Optional[Tuple[str, str]]:
    w3.eth.account.enable_unaudited_hdwallet_features()
    account = w3.eth.account.from_mnemonic(
        menmonic, account_path=f"m/44'/60'/0'/0/{address_index}"
    )
    return account.address, account.key.hex()


def sign_stark_key_message(eth_private_key: int, stark_key_message) -> str:
    w3.eth.account.enable_unaudited_hdwallet_features()
    encoded = encode_structured_data(primitive=stark_key_message)
    print("encoded", encoded)
    signed = w3.eth.account.sign_message(encoded, eth_private_key)
    print("signed object", signed)
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


# describe('Private stark key from eth signature', () => {
#   it('should derive private stark key from eth signature correctly',
# () => {
#     const ethSignature =
# '0x21fbf0696d5e0aa2ef41a2b4ffb623bcaf070461d61cf7251c74161f82fec3a43'+
# '70854bc0a34b3ab487c1bc021cd318c734c51ae29374f2beb0e6f2dd49b4bf41c';
#     expect(getPrivateKeyFromEthSignature(ethSignature)).to.equal(
#       '766f11e90cd7c7b43085b56da35c781f8c067ac0d578eabdceebc4886435bda'
#     );
#   });
# });
def get_private_key_from_eth_signature(eth_signature_hex: str) -> int:
    r = eth_signature_hex[2 : 64 + 2]
    return grind_key(int(r, 16), EC_ORDER)


# https://github.com/starkware-libs/\
# starkware-crypto-utils/blob/d3a1e655105afd66ebc07f88a179a3042407cc7b\
# /src/js/key_derivation.js
# /*
#  Returns a private stark key based on a given Eth signature.
#  The given signature should be a 130 character hex string produced
#  by the user signing a
#  predetermined message in order to guarantee getting the same private
#  key each time it is invoked.
# */
# function getPrivateKeyFromEthSignature(ethSignature) {
#   const ethSignatureFixed = ethSignature.replace(/^0x/, '');
#   assert(isHexOfLength(ethSignatureFixed, ETH_SIGNATURE_LENGTH));
#   const r = ethSignatureFixed.substring(0, 64);
#   return grindKey(r, ec.n);
# }
def derive_stark_key_from_eth_key(msg: str, eth_private_key: str) -> int:
    signed_message = sign_stark_key_message(eth_private_key, msg)
    private_key = get_private_key_from_eth_signature(signed_message)
    return private_key


def generate_accounts_dict(config: dict) -> dict:
    FN = "generate_accounts_dict"
    if config.get("ethereum_private_key"):
        w3.eth.account.enable_unaudited_hdwallet_features()
        account = w3.eth.account.from_key(config.get("ethereum_private_key"))
        eth_address, eth_priv = account.address, account.key.hex()
    else:
        mnemonic = get_recovery_phrase_dict(config)
        eth_address, eth_priv = generate_keys(mnemonic, config.get("pod_index"))

    logging.info(f"{FN} address: {eth_address}")
    config["ethereum_account"] = eth_address
    eth_chain_id = int(config.get("paradex_config", {}).get("l1_chain_id"))
    msg = stark_key_message(eth_chain_id)
    logging.info(f"{FN} stark_key_message: {msg}")
    # this can be replaces with kms?
    private_key = derive_stark_key_from_eth_key(msg, eth_priv)
    logging.info(f"{FN} private_key:{private_key}")
    key_pair = KeyPair.from_private_key(private_key)
    logging.info(f"{FN} pub_key: {hex(key_pair.public_key)}")
    config["paradex_account_private_key"] = hex(private_key)
    proxy_class_hash = config["paradex_config"]['paraclear_account_proxy_hash']
    account_class_hash = config["paradex_config"]['paraclear_account_hash']
    config["paradex_account"] = get_acc_contract_address_and_call_data(
        proxy_class_hash,
        account_class_hash,
        hex(key_pair.public_key),
    )
    logging.info(f"{FN} config.paradex_account: {config['paradex_account']}")
    return config
