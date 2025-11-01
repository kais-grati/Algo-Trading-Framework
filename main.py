from data.data_provider import BaseDataProvider, CSVDataProvider, BinanceDataProvider
from core.base_strategy import BaseStrategy
from core.position_manager import BasePositionManager
import asyncio, os
from dotenv import load_dotenv
from data.base_candle import BaseCandle
from backtesting.misc import ChartType
from core.indicators import SMA, VWAP, EMA, RSI
import time

load_dotenv()


class TestStrategy(BaseStrategy):
    def __init__(self, provider: BaseDataProvider):
        super().__init__(provider)
        self.indicator_manager.add_indicator(EMA(20), color="#5900FF", alias="Slow EMA")
        self.indicator_manager.add_indicator(EMA(5), color="#FF004C", alias="Fast EMA")
        self.count = 0
        self.cooldown = 10


    def on_candle(self, candle: BaseCandle) -> None:
        slow = self.indicator_manager.get_value("Slow EMA").value
        fast = self.indicator_manager.get_value("Fast EMA").value

        # Wait until both EMAs have valid values
        if slow is None or fast is None:
            return

        # Detect crossover
        if fast > slow and not self.position_manager.is_long and self.count > self.cooldown:
            self.position_manager.close(candle=candle, percentage=1)
            self.position_manager.long(candle=candle, value=1000, sl=[(0.9 * candle.close, 1)], tp=[(1.2 * candle.close, 1)])
            self.count = 0
        elif fast < slow and not self.position_manager.is_short and self.count > self.cooldown:
            self.position_manager.close(candle=candle, percentage=1)
            self.position_manager.short(candle=candle, value=1000, sl=[(1.1 * candle.close, 1)], tp=[(0.8 * candle.close, 1)])
            self.count = 0

        self.count += 1

        
            

provider = CSVDataProvider("xrp_5m_last_year.csv", delay=0.1)
# provider = BinanceDataProvider('XRPUSDT', '1s', key=os.getenv('API_KEY'), secret=os.getenv('API_SECRET'))

strat = TestStrategy(provider)

if __name__ == "__main__":
    strat.run(print_stats=False, plot_stats=True, chart_type=ChartType.CANDLESTICK, show_n_candles=500)