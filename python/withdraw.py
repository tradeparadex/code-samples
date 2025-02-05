# built ins
import asyncio
import json
import logging
import os
import traceback
from hexbytes import HexBytes
from typing import Dict, Tuple

from web3.auto import Web3

from starknet_py.contract import Contract
from starknet_py.net.client import Client

from helpers.account import Account
from shared.api_client import get_paradex_config
from utils import (
    generate_paradex_account,
    get_account,
    get_l1_eth_account,
    get_proxy_config,
    get_random_max_fee,
    hex_to_int,
    wait_for_tx,
)

paradex_http_url = "https://api.testnet.paradex.trade/v1"
l2_bridge_version = 2

async def withdraw_from_paraclear(
    l1_recipient: str, amount: int, config: Dict, account: Account
) -> Tuple[Client, str]:
    logging.info("Withdraw from Paraclear to L2 token bridge contract")

    paraclear_address = config["paraclear_address"]
    paraclear_decimals = config["paraclear_decimals"]
    usdc_address = config["bridged_tokens"][0]["l2_token_address"]
    l2_bridge_address = config["bridged_tokens"][0]["l2_bridge_address"]
    usdc_decimals = config["bridged_tokens"][0]["decimals"]

    paraclear_contract = await Contract.from_address(
        provider=account, address=paraclear_address, proxy_config=True
    )
    logging.info(f"Paraclear Contract: {hex(paraclear_contract.address)}")

    l2_bridge_contract = await Contract.from_address(
        provider=account, address=l2_bridge_address, proxy_config=get_proxy_config()
    )
    logging.info(f"USDC Bridge Contract: {hex(l2_bridge_contract.address)}")

    token_asset_bal = await paraclear_contract.functions["getTokenAssetBalance"].call(
        account=account.address, token_address=hex_to_int(usdc_address)
    )
    logging.info(
        f"USDC balance on Paraclear: {token_asset_bal[0] / 10**paraclear_decimals}"
    )

    l1_recipient_arg = hex_to_int(l1_recipient)
    l1_recipient_arg = (
        {"address": l1_recipient_arg} if l2_bridge_version == 2 else l1_recipient_arg
    )
    calls = [
        paraclear_contract.functions["withdraw"].prepare_invoke_v1(
            token_address=hex_to_int(usdc_address),
            amount=amount * 10**paraclear_decimals,
        ),
        l2_bridge_contract.functions["initiate_withdraw"].prepare_invoke_v1(
            l1_recipient=l1_recipient_arg,
            amount=amount * 10**usdc_decimals,
        ),
    ]
    withdraw_info = await account.execute_v1(calls=calls, max_fee=get_random_max_fee())
    withdraw_tx_hash = hex(withdraw_info.transaction_hash)
    logging.info(f"Waiting for withdraw to complete: {withdraw_tx_hash}")
    tx_status = await account.client.wait_for_tx(
        tx_hash=withdraw_info.transaction_hash,
    )
    logging.info(f"L2 withdraw completed: {tx_status}")

    # Check balance
    usdc_contract = await Contract.from_address(
        provider=account, address=usdc_address, proxy_config=get_proxy_config()
    )
    usdc_bal = await usdc_contract.functions["balanceOf"].call(account=account.address)
    logging.info(f"USDC L2 balance is {usdc_bal[0] / 10**usdc_decimals}")

    return account.client, withdraw_tx_hash


async def withdraw_from_l1_bridge(
    l1_recipient: str, amount: int, config: Dict, w3: Web3
) -> None:
    logging.info("Withdraw from L1 token bridge contract to L1 recipient")

    l1_bridge_address = config["bridged_tokens"][0]["l1_bridge_address"]
    l1_bridge_abi = json.load(open(os.path.abspath("./abis/l1_bridge_abi.json")))
    usdc_decimals = config["bridged_tokens"][0]["decimals"]

    l1_contract = w3.eth.contract(address=l1_bridge_address, abi=l1_bridge_abi)

    nonce = w3.eth.get_transaction_count(l1_recipient, "pending")
    tx = {
        "maxFeePerGas": w3.toWei("2", "gwei"),
        "maxPriorityFeePerGas": w3.toWei("1", "gwei"),
        "nonce": nonce,
        "type": 2,
    }
    withdraw_tx = l1_contract.functions.withdraw(
        amount * 10**usdc_decimals, l1_recipient
    ).build_transaction(tx)
    tx_hash = w3.eth.send_transaction(withdraw_tx)
    logging.info(f"L1 withdraw tx hash: { HexBytes(tx_hash).hex()}")


# Primary Coroutine
async def main(eth_private_key_hex: str) -> None:
    w3, eth_account = get_l1_eth_account(eth_private_key_hex)

    # Load Paradex config
    paradex_config = await get_paradex_config(paradex_http_url)

    # Generate Paradex account (only local)
    paradex_account_address, paradex_account_private_key_hex = generate_paradex_account(
        paradex_config, eth_account.key.hex()
    )

    # Starknet account
    account = get_account(
        paradex_account_address, paradex_account_private_key_hex, paradex_config
    )

    amount = 1  # 1 USDC

    # This method only waits for `ACCEPTED_ON_L2` status
    # Status change to `ACCEPTED_ON_L1` could take up to 12 hours
    client, withdraw_tx_hash = await withdraw_from_paraclear(
        eth_account.address, amount, paradex_config, account
    )

    # Poll for `ACCEPTED_ON_L1` status
    logging.info(f"Poll L2 withdraw tx: {withdraw_tx_hash}")
    await wait_for_tx(client=client, tx_hash=withdraw_tx_hash)

    # After withdraw tx is `ACCEPTED_ON_L1`, trigger the withdrawal from L1 bridge
    await withdraw_from_l1_bridge(eth_account.address, amount, paradex_config, w3)


if __name__ == "__main__":
    # Logging
    logging.basicConfig(
        level=os.getenv("LOGGING_LEVEL", "INFO"),
        format="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Load environment variables
    eth_private_key_hex = os.getenv("ETHEREUM_PRIVATE_KEY", "")

    # Run main
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(eth_private_key_hex))
    except Exception as e:
        logging.error("Local Main Error")
        logging.error(e)
        traceback.print_exc()
