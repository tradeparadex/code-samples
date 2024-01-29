import asyncio
import timeit
import os

from decimal import Decimal

from shared.api_client import generate_accounts, get_paradex_config, sign_order
from shared.api_config import ApiConfig
from shared.paradex_api_utils import Order, OrderSide, OrderType

number = 100
rep = 7

mock_order = Order(
    market='ETH-USD-PERP',
    order_type=OrderType.Market,
    order_side=OrderSide.Buy,
    size=Decimal("0.1"),
    client_id="mock",
)
os.environ["PARADEX_ENVIRONMENT"] = "local"

config = ApiConfig()
config.paradex_http_url = "https://api.testnet.paradex.trade/v1"

loop = asyncio.get_event_loop()
config.paradex_config = loop.run_until_complete(get_paradex_config(config.paradex_http_url))
generate_accounts(config)

t1 = timeit.repeat(lambda: sign_order(config, mock_order), number=number, repeat=rep)

print(
    f"order sign:\n\tbest time:\t{1000*min(t1)/number:.0f}ms\n\tbest per sec:\t{number/min(t1):.0f}\n\tavg per sec:\t{(number*rep)/sum(t1):.0f}"
)
