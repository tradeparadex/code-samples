import asyncio
import logging
import os

from starknet_py.contract import Contract

from helpers.account import Account
from shared.api_client import get_paradex_config
from utils import (
    get_account,
    get_paradex_account_address,
    get_proxy_config,
    get_random_max_fee,
    hex_to_int,
)

paradex_http_url = "https://api.testnet.paradex.trade/v1"

# Transfer USDC from old Paradex account to new Paradex account
async def paraclear_transfer(
    config: dict, old_account: Account, new_account: Account, transfer_amount: float = None
):
    paraclear_address = config["paraclear_address"]
    paraclear_decimals = config["paraclear_decimals"]
    usdc_address = config["bridged_tokens"][0]["l2_token_address"]
    usdc_decimals = config["bridged_tokens"][0]["decimals"]

    paraclear_contract = await Contract.from_address(
        provider=old_account, address=paraclear_address, proxy_config=get_proxy_config()
    )
    paraclear_contract_new = await Contract.from_address(
        provider=new_account, address=paraclear_address, proxy_config=get_proxy_config()
    )
    usdc_contract = await Contract.from_address(
        provider=old_account, address=usdc_address, proxy_config=get_proxy_config()
    )

    # Set transfer amount to available balance if not specified
    if (transfer_amount is None):
        old_acc_token_asset_bal = await paraclear_contract.functions["getTokenAssetBalance"].call(
            account=old_account.address, token_address=hex_to_int(usdc_address)
        )
        available_balance_paraclear = old_acc_token_asset_bal.balance
        available_balance = available_balance_paraclear / 10**paraclear_decimals
        logging.info(f"USDC balance on paraclear: {available_balance} (old account)")
        transfer_amount = available_balance

    transfer_amount_paraclear = int(transfer_amount * 10**paraclear_decimals)
    transfer_amount_usdc = int(transfer_amount * 10**usdc_decimals)

    # Calls
    # 1. Withdraw available USDC from Paraclear (old account)
    # 2. Transfer USDC to new account (old account -> new account)
    calls = [
        paraclear_contract.functions["withdraw"].prepare_invoke_v1(
            token_address=hex_to_int(usdc_address),
            amount=transfer_amount_paraclear,
        ),
        usdc_contract.functions["transfer"].prepare_invoke_v1(
            recipient=new_account.address,
            amount=transfer_amount_usdc,
        ),
    ]
    transfer_info = await old_account.execute_v1(calls=calls, max_fee=get_random_max_fee())
    transfer_tx_hash = hex(transfer_info.transaction_hash)
    logging.info(f"Waiting for transfer to complete: {transfer_tx_hash}")
    tx_status = await old_account.client.wait_for_tx(tx_hash=transfer_tx_hash)
    logging.info(f"L2 transfer completed: {tx_status}")

    # 3. Increase USDC allowance for Paraclear (new account)
    # 4. Deposit USDC to Paraclear (new account)
    deposit_calls = [
        usdc_contract.functions["increaseAllowance"].prepare_invoke_v1(
            spender=hex_to_int(paraclear_address), addedValue=transfer_amount_usdc
        ),
        paraclear_contract_new.functions["deposit"].prepare_invoke_v1(
            token_address=hex_to_int(usdc_address),
            amount=transfer_amount_paraclear,
        )
    ]
    deposit_info = await new_account.execute_v1(calls=deposit_calls, max_fee=get_random_max_fee())
    deposit_tx_hash = hex(deposit_info.transaction_hash)
    logging.info(f"Waiting for deposit to complete: {deposit_tx_hash}")
    tx_status = await old_account.client.wait_for_tx(tx_hash=deposit_tx_hash)
    logging.info(f"L2 deposit completed: {tx_status}")

    # Check balance on USDC
    old_acc_usdc_bal = await usdc_contract.functions["balanceOf"].call(account=old_account.address)
    logging.info(f"USDC L2 balance is {old_acc_usdc_bal.balance / 10**usdc_decimals} (old account)")

    new_acc_usdc_bal = await usdc_contract.functions["balanceOf"].call(account=new_account.address)
    logging.info(f"USDC L2 balance is {new_acc_usdc_bal.balance / 10**usdc_decimals} (new account)")

    # Check balance on Paraclear
    old_acc_token_asset_bal = await paraclear_contract.functions["getTokenAssetBalance"].call(
        account=old_account.address, token_address=hex_to_int(usdc_address)
    )
    logging.info(
        f"USDC balance on paraclear: {old_acc_token_asset_bal.balance / 10**paraclear_decimals} (old account)"
    )
    new_acc_token_asset_bal = await paraclear_contract_new.functions["getTokenAssetBalance"].call(
        account=new_account.address, token_address=hex_to_int(usdc_address)
    )
    logging.info(
        f"USDC balance on paraclear: {new_acc_token_asset_bal.balance / 10**paraclear_decimals} (new account)"
    )


async def main(old_paradex_account_private_key_hex, new_paradex_account_private_key_hex) -> None:
    # Load Paradex config
    paradex_config = await get_paradex_config(paradex_http_url)

    # Get Paradex account addresses
    old_paradex_account_address = get_paradex_account_address(
        paradex_config, old_paradex_account_private_key_hex
    )
    new_paradex_account_address = get_paradex_account_address(
        paradex_config, new_paradex_account_private_key_hex
    )
    print(f"OLD Paradex Account Address: {old_paradex_account_address}")
    print(f"NEW Paradex Account Address: {new_paradex_account_address}")

    old_account = get_account(
        old_paradex_account_address, old_paradex_account_private_key_hex, paradex_config
    )
    new_account = get_account(
        new_paradex_account_address, new_paradex_account_private_key_hex, paradex_config
    )

    # Remove transfer amount to transfer all available balance
    await paraclear_transfer(paradex_config, old_account, new_account, transfer_amount=100.0)


if __name__ == "__main__":
    # Logging
    logging.basicConfig(
        level=os.getenv("LOGGING_LEVEL", "INFO"),
        format="%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Load environment variables
    old_paradex_account_private_key_hex = os.getenv("OLD_PARADEX_ACCOUNT_PRIVATE_KEY", "")
    new_paradex_account_private_key_hex = os.getenv("NEW_PARADEX_ACCOUNT_PRIVATE_KEY", "")
    asyncio.run(main(old_paradex_account_private_key_hex, new_paradex_account_private_key_hex))
