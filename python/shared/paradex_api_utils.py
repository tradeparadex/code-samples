import math
import statistics
import time
from decimal import Decimal
from enum import Enum


def time_now_milli_secs() -> float:
    return time.time() * 1_000


def time_now_micro_secs() -> float:
    return time.time() * 1_000_000


class OrderType(Enum):
    Market = "MARKET"
    Limit = "LIMIT"


class OrderSide(Enum):
    Buy = "BUY"
    Sell = "SELL"

    def opposite_side(self):
        if self == OrderSide.Buy:
            return OrderSide.Sell
        else:
            return OrderSide.Buy

    def sign(self) -> int:
        if self == OrderSide.Buy:
            return 1
        else:
            return -1

    def chain_side(self) -> str:
        if self == OrderSide.Buy:
            return "1"
        else:
            return "2"


def quantity_side(amount: Decimal) -> OrderSide:
    if amount >= 0.0:
        return OrderSide.Buy
    else:
        return OrderSide.Sell


def price_more_aggressive(price1: Decimal, price2: Decimal, side: OrderSide) -> bool:
    if side == OrderSide.Buy:
        return price1 > price2
    else:
        return price1 < price2


def sign(a) -> int:
    if a > 0.000001:
        return 1
    elif a < -0.000001:
        return -1
    else:
        return 0


def time_millis() -> int:
    return int(time.time_ns() / 1_000_000)


class OrderStatus(Enum):
    NEW = "NEW"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


# rounding a price to the tick size
def round_to_tick(value, tick):
    return round(value / tick, 0) * tick


def round_to_tick_with_side(value, tick: Decimal, side: OrderSide) -> Decimal:
    if side == OrderSide.Buy:
        return math.floor(value / tick) * tick
    else:
        return math.ceil(value / tick) * tick


# capping price aggressiveness by most_aggressive_price
def cap_price(price: Decimal, most_aggressive_price: Decimal, side: OrderSide) -> Decimal:
    if side == OrderSide.Buy:
        if isinstance(most_aggressive_price, Decimal) and most_aggressive_price != Decimal('0'):
            return price.min(most_aggressive_price)
        else:
            return price
    else:
        if isinstance(most_aggressive_price, Decimal) and most_aggressive_price != Decimal('0'):
            return price.max(most_aggressive_price)
        else:
            return price


def add_price_offset(price: Decimal, offset: Decimal, side: OrderSide) -> Decimal:
    if not offset or price is None:
        return price
    else:
        return price + side.sign() * offset


def calc_price_offset(target_price: Decimal, price: Decimal, side: OrderSide) -> Decimal:
    """Calculates by how much price is more passive than target_price.
        Or how much to make price more aggressive to match target_price
    i.e. side = Buy , target_price = 100, price = 99, returns 1
    i.e. side = Buy , target_price = 100, price = 101, returns -1
         side = Sell, target_price = 100, price = 99, returns -1
    """
    return Decimal(side.sign() * (target_price - price))


class OrderAction(Enum):
    NAN = "NAN"
    Send = "SEND"
    SendCancel = "SEND_CANCEL"


class Order:
    def __init__(
        self,
        market,
        order_type: OrderType,
        order_side: OrderSide,
        size: Decimal,
        limit_price: Decimal = None,
        client_id: str = "",
        signature_timestamp = None,
        instruction: str = "GTC",
    ):
        ts = time_millis()
        self.id: str = ""
        self.account: str = ""
        self.status = OrderStatus.NEW
        self.limit_price = limit_price
        self.size = size
        self.market = market
        self.remaining = size
        self.order_type = order_type
        self.order_side = order_side
        self.client_id = client_id
        # created_at is in milliseconds
        self.created_at = ts
        self.cancel_reason = ""
        self.last_action = OrderAction.NAN
        self.last_action_time = 0
        self.cancel_attempts = 0
        self.signature = ""
        self.signature_timestamp = ts if signature_timestamp is None else signature_timestamp
        self.instruction = instruction

    def __repr__(self):
        ord_status = self.status.value
        if self.status == OrderStatus.CLOSED:
            ord_status += f"({self.cancel_reason})"
        msg = f'{self.market} {ord_status} {self.order_type.name} '
        msg += f'{self.order_side} {self.remaining}/{self.size}'
        msg += f'@{self.limit_price}' if self.order_type == OrderType.Limit else ''
        msg += f';{self.instruction}'
        msg += f';id={self.id}' if self.id else ''
        msg += f';client_id={self.client_id}' if self.client_id else ''
        msg += f';last_action:{self.last_action}' if self.last_action != OrderAction.NAN else ''
        msg += f';signed with:{self.signature}@{self.signature_timestamp}'
        return msg

    def __eq__(self, __o) -> bool:
        return self.id == __o.id

    def __hash__(self):
        return hash(self.id)

    def dump_to_dict(self) -> dict:
        order_dict = {
            "market": self.market,
            "side": self.order_side.value,
            "size": str(self.size),
            "type": self.order_type.value,
            "client_id": self.client_id,
            "signature": self.signature,
            "signature_timestamp": self.signature_timestamp,
            "instruction": self.instruction,
        }
        if self.order_type == OrderType.Limit:
            order_dict["price"] = str(self.limit_price)

        return order_dict

    def chain_price(self) -> str:
        if self.order_type == OrderType.Market:
            return "0"
        return str(int(self.limit_price.scaleb(8)))

    def chain_size(self) -> str:
        return str(int(self.size.scaleb(8)))


def calc_order_age_stats(orders: list) -> dict:
    age_stats = {}
    if orders:
        now = time_millis()
        age_stats['count'] = len(orders)
        age_stats['mean_age'] = sum([(now - o.created_at) / 1_000 for o in orders]) / len(orders)
        age_stats['median_age'] = statistics.median([(now - o.created_at) / 1_000 for o in orders])
        age_stats['max_age'] = max([(now - o.created_at) / 1_000 for o in orders])
        age_stats['buy_size'] = sum([o.remaining for o in orders if o.order_side == OrderSide.Buy])
        age_stats['sell_size'] = sum(
            [o.remaining for o in orders if o.order_side == OrderSide.Sell]
        )
    return age_stats


class WSSubscription(Enum):
    ACCOUNT_SUMMARY = 1
    BALANCES = 2
    FILLS = 3
    FUNDING_INDEX = 4
    MARKETS_SUMMARY = 5
    ORDERS = 6
    ORDER_BOOK = 7
    POSITIONS = 8
    TRADES = 9
    TRADEBUSTS = 10
    TRANSACTIONS = 11


class ApiConfigInterface:
    def __init__(self):
        self.load_config()

    def load_config(self):
        pass


class DatastoreInterface:
    def __init__(self, account: str):
        pass


class ParadexApiInterface:
    @classmethod
    async def create(cls, datastore: DatastoreInterface, config: dict, loop):
        pass

    def __init__(
        self,
        datastore: DatastoreInterface,
        config: dict,
        loop,
    ):
        pass

    def init_subscription_channels(self, markets: list):
        pass

    async def create_tasks(self, order_creator_cb):
        pass

    def refresh_state(self, market: str):
        pass

    def get_time_now_milli_secs(self) -> float:
        pass

    async def cancel_order_async(self, order: Order):
        pass

    async def submit_order_async(self, order: Order):
        pass
