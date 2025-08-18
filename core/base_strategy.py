from abc import abstractmethod
from data import BaseCandle
from typing import TYPE_CHECKING
from data import BaseDataProvider

class BaseStrategy():
    def __init__(self, data_provider: BaseDataProvider) -> None:
        """
        Initialize the BaseStrategy with a data provider.
        
        :param data_provider: The DataProvider instance to subscribe to.
        """
        self.data_provider = data_provider
        self.data_provider.subscribe(self)
    
    @abstractmethod
    def async_update(self, candle: BaseCandle) -> None:
        """
        Update the strategy with a new candle.
        
        :param candle: The new candle data to update the strategy with.
        """
        raise NotImplementedError("This strategy does not support asynchronous updates.")

    def update(self, candle: BaseCandle) -> None:
        """
        Synchronous update method for strategies that do not require async handling.
        
        :param candle: The new candle data to update the strategy with.
        """
        raise NotImplementedError("This strategy does not support synchronous updates.")