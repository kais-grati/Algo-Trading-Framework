from abc import abstractmethod
from multiprocessing import Event, Queue
from data import BaseCandle
from typing import Optional
from data import BaseDataProvider
from data.data_provider import BaseSubscriber
from backtesting.backtester import BaseBacktester
from backtesting.plotter import TradingDashboard, PlotData
from core.position_manager import BasePositionManager
import asyncio, os, time, threading
from collections import deque



class BaseStrategy(BaseSubscriber):
    def __init__(
        self, 
        dataprovider: BaseDataProvider,
        position_manager_kwargs: Optional[dict] = None,
        backtester_kwargs: Optional[dict] = None,
        price_history_size: int = 1000
    ) -> None:
        self.dataprovider = dataprovider

        pm_kwargs = position_manager_kwargs or {}
        self.position_manager = BasePositionManager(**pm_kwargs)

        bt_kwargs = backtester_kwargs or {}
        self.backtester = BaseBacktester(self.position_manager, **bt_kwargs)

        dataprovider.subscribe(self)

        # Enhanced plotting support
        self.queue = Queue()
        self.print_stop_event = threading.Event()
        self.plot_stop_event = Event()
        self.plot_stats = False
        self.print_stats = False
        
        # Store recent price history for plotting
        self.price_history = deque(maxlen=price_history_size)

    def update(self, candle: BaseCandle) -> None:
        """
        Update the strategy and backtest stats with a new candle.
        
        :param candle: The new candle data to update the strategy with.
        """
        # Store price history
        self.price_history.append({
            'timestamp': candle.timestamp,
            'open': candle.open,
            'high': candle.high,
            'low': candle.low,
            'close': candle.close,
            'volume': getattr(candle, 'volume', 0)
        })

        # Run strategy logic
        self.on_candle(candle)

        # Update backtester
        if self.backtester:
            self.backtester.update(candle)

            # Send comprehensive plot data if plotting is enabled
            if self.plot_stats:
                try:
                    # Get recent position events
                    recent_events = self.backtester.get_recent_position_events()
                    
                    # Get current position info
                    current_position = self.position_manager.get_current_position_info()
                    
                    # Create comprehensive plot data
                    plot_data = PlotData(
                        stats=self.backtester.stats,
                        candle=candle,
                        recent_events=recent_events,
                        current_position=current_position
                    )
                    
                    self.queue.put_nowait(plot_data)
                except Exception:
                    pass  # Handle queue full gracefully

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
        self.print_stop_event.set()
        self.plot_stop_event.set()

    def _start_print_thread(self):
        def print_loop():
            while not self.print_stop_event.is_set(): 
                if os.name == 'nt':
                    os.system('cls')
                else:
                    os.system('clear')
                print(self.backtester)
                time.sleep(1)  

        thread = threading.Thread(target=print_loop, daemon=True)
        thread.start()

    def _start_stats_plotting(self):
        plotter = TradingDashboard(self.plot_stop_event, self.queue)
        plotter.start()

    def get_price_history(self):
        """Get the stored price history for plotting."""
        return list(self.price_history)

    def get_all_position_events(self):
        """Get all position events for analysis."""
        if self.backtester:
            return self.backtester.get_all_position_events()
        return []

    def get_position_summary(self):
        """Get a summary of all position events grouped by type."""
        events = self.get_all_position_events()
        summary = {
            'open_long': [],
            'open_short': [],
            'close_full': [],
            'close_partial': [],
            'tp_hit': [],
            'sl_hit': [],
            'increase_long': [],
            'increase_short': []
        }
        
        for event in events:
            event_type = event.get('event_type')
            if event_type in summary:
                summary[event_type].append(event)
        
        return summary

    def run(self, print_stats: bool = True, plot_stats: bool = False) -> None:
        """
        Run the strategy with optional statistics display and plotting.
        
        :param print_stats: Whether to print statistics to console
        :param plot_stats: Whether to show the trading dashboard
        """
        self.plot_stats = plot_stats
        self.print_stats = print_stats
        
        if print_stats:
            self._start_print_thread()

        if plot_stats:
            self._start_stats_plotting()
        
        asyncio.run(self.dataprovider.run())

    def export_trade_log(self, filename: str = "trade_log.json"):
        """Export all position events and price history to a JSON file."""
        import json
        from pathlib import Path
        
        export_data = {
            'price_history': self.get_price_history(),
            'position_events': self.get_all_position_events(),
            'position_summary': self.get_position_summary(),
            'final_stats': self.backtester.get_results() if self.backtester else {}
        }
        
        Path(filename).write_text(json.dumps(export_data, default=str, indent=2))
        print(f"Trade log exported to {filename}")