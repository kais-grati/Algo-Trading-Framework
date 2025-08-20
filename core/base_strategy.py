from abc import abstractmethod
from data import BaseCandle
from typing import TYPE_CHECKING
from data import BaseDataProvider
from data.data_provider import BaseSubscriber
from backtesting.backtester import BaseBacktester
from position_manager import BasePositionManager

class BaseStrategy(BaseSubscriber):
    def __init__(self, dataprovider) -> None:
        """
        Initialize the BaseStrategy with a data provider.
        
        :param data_provider: The DataProvider instance to subscribe to.
        """
        self.dataprovider = dataprovider
        self.position_manager = BasePositionManager()
        self.backtester = BaseBacktester(dataprovider, self.position_manager)
        dataprovider.subscribe(self)
    
    def update(self, candle: BaseCandle) -> None:
        """
        Update the strategy and backtest stats with a new candle.
        
        :param candle: The new candle data to update the strategy with.
        """
        self.backtester.update(candle)
        
