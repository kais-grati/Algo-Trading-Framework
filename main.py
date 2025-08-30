from data.data_provider import BaseDataProvider, CSVDataProvider, BinanceDataProvider
from core.base_strategy import BaseStrategy
from core.position_manager import BasePositionManager
import asyncio, os
from dotenv import load_dotenv
from data.base_candle import BaseCandle
from backtesting.misc import ChartType
from core.indicators import SMA, RSI

load_dotenv()

pm = BasePositionManager()


class Printer(BaseStrategy):
    def __init__(self, provider: BaseDataProvider):
        super().__init__(provider)
        self.indicator_manager.add_indicator(SMA(3))
        self.indicator_manager.add_indicator(RSI(3))

    def on_candle(self, candle: BaseCandle) -> None:
        print(self.indicator_manager.get_all_current_values())
        if candle.open == 10:
            self.position_manager.long(candle, value=100, tp=[(11, 0.5), (12, 0.5)], sl=[(9, 1)], fees=1)
        
            

provider = CSVDataProvider("test_data.csv", delay=3)
# provider = BinanceDataProvider('XRPUSDT', '1m', key=os.getenv('API_KEY'), secret=os.getenv('API_SECRET'))

strat = Printer(provider)

if __name__ == "__main__":
    strat.run(print_stats=False, plot_stats=True, chart_type=ChartType.CANDLESTICK)