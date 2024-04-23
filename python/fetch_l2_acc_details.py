import asyncio
import logging
import os
from typing import Dict, List
from shared.api_client import get_paradex_config
from utils import (
    generate_paradex_account,
    get_l1_eth_account,
)

paradex_http_url = "https://api.testnet.paradex.trade/v1"
async def main(eth_private_key_hex: str) -> None:
    # Initialize Ethereum account
    _, eth_account = get_l1_eth_account(eth_private_key_hex)

    # Load Paradex config
    paradex_config = await get_paradex_config(paradex_http_url)

    # Generate Paradex account (only local)
    paradex_account_address, paradex_account_private_key_hex = generate_paradex_account(
        paradex_config, eth_account.key.hex()
    )
    print(f"Paradex Account Address: {paradex_account_address}")
    print(f"Paradex Account Private Key: {paradex_account_private_key_hex}")


if __name__ == "__main__":
    # Logging
    logging.basicConfig(
        level=os.getenv("LOGGING_LEVEL", "INFO"),
        format="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Load environment variables
    eth_private_key_hex = os.getenv('ETHEREUM_PRIVATE_KEY', "")
    asyncio.run(main(eth_private_key_hex))
