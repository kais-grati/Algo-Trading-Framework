from multiprocessing import Process, Event, Queue
import sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from collections import deque
import numpy as np
from datetime import datetime

class PlotData:
    """Data structure for sending comprehensive plotting information."""
    def __init__(self, stats, candle, recent_events=None, current_position=None):
        self.stats = stats
        self.candle = candle
        self.recent_events = recent_events or []
        self.current_position = current_position

    def to_dict(self):
        return {
            'stats': self.stats,
            'candle': {
                'timestamp': self.candle.timestamp,
                'open': self.candle.open,
                'high': self.candle.high,
                'low': self.candle.low,
                'close': self.candle.close,
                'volume': getattr(self.candle, 'volume', 0)
            },
            'recent_events': self.recent_events,
            'current_position': self.current_position
        }

class TradingDashboard(Process):
    def __init__(self, stop_event, queue: Queue, interval_ms: int = 100):
        super().__init__(daemon=False)
        self.stop_event = stop_event
        self.queue = queue
        self.interval_ms = interval_ms

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

    def create_charts(self, parent_layout):
        """Create all chart widgets"""
        
        # Price chart with position markers
        self.price_plot_widget = pg.PlotWidget(title="Price Chart with Positions")
        self.price_plot_widget.setBackground('#2d2d2d')
        self.price_plot_widget.setLabel('left', 'Price ($)')
        self.price_plot_widget.setLabel('bottom', 'Time')
        self.price_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Price line
        self.price_curve = self.price_plot_widget.plot(pen=pg.mkPen(color='#ffffff', width=2))
        
        # Volume bars (secondary y-axis)
        self.volume_plot_widget = pg.PlotWidget(title="Volume")
        self.volume_plot_widget.setBackground('#2d2d2d')
        self.volume_plot_widget.setLabel('left', 'Volume')
        self.volume_plot_widget.setLabel('bottom', 'Time')
        self.volume_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.volume_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush='#4444ff')
        self.volume_plot_widget.addItem(self.volume_bars)
        
        # Equity curve plot
        self.equity_plot_widget = pg.PlotWidget(title="Equity Curve")
        self.equity_plot_widget.setBackground('#2d2d2d')
        self.equity_plot_widget.setLabel('left', 'Equity ($)')
        self.equity_plot_widget.setLabel('bottom', 'Time')
        self.equity_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.equity_curve = self.equity_plot_widget.plot(pen=pg.mkPen(color='#00ff88', width=2))
        self.equity_fill = self.equity_plot_widget.plot(pen=None, fillLevel=0, brush=pg.mkBrush(color=(0, 255, 136, 30)))
        
        # Drawdown plot
        self.drawdown_plot_widget = pg.PlotWidget(title="Drawdown")
        self.drawdown_plot_widget.setBackground('#2d2d2d')
        self.drawdown_plot_widget.setLabel('left', 'Drawdown ($)')
        self.drawdown_plot_widget.setLabel('bottom', 'Time')
        self.drawdown_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.drawdown_curve = self.drawdown_plot_widget.plot(pen=pg.mkPen(color='#ff4444', width=2))
        self.drawdown_fill = self.drawdown_plot_widget.plot(pen=None, fillLevel=0, brush=pg.mkBrush(color=(255, 68, 68, 30)))
        
        # Add charts to layout with appropriate sizing
        parent_layout.addWidget(self.price_plot_widget, 2)    # Price chart (largest)
        parent_layout.addWidget(self.volume_plot_widget, 1)   # Volume chart
        parent_layout.addWidget(self.equity_plot_widget, 2)   # Equity chart
        parent_layout.addWidget(self.drawdown_plot_widget, 1) # Drawdown chart

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
        self.events_list.setMaximumHeight(150)
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
        """Add position markers to price chart"""
        # Clear existing markers
        for marker in self.position_markers:
            self.price_plot_widget.removeItem(marker)
        self.position_markers.clear()
        
        # Add new markers for recent events
        for event in events[-20:]:  # Show last 20 events
            try:
                event_type = event.get('event_type', '')
                price = event.get('price', 0)
                time_index = len(self.time_data)  # Use current time index
                
                # Define marker styles for different event types
                marker_styles = {
                    'open_long': {'color': '#00ff00', 'symbol': 'u', 'size': 12},
                    'open_short': {'color': '#ff0000', 'symbol': 'd', 'size': 12},
                    'close_full': {'color': '#ffff00', 'symbol': 'x', 'size': 10},
                    'close_partial': {'color': '#ffaa00', 'symbol': 'x', 'size': 8},
                    'tp_hit': {'color': '#00ff88', 'symbol': 's', 'size': 10},
                    'sl_hit': {'color': '#ff4444', 'symbol': 's', 'size': 10},
                    'increase_long': {'color': '#88ff00', 'symbol': '+', 'size': 8},
                    'increase_short': {'color': '#ff8800', 'symbol': '+', 'size': 8}
                }
                
                if event_type in marker_styles:
                    style = marker_styles[event_type]
                    scatter = pg.ScatterPlotItem(
                        x=[time_index],
                        y=[price],
                        pen=pg.mkPen(color=style['color'], width=2),
                        brush=pg.mkBrush(color=style['color']),
                        symbol=style['symbol'],
                        size=style['size']
                    )
                    self.price_plot_widget.addItem(scatter)
                    self.position_markers.append(scatter)
                    
            except Exception:
                continue  # Skip invalid events

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
        try:
            # Get all available data from queue
            while not self.queue.empty():
                plot_data = self.queue.get_nowait()
                self.current_plot_data = plot_data
                
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
                
                # Add data points
                if hasattr(stats, 'equity'):
                    self.equity_data.append(stats.equity)
                    
                    # Calculate drawdown from peak
                    if len(self.equity_data) > 0:
                        peak = max(self.equity_data)
                        current_dd = peak - stats.equity
                        self.drawdown_data.append(-current_dd)  # Negative for display
                    else:
                        self.drawdown_data.append(0)
                
                # Add price and volume data if available
                if candle:
                    self.price_data.append(candle.close)
                    self.volume_data.append(getattr(candle, 'volume', 0))
                
                self.time_data.append(len(self.time_data))
                
            # Update charts if we have data
            if self.current_plot_data and len(self.time_data) > 0:
                self.update_charts()
                self.update_stats_display()
                self.update_events_list()
                self.update_header_status()
                
        except Exception as e:
            pass  # Handle queue empty gracefully

        # Check stop condition
        if self.stop_event.is_set():
            pass

    def update_charts(self):
        """Update all chart displays"""
        x_data = list(self.time_data)
        
        # Update equity curve
        if len(self.equity_data) > 0:
            equity_y = list(self.equity_data)
            self.equity_curve.setData(x_data, equity_y)
            self.equity_fill.setData(x_data, equity_y)
        
        # Update drawdown curve
        if len(self.drawdown_data) > 0:
            drawdown_y = list(self.drawdown_data)
            self.drawdown_curve.setData(x_data, drawdown_y)
            self.drawdown_fill.setData(x_data, drawdown_y)
        
        # Update price chart
        if len(self.price_data) > 0:
            price_y = list(self.price_data)
            self.price_curve.setData(x_data, price_y)
            
            # Add position markers
            if hasattr(self.current_plot_data, 'recent_events') and self.current_plot_data.recent_events:
                self.add_position_markers(self.current_plot_data.recent_events)
        
        # Update volume chart
        if len(self.volume_data) > 0:
            volume_y = list(self.volume_data)
            self.volume_bars.setOpts(x=x_data, height=volume_y, width=0.6)

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