from typing import List, AsyncGenerator, TYPE_CHECKING
from .base_candle import BaseCandle
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os

if TYPE_CHECKING:
    from core.base_strategy import BaseStrategy

load_dotenv()

UTC_OFFSET = int(os.getenv('UTC_TIMEZONE', 0))

class BaseSubscriber(ABC):
    """
    Update the strategy with a new candle.
    
    :param candle: The new candle data to update the strategy with.
    """    
    async def async_update(self, candle: BaseCandle) -> None:
        await asyncio.to_thread(self.update, candle)


    """Called when data stream finishes"""
    async def on_stream_end(self) -> None:
        pass

class BaseDataProvider(ABC):

    def __init__(self) -> None:
        self._subscribers: List["BaseSubscriber"] = []
    
    def subscribe(self, strategy: "BaseSubscriber") -> None:
        self._subscribers.append(strategy)
    
    def unsubscribe(self, strategy: "BaseSubscriber") -> None:
        self._subscribers.remove(strategy)
    
    async def notify(self, candle: BaseCandle) -> None:
        """Async notification - can handle async strategies"""
        tasks = []
        for subscriber in self._subscribers:
            try:
                tasks.append(subscriber.async_update(candle))
            except:
                pass
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    @abstractmethod
    async def stream_data(self) -> AsyncGenerator[BaseCandle, None]:
        """Stream data - works for both historical and live"""
        if False:
            yield  
    
    async def run(self) -> None:
        """Main execution loop"""
        async for candle in self.stream_data():
            await self.notify(candle)
        
        # Notify subscribers that stream ended
        for subscriber in self._subscribers:
            if hasattr(subscriber, "on_stream_end"):
                await subscriber.on_stream_end()

class CSVDataProvider(BaseDataProvider):
    def __init__(self, file_path: str, delay: float = 0.1) -> None:
        super().__init__()
        self.file_path = file_path
        self.delay = delay
    
    async def stream_data(self) -> AsyncGenerator[BaseCandle, None]:
        """Stream data from a CSV file"""
        import pandas as pd
        df = pd.read_csv(self.file_path)
        for index, row in df.iterrows():
            candle = BaseCandle(
                timestamp=datetime.strptime(row['open_time'], "%Y-%m-%d %H:%M:%S"),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['volume'])
            )
            yield candle
            if self.delay > 0:  
                await asyncio.sleep(self.delay)

class BinanceDataProvider(BaseDataProvider):
    def __init__(self, symbol: str, interval: str, key: str | None = '', secret: str | None= '') -> None:
        super().__init__()
        self.symbol = symbol
        self.interval = interval
        self.api_key = key
        self.api_secret = secret
    
    async def stream_data(self) -> AsyncGenerator[BaseCandle, None]:
        """Stream data from Binance API"""
        from binance import AsyncClient, BinanceSocketManager
        client = None
        try:
            # create async client (api keys optional for public streams)
            client = await AsyncClient.create(self.api_key, self.api_secret)
            bsm = BinanceSocketManager(client)
            # create a kline socket for the symbol/interval
            ks = bsm.kline_socket(symbol=self.symbol, interval=self.interval)
            async with ks as stream:
                # previous_candle = None
                while True:
                    msg = await stream.recv()
                    if msg is None:
                        # connection closed or heartbeat - break to recreate socket
                        break
                    # msg expected to contain 'k' (kline) per python-binance websocket format
                    k = msg.get("k") if isinstance(msg, dict) else None
                    if not k:
                        continue
                    tz = timezone(timedelta(hours=UTC_OFFSET))
                    ts_ms = int(k.get("t", 0))
                    ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone(tz)
                    candle = BaseCandle(
                        timestamp=ts,
                        open=float(k.get("o", 0.0)),
                        high=float(k.get("h", 0.0)),
                        low=float(k.get("l", 0.0)),
                        close=float(k.get("c", 0.0)),
                        volume=float(k.get("v", 0.0)),
                    )
                    # if previous_candle and previous_candle.timestamp == candle.timestamp:
                    #     continue
                    yield candle
                    # previous_candle = candle
        finally:
            if client is not None:
                try:
                    await client.close_connection()
                except Exception:
                    pass

