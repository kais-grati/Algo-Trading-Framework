from abc import abstractmethod
from data import BaseCandle
from typing import TYPE_CHECKING
from data import BaseDataProvider
from data.data_provider import BaseSubscriber
from backtesting.backtester import BaseBacktester
from core.position_manager import BasePositionManager

class BaseStrategy(BaseSubscriber):
    def __init__(self, dataprovider: BaseDataProvider, enable_backtesting: bool = True) -> None:
        """
        Initialize the BaseStrategy with a data provider.
        
        :param data_provider: The DataProvider instance to subscribe to.
        """
        self.dataprovider = dataprovider
        self.position_manager = BasePositionManager()
        self.backtester = BaseBacktester(self.position_manager) if enable_backtesting else None
        dataprovider.subscribe(self)
    
    def update(self, candle: BaseCandle) -> None:
        """
        Update the strategy and backtest stats with a new candle.
        
        :param candle: The new candle data to update the strategy with.
        """
        self.on_candle(candle)

        if self.backtester:
            self.backtester.update(candle)

    
    @abstractmethod
    def on_candle(self, candle: BaseCandle) -> None:
        """
        Strategy-specific logic to be implemented by subclasses.
        This is where you implement your trading signals and position management.
        
        :param candle: The new candle data
        """
        pass

    async def on_stream_end(self) -> None:
        """
        Called when the data stream ends.
        This can be used to finalize any open positions or perform end-of-stream logic.
        """
        pass

    async def run(self) -> None:
        """Start the data provider to begin receiving candle updates."""
        await self.dataprovider.run() 