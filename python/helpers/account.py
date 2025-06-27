import time

from typing import List, Optional

from poseidon_py.poseidon_hash import poseidon_hash_many
from starknet_py.net.account.account import Account as StarknetAccount
from starknet_py.net.client import Client
from starknet_py.net.models import AddressRepresentation, StarknetChainId
from starknet_py.net.signer import BaseSigner
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.serialization.data_serializers.byte_array_serializer import ByteArraySerializer
from starknet_py.utils.typed_data import TypedData as TypedDataDataclass


from .typed_data import TypedData
from .utils import message_signature

FULLNODE_SIGNATURE_VERSION = "1.0.0"

def poseidon_hash(input_str: str) -> int:
    byte_array_serializer = ByteArraySerializer()
    input_felts = byte_array_serializer.serialize(input_str)
    return poseidon_hash_many(input_felts)


class Account(StarknetAccount):
    def __init__(
        self,
        *,
        address: AddressRepresentation,
        client: Client,
        signer: Optional[BaseSigner] = None,
        key_pair: Optional[KeyPair] = None,
        chain: Optional[StarknetChainId] = None,
    ):
        super().__init__(
            address=address, client=client, signer=signer, key_pair=key_pair, chain=chain
        )

    def sign_message(self, typed_data: TypedData) -> List[int]:
        typed_data_dataclass = TypedDataDataclass.from_dict(typed_data)
        msg_hash = typed_data_dataclass.message_hash(self.address)
        r, s = message_signature(msg_hash=msg_hash, priv_key=self.signer.key_pair.private_key)
        return [r, s]

    def fullnode_request_headers(self, chain_id: int, json_payload: str):
        signature_timestamp = int(time.time())
        account_address = hex(self.address)
        message = self.build_fullnode_message(
            chain_id,
            account_address,
            json_payload,
            signature_timestamp,
            FULLNODE_SIGNATURE_VERSION,
        )
        sig = super().sign_message(message)
        return {
            "Content-Type": "application/json",
            "PARADEX-STARKNET-ACCOUNT": account_address,
            "PARADEX-STARKNET-SIGNATURE": f'["{sig[0]}","{sig[1]}"]',
            "PARADEX-STARKNET-SIGNATURE-TIMESTAMP": str(signature_timestamp),
            "PARADEX-STARKNET-SIGNATURE-VERSION": FULLNODE_SIGNATURE_VERSION,
        }

    def build_fullnode_message(
        self, chainId: int, account: str, json_payload: str, timestamp: int, version: str
    ) -> TypedData:
        payload_hash = poseidon_hash(json_payload)
        message = {
            "message": {
                "account": account,
                "payload": payload_hash,
                "timestamp": timestamp,
                "version": version,
            },
            "domain": {"name": "Paradex", "chainId": hex(chainId), "version": "1"},
            "primaryType": "Request",
            "types": {
                "StarkNetDomain": [
                    {"name": "name", "type": "felt"},
                    {"name": "chainId", "type": "felt"},
                    {"name": "version", "type": "felt"},
                ],
                "Request": [
                    {"name": "account", "type": "felt"},
                    {"name": "payload", "type": "felt"},
                    {"name": "timestamp", "type": "felt"},
                    {"name": "version", "type": "felt"},
                ],
            },
        }
        return message
