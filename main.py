from data.data_provider import BaseDataProvider, CSVDataProvider, BinanceDataProvider
from core.base_strategy import BaseStrategy
from core.position_manager import BasePositionManager
import asyncio, os
from dotenv import load_dotenv
from data.base_candle import BaseCandle
from backtesting.misc import ChartType
from core.indicators import SMA, VWAP, EMA, MACD

load_dotenv()

pm = BasePositionManager()


class Printer(BaseStrategy):
    def __init__(self, provider: BaseDataProvider):
        super().__init__(provider)
        self.indicator_manager.add_indicator(SMA(14), color="#5900FF")
        self.indicator_manager.add_indicator(EMA(14), color="#FF004C")
        self.indicator_manager.add_indicator(VWAP(), color="#FFEE00")

        # self.indicator_manager.add_indicator(MACD(), color="#00FFA3", separate_chart=True)

    def on_candle(self, candle: BaseCandle) -> None:
        if candle.open == 10:
            self.position_manager.long(candle, value=100, tp=[(11, 0.5), (12, 0.5)], sl=[(9, 1)], fees=1)
        
            

# provider = CSVDataProvider("xrp_5m_last_year.csv", delay=0.1)
provider = BinanceDataProvider('XRPUSDT', '1s', key=os.getenv('API_KEY'), secret=os.getenv('API_SECRET'))

strat = Printer(provider)

if __name__ == "__main__":
    strat.run(print_stats=False, plot_stats=True, chart_type=ChartType.CANDLESTICK, show_n_candles=1000)