"""
Description:
    Paradex client. To be replaced by generated stubs
"""

# built ins
import asyncio
import base64
import hmac
import json
import logging
import sys
import time
from typing import Dict, List, Tuple

import aiohttp
import websockets
from .api_client_utils import (
    DecimalEncoder,
    auth_message,
    derive_stark_key_from_eth_key,
    flatten_signature,
    gen_and_save_recovery_phrase,
    generate_keys,
    get_acc_contract_address_and_call_data,
    get_account,
    is_token_expired,
    onboarding_message,
    order_sign_message,
    stark_key_message,
)
from .api_config import ApiConfig
from .paradex_api_utils import Order
from starknet_py.common import int_from_bytes
from starknet_py.contract import Contract
from starknet_py.net.signer.stark_curve_signer import KeyPair
from .starknet_utils import get_proxy_config
from web3.auto import w3

from helpers.account import Account


# RESToverHTTP Interface
async def sign_request(
    paradex_maker_secret_key: str, method: str, path: str, body: Dict
) -> Tuple[int, bytes]:
    """
    Creates the required signature necessary
    as apart of all RESToverHTTP requests with Paradex.
    """
    _secret_key: bytes = paradex_maker_secret_key.encode("utf-8")
    _method: bytes = method.encode("utf-8")
    _path: bytes = path.encode("utf-8")
    _body: bytes = body.encode("utf-8")
    signing_key: bytes = base64.b64decode(_secret_key)
    timestamp: str = str(int(time.time() * 1000)).encode("utf-8")
    message: bytes = b"\n".join([timestamp, _method.upper(), _path, _body])
    digest: hmac.digest = hmac.digest(signing_key, message, "sha256")
    signature: bytes = base64.b64encode(digest)

    return timestamp, signature


async def create_rest_headers(
    paradex_jwt: str,
    paradex_maker_secret_key: str,
    method: str,
    path: str,
    body: Dict,
) -> Dict:
    """
    Creates the required headers to authenticate
    Paradex RESToverHTTP requests.
    """
    # timestamp, signature = await sign_request(
    #     paradex_maker_secret_key=paradex_maker_secret_key,
    #     method=method,
    #     path=path,
    #     body=body
    #     )

    headers: Dict = {
        # 'Paradex-API-Timestamp': timestamp.decode('utf-8'),
        # 'Paradex-API-Signature': signature.decode('utf-8'),
        "Authorization": f"Bearer {paradex_jwt}"
    }

    return headers


