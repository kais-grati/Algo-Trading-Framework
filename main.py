from data.data_provider import BaseDataProvider, CSVDataProvider, BinanceDataProvider
from core.base_strategy import BaseStrategy
from core.position_manager import BasePositionManager
import asyncio, os
from dotenv import load_dotenv
from data.base_candle import BaseCandle
from backtesting.misc import ChartType
from core.indicators import SMA, VWAP, EMA, RSI

load_dotenv()


class TestStrategy(BaseStrategy):
    def __init__(self, provider: BaseDataProvider):
        super().__init__(provider)
        self.indicator_manager.add_indicator(EMA(28), color="#5900FF")
        self.indicator_manager.add_indicator(EMA(14), color="#FF004C")
        self.indicator_manager.add_indicator(VWAP(), color="#FFEE00")
        self.indicator_manager.add_indicator(RSI(), separate_chart=True)

        self.bool = True
        self.bool2 = True
        self.bool3 = True


    def on_candle(self, candle: BaseCandle) -> None:
        if self.bool:
            if candle.close >= 0.5667:
                self.bool = False
                self.position_manager.long(candle, qty=10, tp=[(0.58,1.0)], sl=[(0.0,1.0)])
        if self.bool2:
            if candle.close >= 0.585:
                self.bool2 = False
                self.position_manager.long(candle, qty=10, tp=[(0.59,1.0)], sl=[(0.0,1.0)])
        if self.bool3:
            if candle.close >= 0.59:
                self.bool3 = False
                self.position_manager.long(candle, qty=10, tp=[(0.61,1.0)], sl=[(0.0,1.0)])
        
            

provider = CSVDataProvider("xrp_5m_last_year.csv", delay=0.1)
# provider = BinanceDataProvider('XRPUSDT', '1s', key=os.getenv('API_KEY'), secret=os.getenv('API_SECRET'))

strat = TestStrategy(provider)

if __name__ == "__main__":
    strat.run(print_stats=True, plot_stats=True, chart_type=ChartType.CANDLESTICK, show_n_candles=1000)