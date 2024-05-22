import asyncio
import logging
import os
import time
import traceback
from typing import Dict, List
import json
from decimal import Decimal
import aiohttp
from starknet_py.common import int_from_bytes
from starknet_py.utils.typed_data import TypedData
from utils import (
    generate_paradex_account,
    get_account,
    get_l1_eth_account,
    sign_stark_key_message,
)
import pandas as pd
from onboarding import get_jwt_token
from shared.api_client import get_paradex_config

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

paradex_http_url = "https://api.testnet.paradex.trade/v1"

async def _get(url: str, params, paradex_jwt: str):
    headers = {"Authorization": f"Bearer {paradex_jwt}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            status_code: int = response.status
            response: Dict = await response.json()
            if status_code == 200:
                logging.info(f"Success")
                logging.info("Get Trades successful")
                return response["results"], response["next"]
            else:
                # print(response)
                logging.error(f"Status Code: {status_code}")
                logging.error(f"Response Text: {response}")
    return dict(), None

async def get_trades(
    paradex_http_url: str,
    paradex_jwt: str,
) -> List[Dict]:
    headers = {"Authorization": f"Bearer {paradex_jwt}"}
    count=0
    base_url = paradex_http_url + '/trades'
    params={
    'market': 'ETH-USD-PERP'
    }
    logging.info(f"GET {base_url}")
    logging.info(f"Headers: {headers}")
    trades, next= await _get(url=base_url, params=params, paradex_jwt=paradex_jwt)
    print(type(trades))
    while next is not None:
        url=base_url+'/?cursor='+next
        TempTrades, next= await _get(url=url, params=params, paradex_jwt=paradex_jwt)
        trades.extend(TempTrades)   
    return trades


async def main(eth_private_key_hex: str) -> None:
    # Initialize Ethereum account
    _, eth_account = get_l1_eth_account(eth_private_key_hex)

    # Load Paradex config
    paradex_config = await get_paradex_config(paradex_http_url)

    # Generate Paradex account (only local)
    paradex_account_address, paradex_account_private_key_hex = generate_paradex_account(
        paradex_config, eth_account.key.hex()
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
    logging.info("Getting account's trades...")
    trades = await get_trades(paradex_http_url, paradex_jwt)
    print(type(trades))
    df=pd.DataFrame(trades)
    print(df)
    df.to_csv('Trades_Paradex.csv')

if __name__ == "__main__":
    # Logging
    logging.basicConfig(
        level=os.getenv("LOGGING_LEVEL", "INFO"),
        format="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Load environment variables
    eth_private_key_hex = os.getenv('ETH_PRIVATE_KEY_HEX', '')

    # Run main
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(eth_private_key_hex))
    except Exception as e:
        logging.error("Local Main Error")
        logging.error(e)
        traceback.print_exc()