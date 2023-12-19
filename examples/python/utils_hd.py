from typing import Dict, Tuple

from eth_account.messages import encode_typed_data, SignableMessage
from ledgereth.accounts import find_account
from ledgereth.comms import init_dongle
from ledgereth.messages import sign_typed_data_draft
from starknet_py.net.signer.stark_curve_signer import KeyPair

from utils import (
    build_stark_key_message,
    get_acc_contract_address_and_call_data,
    get_private_key_from_eth_signature
)


def sign_stark_key_message_ledger(message: SignableMessage, eth_account_address: str) -> str:
    dongle = init_dongle()
    account = find_account(eth_account_address, dongle, count=10)
    if account is None:
        raise Exception(f"Account {eth_account_address} not found on Ledger")
    # header/body is eth_account naming, presumably to be generic
    domain_hash = message.header
    message_hash = message.body
    signed = sign_typed_data_draft(
        domain_hash=domain_hash,
        message_hash=message_hash,
        sender_path=account.path,
        dongle=dongle,
    )
    return signed.signature


def derive_stark_key_from_ledger(message: str, eth_account_address: str) -> int:
    signable_message = encode_typed_data(full_message=message)
    message_signature = sign_stark_key_message_ledger(signable_message, eth_account_address)
    private_key = get_private_key_from_eth_signature(message_signature)
    return private_key


def generate_paradex_account_from_ledger(
    paradex_config: Dict, eth_account_address: str
) -> Tuple[str, str]:
    eth_chain_id = int(paradex_config['l1_chain_id'])
    stark_key_msg = build_stark_key_message(eth_chain_id)
    paradex_private_key = derive_stark_key_from_ledger(stark_key_msg, eth_account_address)
    paradex_key_pair = KeyPair.from_private_key(paradex_private_key)
    paradex_account_private_key_hex = hex(paradex_private_key)
    paradex_account_address = get_acc_contract_address_and_call_data(
        paradex_config['paraclear_account_proxy_hash'],
        paradex_config['paraclear_account_hash'],
        hex(paradex_key_pair.public_key),
    )
    return paradex_account_address, paradex_account_private_key_hex
