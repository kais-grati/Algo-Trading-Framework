from abc import abstractmethod
from data import BaseCandle
from typing import TYPE_CHECKING
from data import BaseDataProvider
from data.data_provider import BaseSubscriber
from backtesting.backtester import BaseBacktester
from backtesting.plotter import EquityPlotter
from core.position_manager import BasePositionManager
import asyncio, os, threading, time

class BaseStrategy(BaseSubscriber):
    def __init__(self, dataprovider: BaseDataProvider) -> None:
        """
        Initialize the BaseStrategy with a data provider.
        
        :param data_provider: The DataProvider instance to subscribe to.
        """
        self.dataprovider = dataprovider
        self.position_manager = BasePositionManager()
        self.backtester = BaseBacktester(self.position_manager)
        dataprovider.subscribe(self)
        self.stop_event = threading.Event()
    
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
        self.stop_event.set()
        
        if hasattr(self, 'plotter'):
            for i in range(10): 
                if not self.plotter.is_alive():
                    break
                await asyncio.sleep(0.1)

    def _start_print_thread(self):
        def print_loop():
            while not self.stop_event.is_set(): 
                if os.name == 'nt':
                    os.system('cls')
                else:
                    os.system('clear')
                print(self.backtester)
                time.sleep(1)  

        thread = threading.Thread(target=print_loop, daemon=True)
        thread.start()

    def _start_stats_plotting(self):
        self.plotter = EquityPlotter(
            backtester=self.backtester,
            stop_event=self.stop_event
        )
        self.plotter.start()

    def run(self, print_stats: bool = True, plot_stats: bool = False) -> None:
        if print_stats:
            self._start_print_thread()

        if plot_stats:
            self._start_stats_plotting()
        
        asyncio.run(self.dataprovider.run())