async def get_open_orders(
    paradex_http_url: str,
    paradex_jwt: str,
) -> List[Dict]:
    """
    Paradex RESToverHTTP endpoint.
    [GET] /orders
    """
    logging.info("Getting Open Orders")
    method: str = "GET"
    path: str = "/orders"

    headers: Dict = await create_rest_headers(
        paradex_jwt=paradex_jwt,
        paradex_maker_secret_key="",
        method=method,
        path=path,
        body="",
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(paradex_http_url + path, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            logging.debug("GET /orders: ", response)
            check_token_expiry(status_code=status_code, response=response)
            if status_code != 200:
                logging.error("Unable to [GET] /orders")
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
            response = response["results"]
    return response


async def fetch_account(
    paradex_http_url: str,
    paradex_jwt: str,
) -> List[Dict]:
    """
    Paradex RESToverHTTP endpoint.
    [GET] /account
    """
    logging.info("Getting Account state")
    method: str = "GET"
    path: str = "/account"

    headers: Dict = await create_rest_headers(
        paradex_jwt=paradex_jwt,
        paradex_maker_secret_key="",
        method=method,
        path=path,
        body="",
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(paradex_http_url + path, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            check_token_expiry(status_code=status_code, response=response)
            if status_code != 200:
                logging.error("Unable to [GET] /account")
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
    return response


async def fetch_transfers(
    paradex_http_url: str,
    paradex_jwt: str,
) -> List[Dict]:
    """
    Paradex RESToverHTTP endpoint.
    [GET] /account/transfers
    """
    logging.info("Getting Account state")
    method: str = "GET"
    path: str = "/account/transfers"

    headers: Dict = await create_rest_headers(
        paradex_jwt=paradex_jwt,
        paradex_maker_secret_key="",
        method=method,
        path=path,
        body="",
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(paradex_http_url + path, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            check_token_expiry(status_code=status_code, response=response)
            if status_code != 200:
                logging.error("Unable to [{method}] {path}")
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
    return response


async def fetch_positions(
    paradex_http_url: str,
    paradex_jwt: str,
) -> List[Dict]:
    """
    Paradex RESToverHTTP endpoint.
    [GET] /positions
    """
    FN = "private_get_positions"
    logging.info("Getting Positions")
    method: str = "GET"
    path: str = "/positions"

    headers: Dict = await create_rest_headers(
        paradex_jwt=paradex_jwt,
        paradex_maker_secret_key="",
        method=method,
        path=path,
        body="",
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(paradex_http_url + path, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            check_token_expiry(status_code=status_code, response=response)
            if status_code != 200:
                logging.error(
                    f"{FN} Unable to [GET] {path}"
                    f" Status Code: {status_code}"
                    f" Response: {response}"
                )
            response = response["results"]
    return response


async def fetch_tokens(
    paradex_http_url: str,
    paradex_jwt: str,
) -> List[Dict]:
    """
    Paradex RESToverHTTP endpoint.
    [GET] /balance
    """
    logging.info("Getting Token balances")
    method: str = "GET"
    path: str = "/balance"

    headers: Dict = await create_rest_headers(
        paradex_jwt=paradex_jwt,
        paradex_maker_secret_key="",
        method=method,
        path=path,
        body="",
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(paradex_http_url + path, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            check_token_expiry(status_code=status_code, response=response)
            logging.info(f"Token Balances: {response}")
            if status_code != 200:
                logging.error("Unable to [GET] /balances")
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
            response = response["results"]
    return response


async def fetch_trades(paradex_http_url: str, paradex_jwt: str, market: str) -> None:
    """
    Paradex RESToverHTTP endpoint.
    [GET] /trades
    """
    logging.info("Getting Trades")
    method: str = "GET"
    path: str = "/trades"

    headers: Dict = await create_rest_headers(
        paradex_jwt=paradex_jwt,
        paradex_maker_secret_key="",
        method=method,
        path=path,
        body="",
    )
    params = {"market": market}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            paradex_http_url + path, headers=headers, params=params
        ) as response:
            status_code: int = response.status
            logging.info(f"URL: {response.url}")
            response: Dict = await response.json()
            check_token_expiry(status_code=status_code, response=response)
            if status_code != 200:
                logging.error("Unable to [GET] /trades")
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
            response = response["results"]
    return response


def check_token_expiry(status_code: int, response: Dict) -> None:
    """
    Checks the response from the Paradex API
    to see if the token has expired.
    """
    if is_token_expired(status_code, response):
        logging.info(response["message"])
        logging.error("Token has expired, please restart the bot.")
        sys.exit(1)


async def post_order_payload(paradex_http_url: str, paradex_jwt: str, payload: dict) -> dict:
    """
    Paradex RESToverHTTP endpoint.
    [POST] /orders
    """
    method: str = "POST"
    path: str = "/orders"
    _payload: str = json.dumps(payload, cls=DecimalEncoder)
    headers: Dict = await create_rest_headers(
        paradex_jwt=paradex_jwt,
        paradex_maker_secret_key="",
        method=method,
        path=path,
        body=_payload,
    )
    response = {}
    logging.debug(f"post_order_payload:{payload}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                paradex_http_url + path, headers=headers, json=payload
            ) as response:
                status_code: int = response.status
                response: Dict = await response.json(content_type=None)
                response["status_code"] = status_code
                check_token_expiry(status_code=status_code, response=response)
                if status_code == 201:
                    logging.info(f"Order Created: {status_code} | Response: {response}")
                else:
                    logging.warning(
                        "Unable to [POST] /orders"
                        f" Status Code:{status_code}"
                        f" Response Text:{response}"
                        f" Order Payload:{payload}"
                    )
        except aiohttp.ClientConnectorError as e:
            logging.error(f"[POST] /orders ClientConnectorError: {e}")
    return response


async def delete_order_payload(paradex_http_url: str, paradex_jwt: str, order_id: str) -> bool:
    """
    Paradex RESToverHTTP endpoint.
    [DELETE] /orders/{order_id}
    """
    method: str = "DELETE"
    path: str = f"/orders/{order_id}"
    ret_val = False
    headers: Dict = await create_rest_headers(
        paradex_jwt=paradex_jwt,
        paradex_maker_secret_key="",
        method=method,
        path=path,
        body="",
    )

    async with aiohttp.ClientSession() as session:
        try:
            async with session.delete(paradex_http_url + path, headers=headers) as response:
                status_code: int = response.status
                response: Dict = await response.json(content_type=None)
                check_token_expiry(status_code=status_code, response=response)
                if status_code == 201 or status_code == 204:
                    logging.info(f"Order cancelled: {status_code} | Id: {order_id}")
                    ret_val = True
                else:
                    logging.info(f"Unable to [DELETE] {path}")
                    logging.info(f"Status Code: {status_code}")
                    logging.info(f"Response Text: {response}")

        except aiohttp.ClientConnectorError as e:
            logging.error(f"[DELETE] /orders ClientConnectorError: {e}")
    return ret_val


async def get_markets(
    paradex_http_url: str,
    paradex_jwt: str,
) -> List[Dict]:
    """
    Paradex RESToverHTTP endpoint.
    [GET] /markets
    """
    logging.info("Getting markets...")
    method: str = "GET"
    path: str = "/markets"
    payload: str = ""

    headers: Dict = await create_rest_headers(
        paradex_jwt=paradex_jwt,
        paradex_maker_secret_key=None,
        method=method,
        path=path,
        body=payload,
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(paradex_http_url + path, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            check_token_expiry(status_code=status_code, response=response)
            logging.debug("GET /markets: ", response)
            if status_code != 200:
                message: str = "Unable to [GET] /markets"
                logging.error(message)
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
            response = response["results"]
    return response


async def get_paradex_config(
    paradex_http_url: str,
) -> Dict:
    """
    Paradex RESToverHTTP endpoint.
    [GET] /config
    """
    logging.info("Getting config...")
    path: str = "/system/config"

    headers = dict()

    async with aiohttp.ClientSession() as session:
        async with session.get(paradex_http_url + path, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            logging.info(response)
            if status_code != 200:
                message: str = "Unable to [GET] /system/config"
                logging.error(message)
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
    return response


# JSON-RPCoverWebsocket Interface
async def send_heartbeat_id(websocket: websockets.WebSocketClientProtocol, id: int) -> None:
    """
    Sends a Heartbeat to keep the Paradex WebSocket connection alive.
    """
    await websocket.send(json.dumps({"id": id, "jsonrpc": "2.0", "method": "heartbeat"}))
    logging.debug(f"send_heartbeat_id:{id}")


async def send_auth_id(
    websocket: websockets.WebSocketClientProtocol, paradex_jwt: str, msg_id: str
) -> None:
    """
    Sends an authentication message to the Paradex WebSocket.
    """
    await websocket.send(
        json.dumps(
            {
                "id": msg_id,
                "jsonrpc": "2.0",
                "method": "auth",
                "params": {"bearer": paradex_jwt},
            }
        )
    )


async def subscribe_channel_with_id(
    websocket: websockets.WebSocketClientProtocol, channel: str, sub_id: int
) -> None:
    """
    Subscribe to a named `` WS Channel.
    """
    await websocket.send(
        json.dumps(
            {
                "id": sub_id,
                "jsonrpc": "2.0",
                "method": "subscribe",
                "params": {"channel": channel},
            }
        )
    )


def starknet_account(config: ApiConfig) -> Account:
    if config.starknet_account is not None:
        return config.starknet_account

    account = get_account(
        account_address=config.paradex_account,
        account_key=config.paradex_account_private_key,
        paradex_config=config.paradex_config,
    )
    config.starknet_account = account
    return account


async def get_usdc_balance(config: ApiConfig) -> int:
    logging.info("get_usdc_balance")
    usdc_address = config.paradex_config["bridged_tokens"][0]["l2_token_address"]
    account = starknet_account(config)
    usdc_contract_balance = await account.get_balance(usdc_address)
    return usdc_contract_balance


async def deposit_to_paraclear(config: ApiConfig, amount: int) -> None:
    paraclear_address = config.paradex_config["paraclear_address"]
    account = starknet_account(config)
    paraclear_contract = await Contract.from_address(
        provider=account, address=paraclear_address, proxy_config=get_proxy_config()
    )
    logging.info(f"Paraclear Contract: {hex(paraclear_contract.address)}")
    usdc_address = config.paradex_config["bridged_tokens"][0]["l2_token_address"]
    usdc_decimals = config.paradex_config["bridged_tokens"][0]["decimals"]
    usdc_contract = await Contract.from_address(
        provider=account, address=usdc_address, proxy_config=get_proxy_config()
    )
    logging.info(f"USDC Contract: {usdc_contract}")

    amount_usdc = await get_usdc_balance(config)
    amount_paraclear = int(amount * 10 ** (8 - usdc_decimals))
    calls = [
        usdc_contract.functions["increaseAllowance"].prepare_invoke_v1(
            spender=int(paraclear_address, 16), addedValue=amount_usdc
        ),
        paraclear_contract.functions["deposit"].prepare_invoke_v1(int(usdc_address, 16), amount_paraclear),
    ]
    logging.info(f"Allowance increase to paraclear completed: {calls}")
    deposit_info = await account.execute_v1(calls=calls, max_fee=int(5 * 1e17))
    logging.info(f"Deposit Info: {deposit_info}")
    logging.info(f"Waiting for deposit to complete: {deposit_info.transaction_hash}")
    tx_status = await account.client.wait_for_tx(deposit_info.transaction_hash)
    logging.info(f"Deposit completed: {tx_status}")
    return amount / 10**8


async def get_jwt_token(
    paradex_config: Dict, paradex_http_url: str, account_address: str, private_key: str
) -> str:
    logging.info("get_jwt_token")
    token = ""
    chain = int_from_bytes(paradex_config["starknet_chain_id"].encode())
    account = get_account(
        account_address=account_address, account_key=private_key, paradex_config=paradex_config
    )
    now = int(time.time())
    expiry = now + 24 * 60 * 60
    message = auth_message(chain, now, expiry)

    sig = account.sign_message(message)

    headers: Dict = {
        "PARADEX-STARKNET-ACCOUNT": account_address,
        "PARADEX-STARKNET-SIGNATURE": flatten_signature(sig),
        "PARADEX-TIMESTAMP": str(now),
        "PARADEX-SIGNATURE-EXPIRATION": str(expiry),
    }
    path: str = "/auth"
    logging.info(f"get_jwt_token path:{paradex_http_url + path} headers:{headers}")
    async with aiohttp.ClientSession() as session:
        async with session.post(paradex_http_url + path, headers=headers) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            if status_code != 200:
                message: str = "Unable to [POST] /auth"
                logging.error(message)
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
            logging.info(f"token response:{response}")
            token = response["jwt_token"]
    logging.info("get_jwt_token done")
    return token


async def onboarding(
    paradex_config: Dict,
    paradex_http_url: str,
    account_address: str,
    private_key: str,
    ethereum_account: str,
) -> str:
    chain = int_from_bytes(paradex_config["starknet_chain_id"].encode())
    print("chain", hex(chain))
    account = get_account(
        account_address=account_address, account_key=private_key, paradex_config=paradex_config
    )
    message = onboarding_message(chain)

    sig = account.sign_message(message)

    headers: Dict = {
        "PARADEX-ETHEREUM-ACCOUNT": ethereum_account,
        "PARADEX-STARKNET-ACCOUNT": account_address,
        "PARADEX-STARKNET-SIGNATURE": flatten_signature(sig),
    }
    path: str = '/onboarding'
    body = {'public_key': hex(account.signer.public_key)}
    print(body)
    json_body = json.dumps(body)
    print(json_body)

    logging.info(f"onboarding path:{paradex_http_url + path} headers:{headers}")
    async with aiohttp.ClientSession() as session:
        async with session.post(paradex_http_url + path, headers=headers, json=body) as response:
            status_code: int = response.status
            if status_code != 200:
                message: str = "Unable to [POST] /onboarding"
                logging.error(message)
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
            logging.info(f"token response:{response}")
    logging.info("onboarding done")
    return response


def custom_exception_handler(loop, context):
    loop = asyncio.get_event_loop()
    # first, handle with default handler
    loop.default_exception_handler(context)
    loop.stop()


def sign_order(config: ApiConfig, o: Order) -> Tuple[str, str]:
    account = starknet_account(config)
    message = order_sign_message(account._chain_id.value, o)

    sig = account.sign_message(message)
    flat_sig = flatten_signature(sig)
    return flat_sig


def get_recovery_phrase(config: ApiConfig) -> str:
    if config.paradex_environment == "local":
        return gen_and_save_recovery_phrase()
    else:
        return config.ethereum_hd_phrase


def generate_accounts(config: ApiConfig):
    if config.ethereum_private_key != "":
        w3.eth.account.enable_unaudited_hdwallet_features()
        account = w3.eth.account.from_key(config.ethereum_private_key)
        eth_address, eth_priv = account.address, account.key.hex()
    else:
        mnemonic = get_recovery_phrase(config)
        eth_address, eth_priv = generate_keys(mnemonic, config.pod_index)

    print("address: ", eth_address)
    config.ethereum_account = eth_address
    eth_chain_id = int(config.paradex_config['l1_chain_id'])
    msg = stark_key_message(eth_chain_id)
    print("msg: ", msg)
    # this can be replaces with kms?
    private_key = derive_stark_key_from_eth_key(msg, eth_priv)
    print("private_key: ", private_key)
    key_pair = KeyPair.from_private_key(private_key)
    print("pub_key: ", hex(key_pair.public_key))
    config.paradex_account_private_key = hex(private_key)
    proxy_class_hash = config.paradex_config['paraclear_account_proxy_hash']
    account_class_hash = config.paradex_config['paraclear_account_hash']
    account_address = get_acc_contract_address_and_call_data(
        proxy_class_hash,
        account_class_hash,
        hex(key_pair.public_key),
    )
    print("account_address: ", account_address)
    config.paradex_account = account_address
    print("config.paradex_account: ", config.paradex_account)
