from multiprocessing import Process, Event, Queue
import sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from collections import deque
import numpy as np
from datetime import datetime
from backtesting.candle_item import CandlestickItem
from backtesting.misc import TimeAxisItem, PlotData, ChartType


class TradingDashboard(Process):
    def __init__(self, stop_event, queue: Queue, chart_type: ChartType = ChartType.CANDLESTICK, show_n_candles: int = 100, interval_ms: int = 100):
        super().__init__(daemon=False)
        self.stop_event = stop_event
        self.queue = queue
        self.interval_ms = interval_ms
        self.chart_type = chart_type
        self.show_n_candles = show_n_candles
        self.candle_buffer = np.empty((0, 5), dtype=float)

    def run(self):
        app = QtWidgets.QApplication(sys.argv)
        
        # Create main window
        main_widget = QtWidgets.QWidget()
        main_widget.setWindowTitle("Trading Dashboard")
        main_widget.setGeometry(100, 100, 1600, 1000)
        main_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 12px;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3c3c3c;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #00aaff;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        
        # Title and current info bar
        self.create_header(main_layout)
        
        # Content layout (horizontal split)
        content_layout = QtWidgets.QHBoxLayout()
        
        # Left side: Charts (70% width)
        charts_widget = QtWidgets.QWidget()
        charts_layout = QtWidgets.QVBoxLayout(charts_widget)
        
        # Create chart plots
        self.create_charts(charts_layout)
        
        # Right side: Statistics (30% width)
        stats_widget = QtWidgets.QWidget()
        stats_layout = QtWidgets.QVBoxLayout(stats_widget)
        
        # Create stats groups
        self.create_stats_groups(stats_layout)
        
        # Add scroll area for stats
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(stats_widget)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background-color: #3c3c3c;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #666666;
                border-radius: 6px;
            }
        """)
        
        # Add widgets to content layout
        content_layout.addWidget(charts_widget, 7)  # 70% width
        content_layout.addWidget(scroll_area, 3)    # 30% width
        
        main_layout.addLayout(content_layout)
        
        # Data storage
        self.equity_data = deque(maxlen=5000)
        self.drawdown_data = deque(maxlen=5000)
        self.price_data = deque(maxlen=5000)
        self.volume_data = deque(maxlen=5000)
        self.time_data = deque(maxlen=5000)
        self.current_plot_data: PlotData = PlotData(None, None)
        self.recent_events = deque(maxlen=100)
        
        # Position markers storage
        self.position_markers = []
        
        # Update timer
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update_dashboard)
        timer.start(self.interval_ms)
        
        main_widget.show()
        app.exec_()

    def create_header(self, parent_layout):
        """Create header with title and current status"""
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        
        # Title
        title_label = QtWidgets.QLabel("TRADING DASHBOARD")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #00aaff;
            margin: 10px;
        """)
        
        # Current status (right aligned)
        self.current_price_label = QtWidgets.QLabel("Price: $0.00")
        self.current_position_label = QtWidgets.QLabel("Position: None")
        self.last_update_label = QtWidgets.QLabel("Last Update: --")
        
        status_widget = QtWidgets.QWidget()
        status_layout = QtWidgets.QVBoxLayout(status_widget)
        status_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        
        for label in [self.current_price_label, self.current_position_label, self.last_update_label]:
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            label.setStyleSheet("font-size: 14px; color: #cccccc; margin: 2px;")
            status_layout.addWidget(label)
        
        header_layout.addWidget(title_label, 7)
        header_layout.addWidget(status_widget, 3)
        parent_layout.addWidget(header_widget)

    def create_legend_widget(self):
        """Create a legend widget for position markers using actual scatter plot items"""
        legend_widget = QtWidgets.QWidget()
        legend_layout = QtWidgets.QHBoxLayout(legend_widget)
        legend_layout.setContentsMargins(10, 5, 10, 5)
        
        # Create legend items that exactly match the markers
        legend_items = [
            ('t1', '#00ff00', 12, 'Open Long'),
            ('t', '#570000', 12, 'Open Short'),
            ('x', '#ffff00', 10, 'Close Full'),
            ('x', '#ffaa00', 8, 'Close Partial'),
            ('o', '#004B00', 10, 'Take Profit'),
            ('o', '#570000', 10, 'Stop Loss'),
            ('+', '#004B00', 8, 'Increase Long'),
            ('+', '#ff8800', 8, 'Increase Short')
        ]
        
        for symbol, color, size, description in legend_items:
            # Create a mini container for each legend item
            item_widget = QtWidgets.QWidget()
            item_layout = QtWidgets.QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 2, 5, 2)
            item_layout.setSpacing(8)
            
            # Create a mini plot widget for the symbol
            symbol_plot = pg.PlotWidget()
            symbol_plot.setFixedSize(25, 20)
            symbol_plot.setBackground('#2d2d2d')
            symbol_plot.hideAxis('left')
            symbol_plot.hideAxis('bottom')
            symbol_plot.setMouseEnabled(x=False, y=False)
            symbol_plot.setMenuEnabled(False)
            symbol_plot.setXRange(0, 1)
            symbol_plot.setYRange(0, 1)
            
            # Add the actual scatter plot item
            scatter = pg.ScatterPlotItem(
                x=[0.5],
                y=[0.5],
                pen=pg.mkPen(color=color, width=2),
                brush=pg.mkBrush(color=color),
                symbol=symbol,
                size=size
            )
            symbol_plot.addItem(scatter)
            
            # Description label
            desc_label = QtWidgets.QLabel(description)
            desc_label.setStyleSheet("color: #cccccc; font-size: 10px;")
            
            item_layout.addWidget(symbol_plot)
            item_layout.addWidget(desc_label)
            item_widget.setMaximumWidth(140)
            
            legend_layout.addWidget(item_widget)
        
        legend_layout.addStretch()  # Push items to left
        
        # Style the legend widget
        legend_widget.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
            }
        """)
        legend_widget.setMaximumHeight(40)
        
        return legend_widget

    def create_charts(self, parent_layout):
        """Create all chart widgets"""
        
        # Price chart with position markers
        self.price_plot_widget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')},
            title="Price Chart with Positions"
        )
        self.price_plot_widget.setBackground('#2d2d2d')
        self.price_plot_widget.setLabel('left', 'Price ($)')
        self.price_plot_widget.setLabel('bottom', 'Time')
        self.price_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        if self.chart_type == ChartType.CANDLESTICK:
            self.candlestick_item = CandlestickItem()
            self.price_plot_widget.addItem(self.candlestick_item)
        elif self.chart_type == ChartType.HOLLOW_CANDLESTICK:
            from backtesting.candle_item import HollowCandlestickItem
            self.candlestick_item = HollowCandlestickItem()
            self.price_plot_widget.addItem(self.candlestick_item)
        elif self.chart_type == ChartType.LINE:
            self.price_curve = self.price_plot_widget.plot(pen=pg.mkPen(color="#FFFFFF", width=2))
        
        # Create container for price chart and legend
        price_container = QtWidgets.QWidget()
        price_layout = QtWidgets.QVBoxLayout(price_container)
        price_layout.setContentsMargins(0, 0, 0, 0)
        price_layout.setSpacing(2)
        
        # Add legend above the price chart
        legend_widget = self.create_legend_widget()
        price_layout.addWidget(legend_widget)
        price_layout.addWidget(self.price_plot_widget)
        
        # Volume bars (secondary y-axis)
        self.volume_plot_widget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')},
            title="Volume"
        )
        self.volume_plot_widget.setBackground('#2d2d2d')
        self.volume_plot_widget.setLabel('left', 'Volume')
        self.volume_plot_widget.setLabel('bottom', 'Time')
        self.volume_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.volume_bars = pg.BarGraphItem(x=[], height=[], width=5, brush='#4444ff')
        self.volume_plot_widget.addItem(self.volume_bars)
        
        
        # Equity curve plot
        self.equity_plot_widget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')},
            title="Equity Curve"
        )
        self.equity_plot_widget.setBackground('#2d2d2d')
        self.equity_plot_widget.setLabel('left', 'Equity ($)')
        self.equity_plot_widget.setLabel('bottom', 'Time')
        self.equity_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.equity_curve = self.equity_plot_widget.plot(pen=pg.mkPen(color='#00ff88', width=2))
        self.equity_fill = self.equity_plot_widget.plot(pen=None, fillLevel=0, brush=pg.mkBrush(color=(0, 255, 136, 30)))
        
        # Drawdown plot
        self.drawdown_plot_widget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')},
            title="Drawdown"
        )
        self.drawdown_plot_widget.setBackground('#2d2d2d')
        self.drawdown_plot_widget.setLabel('left', 'Drawdown ($)')
        self.drawdown_plot_widget.setLabel('bottom', 'Time')
        self.drawdown_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.drawdown_curve = self.drawdown_plot_widget.plot(pen=pg.mkPen(color='#ff4444', width=2))
        self.drawdown_fill = self.drawdown_plot_widget.plot(pen=None, fillLevel=0, brush=pg.mkBrush(color=(255, 68, 68, 30)))
        
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(price_container)
        splitter.addWidget(self.volume_plot_widget)
        splitter.addWidget(self.equity_plot_widget)
        splitter.addWidget(self.drawdown_plot_widget)
        
        # Optional: set initial stretch ratios
        splitter.setSizes([500, 100, 200, 100])
        
        # Add splitter to the parent layout
        parent_layout.addWidget(splitter)

    def create_stats_groups(self, parent_layout):
        """Create organized statistics display groups"""
        
        # Current Position Status
        self.position_status_group = QtWidgets.QGroupBox("Current Position")
        pos_status_layout = QtWidgets.QVBoxLayout(self.position_status_group)
        self.position_side_label = QtWidgets.QLabel("Side: None")
        self.position_qty_label = QtWidgets.QLabel("Quantity: 0.00")
        self.position_avg_price_label = QtWidgets.QLabel("Avg Price: $0.00")
        self.position_unrealized_pnl_label = QtWidgets.QLabel("Unrealized PnL: $0.00")
        self.position_tp_levels_label = QtWidgets.QLabel("TP Levels: 0")
        self.position_sl_levels_label = QtWidgets.QLabel("SL Levels: 0")
        
        for label in [self.position_side_label, self.position_qty_label, self.position_avg_price_label,
                      self.position_unrealized_pnl_label, self.position_tp_levels_label, self.position_sl_levels_label]:
            label.setStyleSheet("margin: 3px; padding: 2px; font-size: 11px;")
            pos_status_layout.addWidget(label)
        
        # Performance Overview
        self.perf_group = QtWidgets.QGroupBox("Performance")
        perf_layout = QtWidgets.QVBoxLayout(self.perf_group)
        self.total_pnl_label = QtWidgets.QLabel("Total P&L: $0.00")
        self.current_equity_label = QtWidgets.QLabel("Current Equity: $0.00")
        self.profit_factor_label = QtWidgets.QLabel("Profit Factor: 0.00")
        self.max_drawdown_label = QtWidgets.QLabel("Max Drawdown: $0.00")
        
        for label in [self.total_pnl_label, self.current_equity_label, self.profit_factor_label, self.max_drawdown_label]:
            label.setStyleSheet("margin: 3px; padding: 2px; font-size: 11px;")
            perf_layout.addWidget(label)
        
        # Position Statistics
        self.pos_group = QtWidgets.QGroupBox("Positions")
        pos_layout = QtWidgets.QVBoxLayout(self.pos_group)
        self.total_positions_label = QtWidgets.QLabel("Total Positions: 0")
        self.position_winrate_label = QtWidgets.QLabel("Win Rate: 0.00%")
        self.longs_label = QtWidgets.QLabel("Longs: 0")
        self.shorts_label = QtWidgets.QLabel("Shorts: 0")
        self.avg_duration_label = QtWidgets.QLabel("Avg Duration: 0.00h")
        
        for label in [self.total_positions_label, self.position_winrate_label, self.longs_label, self.shorts_label, self.avg_duration_label]:
            label.setStyleSheet("margin: 3px; padding: 2px; font-size: 11px;")
            pos_layout.addWidget(label)
        
        # Win/Loss Analysis
        self.wl_group = QtWidgets.QGroupBox("Win/Loss")
        wl_layout = QtWidgets.QVBoxLayout(self.wl_group)
        self.wins_label = QtWidgets.QLabel("Wins: 0")
        self.losses_label = QtWidgets.QLabel("Losses: 0")
        self.avg_win_label = QtWidgets.QLabel("Avg Win: $0.00")
        self.avg_loss_label = QtWidgets.QLabel("Avg Loss: $0.00")
        self.max_win_label = QtWidgets.QLabel("Max Win: $0.00")
        self.max_loss_label = QtWidgets.QLabel("Max Loss: $0.00")
        
        for label in [self.wins_label, self.losses_label, self.avg_win_label, self.avg_loss_label, self.max_win_label, self.max_loss_label]:
            label.setStyleSheet("margin: 3px; padding: 2px; font-size: 11px;")
            wl_layout.addWidget(label)
        
        # Exit Analysis
        self.exit_group = QtWidgets.QGroupBox("Exits")
        exit_layout = QtWidgets.QVBoxLayout(self.exit_group)
        self.exit_winrate_label = QtWidgets.QLabel("Exit Win Rate: 0.00%")
        self.tp_hits_label = QtWidgets.QLabel("Take Profit Hits: 0")
        self.sl_hits_label = QtWidgets.QLabel("Stop Loss Hits: 0")
        
        for label in [self.exit_winrate_label, self.tp_hits_label, self.sl_hits_label]:
            label.setStyleSheet("margin: 3px; padding: 2px; font-size: 11px;")
            exit_layout.addWidget(label)
        
        # Recent Events
        self.events_group = QtWidgets.QGroupBox("Recent Events")
        events_layout = QtWidgets.QVBoxLayout(self.events_group)
        self.events_list = QtWidgets.QListWidget()
        self.events_list.setMaximumHeight(400)
        self.events_list.setMinimumHeight(300)
        self.events_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                font-size: 10px;
            }
            QListWidget::item {
                padding: 2px;
                border-bottom: 1px solid #3c3c3c;
            }
        """)
        events_layout.addWidget(self.events_list)
        
        # Streaks & Risk
        self.risk_group = QtWidgets.QGroupBox("Risk & Streaks")
        risk_layout = QtWidgets.QVBoxLayout(self.risk_group)
        self.max_win_streak_label = QtWidgets.QLabel("Max Win Streak: 0")
        self.max_loss_streak_label = QtWidgets.QLabel("Max Loss Streak: 0")
        self.fees_paid_label = QtWidgets.QLabel("Fees Paid: $0.00")
        self.exposure_time_label = QtWidgets.QLabel("Exposure Time: 0.00h")
        
        for label in [self.max_win_streak_label, self.max_loss_streak_label, self.fees_paid_label, self.exposure_time_label]:
            label.setStyleSheet("margin: 3px; padding: 2px; font-size: 11px;")
            risk_layout.addWidget(label)
        
        # Long/Short Performance
        self.ls_group = QtWidgets.QGroupBox("Long/Short")
        ls_layout = QtWidgets.QVBoxLayout(self.ls_group)
        self.long_winrate_label = QtWidgets.QLabel("Long Win Rate: 0.00%")
        self.short_winrate_label = QtWidgets.QLabel("Short Win Rate: 0.00%")
        
        for label in [self.long_winrate_label, self.short_winrate_label]:
            label.setStyleSheet("margin: 3px; padding: 2px; font-size: 11px;")
            ls_layout.addWidget(label)
        
        # Add all groups to layout
        parent_layout.addWidget(self.position_status_group)
        parent_layout.addWidget(self.perf_group)
        parent_layout.addWidget(self.pos_group)
        parent_layout.addWidget(self.wl_group)
        parent_layout.addWidget(self.exit_group)
        parent_layout.addWidget(self.events_group)
        parent_layout.addWidget(self.risk_group)
        parent_layout.addWidget(self.ls_group)
        parent_layout.addStretch()  # Push everything to top

    def add_position_markers(self, events):
        """Add position markers to price chart with vertical offsets to avoid overlap"""
        for marker in self.position_markers:
            self.price_plot_widget.removeItem(marker)
        self.position_markers.clear()

        for event in events:
            try:
                event_type = event.get('event_type', '')
                price = event.get('price', 0)
                timestamp = event.get('timestamp', datetime.now())

                if isinstance(timestamp, datetime):
                    x_val = timestamp.timestamp()
                else:
                    x_val = float(timestamp)

                # Vertical offset
                offset = 0
                if event_type in ['open_long', 'open_short']:
                    offset = 0.0   
                elif event_type in ['close_full', 'close_partial']:
                    offset = 0.2
                elif event_type in ['tp_hit', 'sl_hit']:
                    offset = 0.4
                elif event_type in ['increase_long', 'increase_short']:
                    offset = 0.6

                y_val = price + offset  # shift marker above candle

                marker_styles = {
                    'open_long': {'color': "#004B00", 'symbol': 't1', 'size': 12},
                    'open_short': {'color': "#570000", 'symbol': 't', 'size': 12},
                    'close_full': {'color': '#ffff00', 'symbol': 'x', 'size': 10},
                    'close_partial': {'color': '#ffaa00', 'symbol': 'x', 'size': 8},
                    'tp_hit': {'color': '#004B00', 'symbol': 'o', 'size': 10},
                    'sl_hit': {'color': '#570000', 'symbol': 'o', 'size': 10},
                    'increase_long': {'color': '#004B00', 'symbol': '+', 'size': 8},
                    'increase_short': {'color': '#ff8800', 'symbol': '+', 'size': 8}
                }

                if event_type in marker_styles:
                    style = marker_styles[event_type]
                    scatter = pg.ScatterPlotItem(
                        x=[x_val],
                        y=[y_val],
                        pen=pg.mkPen(color=style['color'], width=2),
                        brush=pg.mkBrush(color=style['color']),
                        symbol=style['symbol'],
                        size=style['size'],
                        data=[{'event_type': event_type, 'price': price, 'timestamp': timestamp}]
                    )

                    # Set tooltip text
                    tooltip_text = f"Event: {event_type}\nPrice: ${price:.2f}\nTime: {timestamp.strftime('%H:%M:%S') if isinstance(timestamp, datetime) else timestamp}"
                    scatter.setToolTip(tooltip_text)

                    self.price_plot_widget.addItem(scatter)
                    self.position_markers.append(scatter)

            except Exception:
                continue



    def format_currency(self, value):
        """Format currency with color coding"""
        if value >= 0:
            return f"<span style='color: #00ff88;'>${value:,.2f}</span>"
        else:
            return f"<span style='color: #ff4444;'>${value:,.2f}</span>"

    def format_percentage(self, value):
        """Format percentage with color coding"""
        percentage = value * 100
        if percentage >= 50:
            color = "#00ff88"
        elif percentage >= 30:
            color = "#ffaa00"
        else:
            color = "#ff4444"
        return f"<span style='color: {color};'>{percentage:.2f}%</span>"

    def update_dashboard(self):
        """Update dashboard with latest data"""
        new_data_received = False
        
        # Get all available data from queue
        while not self.queue.empty():
            plot_data = self.queue.get_nowait()
            self.current_plot_data = plot_data
            new_data_received = True
            
            # Extract data from PlotData object
            if hasattr(plot_data, 'to_dict'):
                data_dict = plot_data.to_dict()
                stats = plot_data.stats
                candle = plot_data.candle
                recent_events = plot_data.recent_events or []
                current_position = plot_data.current_position
            else:
                # Fallback for direct stats objects
                stats = plot_data
                candle = None
                recent_events = []
                current_position = None
            
            # Store recent events
            if recent_events:
                self.recent_events.extend(recent_events)
            
            # Add data points for equity/drawdown
            if hasattr(stats, 'equity'):
                self.equity_data.append(stats.equity)
                
                # Calculate drawdown from peak
                if len(self.equity_data) > 0:
                    peak = max(self.equity_data)
                    current_dd = peak - stats.equity
                    self.drawdown_data.append(-current_dd)
                else:
                    self.drawdown_data.append(0)
            
            # Add candle data - this is the key fix
            if candle and hasattr(candle, 'timestamp'):
                timestamp = candle.timestamp.timestamp()
                
                # Add to time data
                self.time_data.append(timestamp)
                
                # For candlestick charts OHLC buffer
                if self.chart_type in [ChartType.CANDLESTICK, ChartType.HOLLOW_CANDLESTICK]:
                    # Create new candle array [timestamp, open, close, low, high]
                    new_candle = np.array([[
                        timestamp,
                        candle.open,
                        candle.close, 
                        candle.low,
                        candle.high
                    ]])
                    
                    # Add to buffer
                    if len(self.candle_buffer) == 0:
                        self.candle_buffer = new_candle
                    else:
                        self.candle_buffer = np.vstack([self.candle_buffer, new_candle])
                    
                    # Keep only last N candles
                    if len(self.candle_buffer) > self.show_n_candles:
                        self.candle_buffer = self.candle_buffer[-self.show_n_candles:]
                
                # For line charts, just store close price
                elif self.chart_type == ChartType.LINE:
                    self.price_data.append(candle.close)
                
                # Store volume data
                self.volume_data.append(getattr(candle, 'volume', 0))
        
        # Only update charts if we received new data
        if new_data_received and len(self.time_data) > 0:
            self.update_charts()
            self.update_stats_display()
            self.update_events_list()
            self.update_header_status()
        
        # Check stop condition
        if self.stop_event.is_set():
            pass

    def update_charts(self):
        """Update all chart displays"""
        # Only proceed if we have data
        if len(self.time_data) == 0:
            return
            
        x_data = list(self.time_data)
        
        # ---- Equity curve ----
        if self.equity_data and len(self.equity_data) > 0:
            equity_y = list(self.equity_data)
            # Ensure x_data and equity_y have same length
            min_len = min(len(x_data), len(equity_y))
            self.equity_curve.setData(x_data[-min_len:], equity_y[-min_len:])
            self.equity_fill.setData(x_data[-min_len:], equity_y[-min_len:])
        
        # ---- Drawdown ----
        if self.drawdown_data and len(self.drawdown_data) > 0:
            drawdown_y = list(self.drawdown_data)
            min_len = min(len(x_data), len(drawdown_y))
            self.drawdown_curve.setData(x_data[-min_len:], drawdown_y[-min_len:])
            self.drawdown_fill.setData(x_data[-min_len:], drawdown_y[-min_len:])
        
        # ---- Price charts ----
        if self.chart_type in [ChartType.CANDLESTICK, ChartType.HOLLOW_CANDLESTICK]:
            
            if len(self.candle_buffer) > 0:
                # Ensure we have valid OHLC data
                if self.candle_buffer.shape[1] == 5:  # timestamp, open, close, low, high
                    self.candlestick_item.setOHLCData(self.candle_buffer)
                else:
                    print(f"Invalid candle buffer shape: {self.candle_buffer.shape}")
        
        elif self.chart_type == ChartType.LINE and len(self.price_data) > 0:
            price_y = list(self.price_data)
            min_len = min(len(x_data), len(price_y))
            self.price_curve.setData(x_data[-min_len:], price_y[-min_len:])
        
        # Add position markers if available
        if (hasattr(self.current_plot_data, "recent_events") and 
            self.current_plot_data.recent_events):
            self.add_position_markers(self.current_plot_data.recent_events)
        
        # ---- Volume bars ----
        if self.volume_data and len(self.volume_data) > 0:
            volume_y = list(self.volume_data)
            min_len = min(len(x_data), len(volume_y))
            # Adjust bar width based on time intervals
            if len(x_data) > 1:
                avg_interval = (x_data[-1] - x_data[0]) / len(x_data)
                bar_width = avg_interval * 0.5  # 80% of interval
            else:
                bar_width = 100
            
            self.volume_bars.setOpts(
                x=x_data[-min_len:], 
                height=volume_y[-min_len:], 
                width=bar_width
            )



    def update_header_status(self):
        """Update header status information"""
        if not self.current_plot_data:
            return
            
        try:
            # Extract data
            if hasattr(self.current_plot_data, 'to_dict'):
                data_dict = self.current_plot_data.to_dict()
                candle = self.current_plot_data.candle
                current_position = self.current_plot_data.current_position
                stats = self.current_plot_data.stats
            else:
                candle = None
                current_position = None
                stats = self.current_plot_data
            
            # Update current price
            if candle:
                self.current_price_label.setText(f"Price: ${candle.close:,.2f}")
            
            # Update current position
            if current_position:
                side = current_position.get('side', 'None')
                qty = current_position.get('quantity', 0)
                self.current_position_label.setText(f"Position: {side} {qty:.4f}")
            else:
                self.current_position_label.setText("Position: None")
            
            # Update last update time
            self.last_update_label.setText(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception:
            pass

    def update_events_list(self):
        """Update recent events list"""
        try:
            # Clear existing items
            self.events_list.clear()
            
            # Add recent events (last 10)
            recent = list(self.recent_events)[-10:]
            for event in reversed(recent):  # Show newest first
                event_type = event.get('event_type', 'unknown')
                price = event.get('price', 0)
                timestamp = event.get('timestamp', datetime.now())
                
                # Format timestamp
                if isinstance(timestamp, datetime):
                    time_str = timestamp.strftime('%H:%M:%S')
                else:
                    time_str = str(timestamp)[:8] if str(timestamp) else '--:--:--'
                
                # Create event text with color coding
                event_colors = {
                    'open_long': '#00ff00',
                    'open_short': '#ff0000',
                    'close_full': '#ffff00',
                    'close_partial': '#ffaa00',
                    'tp_hit': '#00ff88',
                    'sl_hit': '#ff4444',
                    'increase_long': '#88ff00',
                    'increase_short': '#ff8800'
                }
                
                color = event_colors.get(event_type, '#ffffff')
                item_text = f"[{time_str}] {event_type.upper().replace('_', ' ')}: ${price:.2f}"
                
                item = QtWidgets.QListWidgetItem(item_text)
                item.setForeground(QtGui.QColor(color))
                self.events_list.addItem(item)
                
        except Exception:
            pass

    def update_stats_display(self):
        """Update all statistics labels"""
        if not self.current_plot_data:
            return
        
        try:
            # Extract stats
            if hasattr(self.current_plot_data, 'stats'):
                stats = self.current_plot_data.stats
                current_position = self.current_plot_data.current_position
            else:
                return
            
            # Update current position status
            if current_position:
                side = current_position.get('side', 'None')
                qty = current_position.get('quantity', 0)
                avg_price = current_position.get('avg_price', 0)
                unrealized_pnl = current_position.get('unrealized_pnl', 0)
                tp_levels = current_position.get('take_profit_levels', 0)
                sl_levels = current_position.get('stop_loss_levels', 0)
                
                side_color = '#00ff88' if side == 'LONG' else '#ff4444' if side == 'SHORT' else '#cccccc'
                
                self.position_side_label.setText(f"Side: <span style='color: {side_color};'>{side}</span>")
                self.position_qty_label.setText(f"Quantity: {qty:.6f}")
                self.position_avg_price_label.setText(f"Avg Price: ${avg_price:,.2f}")
                self.position_unrealized_pnl_label.setText(f"Unrealized PnL: {self.format_currency(unrealized_pnl)}")
                self.position_tp_levels_label.setText(f"TP Levels: {tp_levels}")
                self.position_sl_levels_label.setText(f"SL Levels: {sl_levels}")
            else:
                self.position_side_label.setText("Side: None")
                self.position_qty_label.setText("Quantity: 0.00")
                self.position_avg_price_label.setText("Avg Price: $0.00")
                self.position_unrealized_pnl_label.setText("Unrealized PnL: $0.00")
                self.position_tp_levels_label.setText("TP Levels: 0")
                self.position_sl_levels_label.setText("SL Levels: 0")
            
            # Performance Overview
            self.total_pnl_label.setText(f"Total P&L: {self.format_currency(stats.total_pnl)}")
            self.current_equity_label.setText(f"Current Equity: {self.format_currency(stats.equity)}")
            
            pf_color = "#00ff88" if stats.profit_factor >= 1.5 else "#ffaa00" if stats.profit_factor >= 1.0 else "#ff4444"
            self.profit_factor_label.setText(f"Profit Factor: <span style='color: {pf_color};'>{stats.profit_factor:.2f}</span>")
            self.max_drawdown_label.setText(f"Max Drawdown: {self.format_currency(-stats.max_drawdown)}")
            
            # Position Statistics
            self.total_positions_label.setText(f"Total Positions: {stats.positions}")
            self.position_winrate_label.setText(f"Win Rate: {self.format_percentage(stats.position_winrate)}")
            self.longs_label.setText(f"Longs: {stats.longs}")
            self.shorts_label.setText(f"Shorts: {stats.shorts}")
            self.avg_duration_label.setText(f"Avg Duration: {stats.avg_position_duration:.2f}h")
            
            # Win/Loss Analysis
            self.wins_label.setText(f"Wins: <span style='color: #00ff88;'>{stats.position_wins}</span>")
            self.losses_label.setText(f"Losses: <span style='color: #ff4444;'>{stats.position_losses}</span>")
            self.avg_win_label.setText(f"Avg Win: {self.format_currency(stats.avg_win)}")
            self.avg_loss_label.setText(f"Avg Loss: {self.format_currency(stats.avg_loss)}")
            self.max_win_label.setText(f"Max Win: {self.format_currency(stats.max_win)}")
            self.max_loss_label.setText(f"Max Loss: {self.format_currency(stats.max_loss)}")
            
            # Exit Analysis
            self.exit_winrate_label.setText(f"Exit Win Rate: {self.format_percentage(stats.exit_winrate)}")
            self.tp_hits_label.setText(f"Take Profit Hits: <span style='color: #00ff88;'>{stats.exit_wins}</span>")
            self.sl_hits_label.setText(f"Stop Loss Hits: <span style='color: #ff4444;'>{stats.exit_losses}</span>")
            
            # Risk & Streaks
            self.max_win_streak_label.setText(f"Max Win Streak: <span style='color: #00ff88;'>{stats.max_win_streak}</span>")
            self.max_loss_streak_label.setText(f"Max Loss Streak: <span style='color: #ff4444;'>{stats.max_loss_streak}</span>")
            self.fees_paid_label.setText(f"Fees Paid: {self.format_currency(stats.fees_paid)}")
            self.exposure_time_label.setText(f"Exposure Time: {stats.exposure_time:.2f}h")
            
            # Long/Short Performance
            self.long_winrate_label.setText(f"Long Win Rate: {self.format_percentage(stats.long_winrate)}")
            self.short_winrate_label.setText(f"Short Win Rate: {self.format_percentage(stats.short_winrate)}")
            
        except Exception as e:
            pass  # Handle any attribute errors gracefully