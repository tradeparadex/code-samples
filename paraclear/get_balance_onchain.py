import asyncio
import re
import requests
import os

from dotenv import load_dotenv
from decimal import Decimal
from enum import Enum
from rich import print
from typing import Callable, Optional, Union

from starknet_py.cairo.felt import FIELD_PRIME
from starknet_py.constants import RPC_CONTRACT_ERROR
from starknet_py.contract import Contract
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.client import Client
from starknet_py.net.client_errors import ClientError
from starknet_py.net.client_models import Call
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.models import Address
from starknet_py.proxy.contract_abi_resolver import ProxyConfig
from starknet_py.proxy.proxy_check import ArgentProxyCheck, OpenZeppelinProxyCheck, ProxyCheck

FEE_TOKEN_QUANTUMS = 18
PARACLEAR_QUANTUMS = 8
USDC_QUANTUMS = 6

print("Current working directory:", os.getcwd())
print("Trying to load .env file...")
load_dotenv()
print(".env file loaded (if it exists)")

# Debug: Print all environment variables
for key, value in os.environ.items():
    print(f"{key}: {value}")

# Environment variables
# TODO: Get from /config
STRK_API_URL = os.getenv("STRK_API_URL")
PRDX_API_URL = os.getenv("PRDX_API_URL")
FULL_NODE_URL = os.getenv("FULL_NODE_URL")
PARACLEAR_ADDRESS = os.getenv("PARACLEAR_ADDRESS")
L2_ADDRESS = os.getenv("L2_ADDRESS")


class MarginCheckType(int, Enum):
    INITIAL = (1,)
    MAINTENANCE = (2,)
    BANKRUPTCY = 3


class PerpetualAssetBalance:
    market: str
    amount: Decimal
    cost: Decimal
    cached_funding: Decimal

    def __init__(
        self, market: str, amount: Decimal, cost: Decimal, cached_funding: Decimal
    ):
        self.market = market
        self.amount = amount
        self.cost = cost
        self.cached_funding = cached_funding


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
            if re.search(err_msg, err.message, re.IGNORECASE) or err.code == RPC_CONTRACT_ERROR:
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


def as_int(value: int) -> int:
    """
    Returns the lift of the given field element, val, as an integer
    in the range (-prime/2, prime/2).
    """
    return value if value < FIELD_PRIME // 2 else value - FIELD_PRIME


def to_decimal(value_felt: int, decimals=PARACLEAR_QUANTUMS):
    int_value = as_int(value_felt)
    output = Decimal(int_value).scaleb(-decimals)
    return output

def int_16(val):
    if isinstance(val, str):
        return int(val, 16)
    elif isinstance(val, int):
        return val
    else:
        raise ValueError(f"Expected string or integer, got {type(val)}")


def get_client(node_url: str = FULL_NODE_URL):
    return FullNodeClient(node_url=node_url)


def get_proxy_config():
    return ProxyConfig(
        max_steps=5,
        proxy_checks=[StarkwareETHProxyCheck(), ArgentProxyCheck(), OpenZeppelinProxyCheck()],
    )


async def load_contract(
    address: str,
    client: FullNodeClient,
    proxy_config: Union[bool, ProxyConfig] = get_proxy_config(),
) -> Contract:
    return await Contract.from_address(
        address=address, provider=client, proxy_config=proxy_config
    )

def get_markets_from_api():
    headers = {"Accept": "application/json"}
    try:
        resp = requests.get(f"{PRDX_API_URL}/markets", headers=headers)
        # Print status code and response content for debugging
        print(f"Status Code: {resp.status_code}")
        
        # Raise an exception for bad status codes
        resp.raise_for_status()
        
        # Try to parse JSON
        try:
            data = resp.json()
        except requests.exceptions.JSONDecodeError as e:
            print(f"JSONDecodeError: {e}")
            print(f"Response content: {resp.text}")
            return []

        if "results" in data:
            return [r["symbol"] for r in data["results"]]
        else:
            print("Expected 'results' key not found in API response")
            print(f"Response data: {data}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []


async def get_balance(target_address: str):
    print("Loading Client...")
    target_address_int = int_16(target_address)

    client = get_client(node_url=FULL_NODE_URL)
    print("Client loaded")
    print("Loading Paraclear contract...")
    paraclear_contract = await load_contract(PARACLEAR_ADDRESS, client=client)
    print("Paraclear contract loaded")

    acc_value_call = await paraclear_contract.functions["getAccountValue"].call(
        account=target_address_int
    )

    im_health_check_call = await paraclear_contract.functions[
        "getAccountHealthCheck"].call(
        account=target_address_int,
        margin_check_type=MarginCheckType.INITIAL.value
        )

    mm_health_check_call = await paraclear_contract.functions[
        "getAccountHealthCheck"
    ].call(
        account=target_address_int,
        margin_check_type=MarginCheckType.MAINTENANCE.value
    )

    print("------------------")

    print(f"Account: {target_address}")

    print("------------------")

    print(f"Account value: {to_decimal(acc_value_call.account_value)}")
    print(f"Account healthy (IM): {bool(im_health_check_call.is_healthy)}")
    print(f"Account healthy (MM): {bool(mm_health_check_call.is_healthy)}")
    print("------------------\n")
    print("Perpetual balances:")

    markets = get_markets_from_api()

    for market_str in markets:
        perpetual_asset_bal = await paraclear_contract.functions[
            "getPerpetualAssetBalance"
        ].call(account=target_address_int, market=market_str)
        perp_bal = PerpetualAssetBalance(
            market=market_str,
            amount=to_decimal(perpetual_asset_bal.balance["amount"]),
            cost=to_decimal(perpetual_asset_bal.balance["cost"]),
            cached_funding=to_decimal(perpetual_asset_bal.balance["cached_funding"]),
        )
        print(
            f"{perp_bal.market}:\n\tamount: {perp_bal.amount}\n\tcost: {perp_bal.cost}\n\tcached_funding: {perp_bal.cached_funding}",
        )


async def main():
    await get_balance(L2_ADDRESS)


if __name__ == "__main__":
    asyncio.run(main())
