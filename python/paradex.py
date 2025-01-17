import asyncio
import logging
from typing import Dict, List, Optional, Callable
from decimal import Decimal
import aiohttp
from shared.paradex_api_utils import Order, OrderSide, OrderType
from shared.api_client import get_jwt_token, get_paradex_config, post_order_payload, sign_order
from shared.api_config import ApiConfig
from utils import get_account
import os
import time
from dotenv import load_dotenv
from rich import print
import json
import websockets

class Paradex:
    def __init__(
        self,
        account_address: str,
        private_key: str,
        http_url: str = "https://api.testnet.paradex.trade/v1",
        ws_url: str = "wss://ws.api.testnet.paradex.trade/v1"
    ):
        """
        Initialize Paradex client
        
        Args:
            account_address: Paradexアカウントのアドレス
            private_key: Paradexアカウントの秘密鍵
            http_url: ParadexのAPIエンドポイント
        """
        self.account_address = account_address
        self.private_key = private_key
        self.http_url = http_url
        self.ws_url = ws_url
        self.jwt_token: Optional[str] = None
        self.paradex_config: Optional[Dict] = None
        self.account = None
    
    async def initialize(self):
        """Initialize the client by loading config and getting JWT token"""
        self.paradex_config = await get_paradex_config(self.http_url)
        self.api_config = ApiConfig()
        self.api_config.paradex_http_url = self.http_url
        self.api_config.paradex_account = self.account_address
        self.api_config.paradex_account_private_key = self.private_key
        self.api_config.paradex_config = self.paradex_config

        self.account = get_account(
            self.account_address,
            self.private_key,
            self.paradex_config
        )
        await self.refresh_jwt()
    
    async def refresh_jwt(self):
        """Get new JWT token"""
        self.jwt_token = await get_jwt_token(
            self.paradex_config,
            self.http_url,
            self.account_address,
            self.private_key
        )
    
    def _get_headers(self) -> Dict:
        """Get headers with JWT token"""
        if not self.jwt_token:
            raise ValueError("JWT token not initialized. Call initialize() first")
        return {"Authorization": f"Bearer {self.jwt_token}"}
    
    async def create_order(
        self,
        order_type: OrderType,
        order_side: OrderSide,
        size: Decimal,
        market: str,
        client_id: str
    ) -> Dict:
        """
        Create a new order
        
        Args:
            order_type: Market or Limit
            order_side: Buy or Sell
            size: order size
            market: market symbol (e.g. "ETH-USD-PERP")
            client_id: unique order identifier
        """
        from post_order import build_order
        order = Order(
            market=market,
            order_type=order_type,
            order_side=order_side,
            size=size,
            client_id=client_id,
            signature_timestamp=int(time.time()*1000),
        )
        sig = sign_order(self.api_config, order)
        order.signature = sig
        
        response = await post_order_payload(
            self.http_url,
            self.jwt_token,
            order.dump_to_dict()
        )
        return response
    
    
    async def get_open_orders(self) -> List[Dict]:
        """Get open orders"""
        url = f"{self.http_url}/orders"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["results"]
                else:
                    logging.error(f"Error {response.status}: {await response.text()}")
                    return []

    async def subscribe_orderbook(self, symbol: str, callback: Callable[[Dict], None]):
        """
        板情報のWebSocketストリームを購読
        
        Args:
            symbol: 通貨ペアのシンボル（例：'ETH'）
            callback: 板情報を受け取るコールバック関数
        """
        TICK_SIZE_MAP = {
            "BTC": "0_1",
            "ETH": "0_01",
            "SOL": "0_001",
        }
        tick_size = TICK_SIZE_MAP[symbol]
        subscribe_message = {
            "jsonrpc": "2.0",
            "method": "subscribe",
            "params": {
                "channel": f"order_book.{symbol}-USD-PERP.snapshot@15@50ms@{tick_size}"
            },
            "id": 1
        }       

        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:

                    await websocket.send(json.dumps(subscribe_message))
                    logging.info(f"接続完了: {symbol}の板情報の購読を開始")
                    
                    while True:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)
                            if ('method' in data and data['method'] == 'subscription' and 
                                'params' in data and 'data' in data['params']):
                                callback(data['params']['data'])
                        except json.JSONDecodeError as e:
                            logging.error(f"JSONデコードエラー: {e}")
                            continue
                            
            except websockets.exceptions.ConnectionClosed:
                logging.warning("WebSocket接続が切断されました。再接続します...")
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"エラーが発生しました: {e}")
                await asyncio.sleep(5)


async def main():
    load_dotenv("secrets/.env")
    
    # Initialize Paradex client
    client = Paradex(
        account_address=os.getenv("PARADEX_ACCOUNT_ADDRESS"),
        private_key=os.getenv("PARADEX_ACCOUNT_PBKEY")
    )
    await client.initialize()


    def handle_orderbook(data: Dict):
        print(f"orderbook: {data}")
    
    await client.subscribe_orderbook("ETH", handle_orderbook)

    # # Create market buy order
    # order = await client.create_order(
    #     order_type=OrderType.Market,
    #     order_side=OrderSide.Buy,
    #     size=Decimal("0.1"),
    #     market="ETH-USD-PERP",
    #     client_id="test_order_1"
    # )

    # print(f"order: {order}")
    
    # # Get open orders
    # open_orders = await client.get_open_orders()
    # print(open_orders)

if __name__ == "__main__":
    asyncio.run(main())