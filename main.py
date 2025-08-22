from data.data_provider import BaseDataProvider, CSVDataProvider, BinanceDataProvider
from core.base_strategy import BaseStrategy
from core.position_manager import BasePositionManager
import asyncio, os
from dotenv import load_dotenv
from data.base_candle import BaseCandle

load_dotenv()

pm = BasePositionManager()


class Printer(BaseStrategy):
    signal = 1
    def on_candle(self, candle: BaseCandle) -> None:
        print(candle)
        if candle.open == 10:
            self.position_manager.long(candle, 100, tp=[(11, 50), (12, 50)], sl=[(9, 100)], fees=1)
        
            

provider = CSVDataProvider("test_data.csv", delay=1)
# provider = BinanceDataProvider('XRPUSDT', '1m', key=os.getenv('API_KEY'), secret=os.getenv('API_SECRET'))

strat = Printer(provider)

if __name__ == "__main__":
    asyncio.run(strat.run())
    print(strat.backtester)