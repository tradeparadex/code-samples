import asyncio
import logging
import os
import time
import traceback
from decimal import Decimal
from shared.api_config import ApiConfig
from shared.paradex_api_utils import Order, OrderSide, OrderType
from shared.api_client import get_jwt_token, get_paradex_config, post_order_payload, sign_order

from utils import (
    generate_paradex_account,
    get_l1_eth_account,
)


def build_order(config: ApiConfig, order_type: OrderType, order_side: OrderSide, size: Decimal, market, client_id: str) -> Order:
    order = Order(
        market=market,
        order_type=order_type,
        order_side=order_side,
        size=size,
        client_id=client_id,
        signature_timestamp=int(time.time()),
    )
    sig = sign_order(config, order)
    order.signature = sig
    return order


async def main(config: ApiConfig) -> None:
    # Initialize Ethereum account
    _, eth_account = get_l1_eth_account(config.ethereum_private_key)

    config.paradex_account, config.paradex_account_private_key = generate_paradex_account(
        config.paradex_config, eth_account.key.hex()
    )

    # Get a JWT token to interact with private endpoints
    logging.info("Getting JWT...")
    paradex_jwt = await get_jwt_token(
        config.paradex_config,
        config.paradex_http_url,
        config.paradex_account,
        config.paradex_account_private_key,
    )

    # POST order
    order = build_order(config, OrderType.Market, OrderSide.Buy, Decimal("0.1"), "ETH-USD-PERP", "mock")
    await post_order_payload(config.paradex_http_url, paradex_jwt, order.dump_to_dict())

if __name__ == "__main__":
    # Logging
    logging.basicConfig(
        level=os.getenv("LOGGING_LEVEL", "INFO"),
        format="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Load environment variables
    config = ApiConfig()
    config.paradex_http_url = "https://api.testnet.paradex.trade/v1"
    # Requires
    ###
    # WEB3_INFURA_PROJECT_ID
    # ETHEREUM_PRIVATE_KEY
    ###

    # Run main
    try:
        loop = asyncio.get_event_loop()
        # Load paradex config
        config.paradex_config = loop.run_until_complete(get_paradex_config(config.paradex_http_url))
        loop.run_until_complete(main(config))
    except Exception as e:
        logging.error("Local Main Error")
        logging.error(e)
        traceback.print_exc()
