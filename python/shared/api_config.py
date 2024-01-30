"""
Description:
    Paradex client. To be replaced by generated stubs
"""
import ipaddress
import os

from .paradex_api_utils import ApiConfigInterface


class ApiConfig(ApiConfigInterface):
    def __init__(self):
        self.paradex_jwt = ""
        self.load_config()

    def load_config(self):
        """
        Load the configuration from env.
        """

        # Paradex Connection URLs

        self.paradex_environment = os.getenv('PARADEX_ENVIRONMENT', 'TESTNET')

        def local_to_testnet(env: str) -> str:
            if env == 'local':
                return 'testnet'
            return env

        self.paradex_ws_url = (
            f'wss://ws.api.{local_to_testnet(self.paradex_environment.lower())}.paradex.trade/v1'
        )
        self.paradex_http_url = (
            f'https://api.{local_to_testnet(self.paradex_environment.lower())}.paradex.trade/v1'
        )

        # Hex of the account contract address
        self.paradex_account = os.getenv('PARADEX_ACCOUNT', "")

        # Hex of the account private key (Stark Key)
        self.paradex_account_private_key = os.getenv('PARADEX_ACCOUNT_PRIVATE_KEY', "")

        self.ethereum_hd_phrase = os.getenv('ETHEREUM_HD_PHRASE', "")
        self.ethereum_account = os.getenv('ETHEREUM_ACCOUNT', "")
        self.ethereum_private_key = os.getenv('ETHEREUM_PRIVATE_KEY', "")
        self.quote_refresh_lower_boundary = float(os.getenv('QUOTE_REFRESH_LOWER_BOUNDARY', "0"))
        # Maximum time between attempts to submit orders
        self.quote_refresh_higher_boundary = float(
            os.getenv('QUOTE_REFRESH_HIGHER_BOUNDARY', "0.1")
        )

        self.ws_recv_timeout = int(os.getenv('WS_RECV_TIMEOUT', "1"))
        self.ws_heartbeat_period = int(os.getenv('WS_HB_PERIOD', "3"))
        self.needs_onboarding = False
        self.paradex_config = dict()
        self.starknet_account = None
        self.pod_ip = os.getenv('POD_IP', '127.0.0.1')
        MAX_PODS = 15
        self.pod_index = int(ipaddress.IPv4Address(self.pod_ip)) % MAX_PODS
        return

    def __repr__(self):
        return str(vars(self))

    def to_dict(self) -> dict:
        config_dict = {}
        config_dict["paradex_environment"] = self.paradex_environment
        config_dict["paradex_ws_url"] = self.paradex_ws_url
        config_dict["paradex_http_url"] = self.paradex_http_url
        config_dict["paradex_account"] = self.paradex_account
        config_dict["paradex_account_private_key"] = self.paradex_account_private_key
        config_dict["ethereum_hd_phrase"] = self.ethereum_hd_phrase
        config_dict["ethereum_account"] = self.ethereum_account
        config_dict["ethereum_private_key"] = self.ethereum_private_key
        config_dict["quote_refresh_lower_boundary"] = self.quote_refresh_lower_boundary
        config_dict["quote_refresh_higher_boundary"] = self.quote_refresh_higher_boundary
        config_dict["ws_recv_timeout"] = self.ws_recv_timeout
        config_dict["ws_heartbeat_period"] = self.ws_heartbeat_period
        config_dict["needs_onboarding"] = self.needs_onboarding
        config_dict["pod_ip"] = self.pod_ip
        config_dict["pod_index"] = self.pod_index
        config_dict["paradex_config"] = self.paradex_config
        config_dict["starknet_account"] = self.starknet_account

        return config_dict
