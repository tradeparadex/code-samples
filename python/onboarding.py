import asyncio
import os
from paradex_py import Paradex
from paradex_py.environment import TESTNET

async def main(eth_address: str, eth_private_key: str) -> None:
    paradex = Paradex(env=TESTNET, l1_address=eth_address, l1_private_key=eth_private_key)

    print(f"Paradex Account Address: {paradex.account.l2_address}")
    print(f"Paradex Account Public Key: {paradex.account.l2_public_key}")
    print(f"Paradex Account Private Key: {paradex.account.l2_private_key}")

    print(f"Paradex Account JWT Token: {paradex.account.jwt_token}")


if __name__ == "__main__":
    # Load environment variables
    eth_address = os.getenv("ETHEREUM_ADDRESS", "")
    eth_private_key = os.getenv("ETHEREUM_PRIVATE_KEY", "")

    asyncio.run(main(eth_address, eth_private_key))
