import asyncio
import logging
import os
import traceback

from paradex_py import Paradex
from paradex_py.environment import TESTNET


async def main(eth_address: str, eth_private_key: str) -> None:
    paradex = Paradex(env=TESTNET, l1_address=eth_address, l1_private_key=eth_private_key)

    logging.info("Getting account's trades...")
    trades = paradex.api_client.fetch_trades({"market": "ETH-USD-PERP", "page_size": 5})
    print(trades)


if __name__ == "__main__":
    # Logging
    logging.basicConfig(
        level=os.getenv("LOGGING_LEVEL", "INFO"),
        format="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Load environment variables
    eth_address = os.getenv("ETHEREUM_ADDRESS", "")
    eth_private_key = os.getenv("ETHEREUM_PRIVATE_KEY", "")

    # Run main
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(eth_address, eth_private_key))
    except Exception as e:
        logging.error("Local Main Error")
        logging.error(e)
        traceback.print_exc()
