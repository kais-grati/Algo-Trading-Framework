from abc import abstractmethod
from multiprocessing import Event, Queue
import sys
from data import BaseCandle
from typing import List, Optional, Tuple
from data import BaseDataProvider
from data.data_provider import BaseSubscriber
from backtesting.backtester import BaseBacktester
from backtesting.plotter import TradingDashboard, PlotData
from core.position_manager import BasePositionManager
from core.indicator_manager import BaseIndicatorManager, BaseIndicator
import asyncio, os, time, threading
from collections import deque
from backtesting.misc import ChartType



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

        self.indicator_manager = BaseIndicatorManager()

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
            # Check if this is an update to existing candle or a new one
            is_live_update = False
            if (len(self.price_history) > 0 and 
                self.price_history[-1]['timestamp'] == candle.timestamp):
                is_live_update = True
            
            # Handle price history for live updates
            candle_data = {
                'timestamp': candle.timestamp,
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': getattr(candle, 'volume', 0)
            }
            
            if is_live_update:
                # Update the last candle in history
                self.price_history[-1] = candle_data
            else:
                # Add new candle to history
                self.price_history.append(candle_data)

            # Run strategy logic
            self.on_candle(candle)
            
            # Update indicators (they should handle live updates internally)
            self.indicator_manager.update_all(candle)

            # Update backtester
            if self.backtester:
                self.backtester.update(candle)

                if self.plot_stats:
                    try:
                        # Get recent position events
                        recent_events = self.backtester.get_recent_position_events()
                        
                        # Get current position info
                        current_position = self.position_manager.get_current_position_info()
                        
                        plot_data = PlotData(
                            stats=self.backtester.stats,
                            candle=candle,
                            recent_events=recent_events,
                            current_position=current_position,
                            overlay_indicator_data=self.indicator_manager.get_plottable_indicators(separate_chart=False),
                            seperate_chart_indicator_data=self.indicator_manager.get_plottable_indicators(separate_chart=True),
                        )
                        
                        self.queue.put_nowait(plot_data)
                    except Exception:
                        print("Error while sending data to GUI")
                    
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

    def _start_stats_plotting(self,
        chart_type: ChartType = ChartType.CANDLESTICK,
        show_n_candles: int = 100,
        interval_ms: int = 100
    ):
        plotter = TradingDashboard(self.plot_stop_event, 
                                   self.queue, 
                                   chart_type=chart_type, 
                                   show_n_candles=show_n_candles, 
                                   interval_ms=interval_ms)
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
    

    def run(self, 
            print_stats: bool = True, 
            plot_stats: bool = False,
            chart_type: Optional[ChartType] = None,
            show_n_candles: Optional[int] = None,
            interval_ms: Optional[int] = None
        ) -> None:
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
            self._start_stats_plotting(chart_type=chart_type or ChartType.CANDLESTICK, 
                                       show_n_candles=show_n_candles or 100, 
                                       interval_ms=interval_ms or 100)
        
        try:
            asyncio.run(self.dataprovider.run())
        except KeyboardInterrupt:
            print("Stopping strategy...")
            self.print_stop_event.set()
            self.plot_stop_event.set()
            sys.exit()


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