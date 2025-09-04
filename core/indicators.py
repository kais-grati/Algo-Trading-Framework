from collections import deque
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

class IndicatorValue:
    """Simple standardized indicator value for overlay indicators"""
    
    def __init__(self, value: Optional[float] = None, timestamp: Optional[Any] = None, 
                 color: Optional[str] = None, metadata: Optional[Dict] = None):
        self.value = value
        self.timestamp = timestamp
        self.color = color or "#FFFFFF"
        self.metadata = metadata or {}


class BaseIndicator(ABC):
    """Base class for simple indicators (overlay type)"""
    
    def __init__(self, period: int, name: Optional[str] = None):
        self.period = period
        self.name = name or self.__class__.__name__
        self.values = deque(maxlen=1000)
        self.is_ready = False
        self.color = "#FFFFFF"
        self.chart_type = "overlay"  # Default to overlay
        
    @abstractmethod
    def calculate(self, candles: List[Dict]) -> Optional[IndicatorValue]:
        pass
    
    def update(self, candle_data: Dict) -> Optional[IndicatorValue]:
        pass
    
    def get_current_value(self) -> Optional[IndicatorValue]:
        return self.values[-1] if self.values else None
    
    def get_values(self, n: Optional[int] = None) -> List[IndicatorValue]:
        if n is None:
            return list(self.values)
        return list(self.values)[-n:] if len(self.values) >= n else list(self.values)


class ComplexIndicator(ABC):
    """Base class for complex indicators that manage their own plotting"""
    
    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self.is_ready = False
        self.chart_type = "separate"  # Complex indicators are separate by default
        self.plot_widget = None
        self.plot_items = {}
        
    @abstractmethod
    def update(self, candle_data: Dict) -> bool:
        """Update indicator and return True if updated successfully"""
        pass
    
    @abstractmethod
    def create_plot_widget(self, master_plot_widget) -> pg.PlotWidget:
        """Create and configure the plot widget for this indicator"""
        pass
    
    def get_plot_widget(self, master_plot_widget) -> pg.PlotWidget:
        """Get or create the plot widget"""
        if self.plot_widget is None:
            self.plot_widget = self.create_plot_widget(master_plot_widget)
        return self.plot_widget
    
    @abstractmethod
    def update_plot(self, time_data: List[float]):
        """Update the plot with current data"""
        pass


# Simple overlay indicators
class SMA(BaseIndicator):
    """Simple Moving Average - overlay indicator"""
    
    def __init__(self, period: int, source: str = 'close'):
        super().__init__(period, f"SMA_{period}")
        self.source = source
        self.candle_buffer = deque(maxlen=period)
        self.color = "#3498DB"
    
    def update(self, candle_data: Dict) -> Optional[IndicatorValue]:
        self.candle_buffer.append(candle_data[self.source])
        
        if len(self.candle_buffer) >= self.period:
            value = sum(self.candle_buffer) / len(self.candle_buffer)
            
            indicator_value = IndicatorValue(
                value=value,
                timestamp=candle_data.get('timestamp'),
                color=self.color,
                metadata={'period': self.period, 'source': self.source}
            )
            
            self.values.append(indicator_value)
            self.is_ready = True
            return indicator_value
        return None
    
    def calculate(self, candles: List[Dict]) -> Optional[IndicatorValue]:
        if len(candles) < self.period:
            return None
        
        recent_candles = candles[-self.period:]
        prices = [c[self.source] for c in recent_candles]
        sma_value = sum(prices) / len(prices)
        
        return IndicatorValue(
            value=sma_value,
            color=self.color,
            metadata={'period': self.period, 'source': self.source}
        )


class EMA(BaseIndicator):
    """Exponential Moving Average - overlay indicator"""
    
    def __init__(self, period: int, source: str = 'close'):
        super().__init__(period, f"EMA_{period}")
        self.source = source
        self.multiplier = 2 / (period + 1)
        self.ema_value = None
        self.color = "#E74C3C"
    
    def update(self, candle_data: Dict) -> Optional[IndicatorValue]:
        price = candle_data[self.source]
        
        if self.ema_value is None:
            self.ema_value = price
        else:
            self.ema_value = (price * self.multiplier) + (self.ema_value * (1 - self.multiplier))
        
        indicator_value = IndicatorValue(
            value=self.ema_value,
            timestamp=candle_data.get('timestamp'),
            color=self.color,
            metadata={'period': self.period, 'source': self.source}
        )
        
        self.values.append(indicator_value)
        self.is_ready = True
        return indicator_value
    
    def calculate(self, candles: List[Dict]) -> Optional[IndicatorValue]:
        if not candles:
            return None
        
        prices = [c[self.source] for c in candles]
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * self.multiplier) + (ema * (1 - self.multiplier))
        
        return IndicatorValue(
            value=ema,
            color=self.color,
            metadata={'period': self.period, 'source': self.source}
        )


class VWAP(BaseIndicator):
    """Volume Weighted Average Price - overlay indicator"""
    
    def __init__(self, reset_period: str = 'daily'):
        super().__init__(1, f"VWAP_{reset_period}")
        self.reset_period = reset_period
        self.cumulative_pv = 0
        self.cumulative_volume = 0
        self.last_reset_time = None
        self.color = "#FF6B35"
    
    def _should_reset(self, candle_data: Dict) -> bool:
        if self.reset_period == 'never':
            return False
        
        if self.last_reset_time is None:
            return True
        
        current_time = candle_data.get('timestamp', candle_data.get('time'))
        if current_time is None:
            return False
        
        if isinstance(current_time, (int, float)):
            from datetime import datetime
            current_time = datetime.fromtimestamp(current_time)
        
        if isinstance(self.last_reset_time, (int, float)):
            from datetime import datetime
            last_time = datetime.fromtimestamp(self.last_reset_time)
        else:
            last_time = self.last_reset_time
        
        if self.reset_period == 'daily':
            return current_time.date() != last_time.date()
        elif self.reset_period == 'weekly':
            return current_time.isocalendar()[1] != last_time.isocalendar()[1]
        
        return False
    
    def _get_typical_price(self, candle_data: Dict) -> float:
        high = candle_data.get('high', candle_data.get('close'))
        low = candle_data.get('low', candle_data.get('close'))
        close = candle_data['close']
        return (high + low + close) / 3
    
    def update(self, candle_data: Dict) -> Optional[IndicatorValue]:
        if self._should_reset(candle_data):
            self.cumulative_pv = 0
            self.cumulative_volume = 0
            self.last_reset_time = candle_data.get('timestamp', candle_data.get('time'))
        
        typical_price = self._get_typical_price(candle_data)
        volume = candle_data.get('volume', 1)
        
        self.cumulative_pv += typical_price * volume
        self.cumulative_volume += volume
        
        if self.cumulative_volume > 0:
            vwap_value = self.cumulative_pv / self.cumulative_volume
            
            indicator_value = IndicatorValue(
                value=vwap_value,
                timestamp=candle_data.get('timestamp'),
                color=self.color,
                metadata={'reset_period': self.reset_period}
            )
            
            self.values.append(indicator_value)
            self.is_ready = True
            return indicator_value
        
        return None
    
    def calculate(self, candles: List[Dict]) -> Optional[IndicatorValue]:
        if not candles:
            return None
        
        cumulative_pv = 0
        cumulative_volume = 0
        
        for candle in candles:
            typical_price = self._get_typical_price(candle)
            volume = candle.get('volume', 1)
            cumulative_pv += typical_price * volume
            cumulative_volume += volume
        
        if cumulative_volume == 0:
            return None
        
        return IndicatorValue(
            value=cumulative_pv / cumulative_volume,
            color=self.color,
            metadata={'reset_period': self.reset_period}
        )


# Complex indicators that handle their own plotting
class RSI(ComplexIndicator):
    """RSI as a complex indicator that manages its own plot"""
    
    def __init__(self, period: int = 14, source: str = 'close'):
        super().__init__(f"RSI_{period}")
        self.period = period
        self.source = source
        self.gains = deque(maxlen=period)
        self.losses = deque(maxlen=period)
        self.prev_price = None
        self.rsi_values = deque(maxlen=1000)
        self.color = "#9B59B6"
    
    def create_plot_widget(self, master_plot_widget) -> pg.PlotWidget:
        """Create RSI plot widget with reference lines"""
        from backtesting.misc import TimeAxisItem
        
        plot_widget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')},
            title=f"RSI ({self.period})"
        )
        plot_widget.setBackground('#2d2d2d')
        plot_widget.setLabel('left', 'RSI')
        plot_widget.setLabel('bottom', 'Time')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        plot_widget.setYRange(0, 100)
        
        # Link to master chart
        plot_widget.setXLink(master_plot_widget)
        
        # Add reference lines
        overbought = pg.InfiniteLine(pos=70, angle=0, pen=pg.mkPen(color='#ff4444', style=QtCore.Qt.PenStyle.DashLine))
        oversold = pg.InfiniteLine(pos=30, angle=0, pen=pg.mkPen(color='#00ff88', style=QtCore.Qt.PenStyle.DashLine))
        midline = pg.InfiniteLine(pos=50, angle=0, pen=pg.mkPen(color='#666666', style=QtCore.Qt.PenStyle.DashLine))
        
        plot_widget.addItem(overbought)
        plot_widget.addItem(oversold)
        plot_widget.addItem(midline)
        
        # Add labels
        overbought_label = pg.TextItem("70", anchor=(0, 0.5), color='#ff4444')
        oversold_label = pg.TextItem("30", anchor=(0, 0.5), color='#00ff88')
        overbought_label.setPos(0, 70)
        oversold_label.setPos(0, 30)
        plot_widget.addItem(overbought_label)
        plot_widget.addItem(oversold_label)
        
        # Create RSI line plot
        self.plot_items['rsi_line'] = plot_widget.plot(
            pen=pg.mkPen(color=self.color, width=2),
            name="RSI"
        )
        
        return plot_widget
    
    def update(self, candle_data: Dict) -> bool:
        price = candle_data[self.source]
        
        if self.prev_price is not None:
            change = price - self.prev_price
            gain = max(change, 0)
            loss = max(-change, 0)
            
            self.gains.append(gain)
            self.losses.append(loss)
            
            if len(self.gains) >= self.period:
                avg_gain = sum(self.gains) / len(self.gains)
                avg_loss = sum(self.losses) / len(self.losses)
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                
                self.rsi_values.append(rsi)
                self.is_ready = True
                self.prev_price = price
                return True
        
        self.prev_price = price
        return False
    
    def update_plot(self, time_data: List[float]):
        """Update the RSI plot"""
        if not self.is_ready or not self.plot_items.get('rsi_line'):
            return
        
        rsi_data = list(self.rsi_values)
        min_len = min(len(time_data), len(rsi_data))
        
        if min_len > 0:
            self.plot_items['rsi_line'].setData(
                time_data[-min_len:], 
                rsi_data[-min_len:]
            )


class MACD(ComplexIndicator):
    """MACD as a complex indicator that manages its own plot"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(f"MACD_{fast_period}_{slow_period}_{signal_period}")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        self.fast_ema = EMA(fast_period)
        self.slow_ema = EMA(slow_period)
        self.signal_ema = EMA(signal_period)
        
        self.macd_values = deque(maxlen=1000)
        self.signal_values = deque(maxlen=1000)
        self.histogram_values = deque(maxlen=1000)
        
        self.colors = {
            'macd': '#2E86C1',
            'signal': '#E74C3C', 
            'histogram': '#F39C12'
        }
    
    def create_plot_widget(self, master_plot_widget) -> pg.PlotWidget:
        """Create MACD plot widget with multiple series"""
        from backtesting.misc import TimeAxisItem
        
        plot_widget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')},
            title=f"MACD ({self.fast_period}, {self.slow_period}, {self.signal_period})"
        )
        plot_widget.setBackground('#2d2d2d')
        plot_widget.setLabel('left', 'MACD')
        plot_widget.setLabel('bottom', 'Time')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Link to master chart
        plot_widget.setXLink(master_plot_widget)
        
        # Add zero line
        zero_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen(color='#666666', style=QtCore.Qt.PenStyle.DashLine))
        plot_widget.addItem(zero_line)
        
        # Create plot items
        self.plot_items['macd_line'] = plot_widget.plot(
            pen=pg.mkPen(color=self.colors['macd'], width=2),
            name="MACD"
        )
        
        self.plot_items['signal_line'] = plot_widget.plot(
            pen=pg.mkPen(color=self.colors['signal'], width=2),
            name="Signal"
        )
        
        self.plot_items['histogram'] = pg.BarGraphItem(
            x=[], height=[], width=0.8, 
            brush=self.colors['histogram']
        )
        plot_widget.addItem(self.plot_items['histogram'])
        
        return plot_widget
    
    def update(self, candle_data: Dict) -> bool:
        fast_val = self.fast_ema.update(candle_data)
        slow_val = self.slow_ema.update(candle_data)
        
        if fast_val is not None and slow_val is not None:
            macd_line = fast_val.value - slow_val.value
            self.macd_values.append(macd_line)
            
            # Calculate signal line
            signal_val = self.signal_ema.update({'close': macd_line})
            
            if signal_val is not None:
                self.signal_values.append(signal_val.value)
                histogram = macd_line - signal_val.value
                self.histogram_values.append(histogram)
                
                self.is_ready = True
                return True
        
        return False
    
    def update_plot(self, time_data: List[float]):
        """Update all MACD plot elements"""
        if not self.is_ready:
            return
        
        macd_data = list(self.macd_values)
        signal_data = list(self.signal_values)
        histogram_data = list(self.histogram_values)
        
        min_len = min(len(time_data), len(macd_data), len(signal_data), len(histogram_data))
        
        if min_len > 0:
            x_subset = time_data[-min_len:]
            
            # Update MACD line
            if 'macd_line' in self.plot_items:
                self.plot_items['macd_line'].setData(x_subset, macd_data[-min_len:])
            
            # Update signal line
            if 'signal_line' in self.plot_items:
                self.plot_items['signal_line'].setData(x_subset, signal_data[-min_len:])
            
            # Update histogram
            if 'histogram' in self.plot_items:
                # Calculate bar width
                if len(x_subset) > 1:
                    avg_interval = (x_subset[-1] - x_subset[0]) / len(x_subset)
                    bar_width = avg_interval * 0.6
                else:
                    bar_width = 0.8
                
                self.plot_items['histogram'].setOpts(
                    x=x_subset,
                    height=histogram_data[-min_len:],
                    width=bar_width
                )


class StochasticOscillator(ComplexIndicator):
    """Stochastic Oscillator as a complex indicator"""
    
    def __init__(self, k_period: int = 14, d_period: int = 3):
        super().__init__(f"Stoch_{k_period}_{d_period}")
        self.k_period = k_period
        self.d_period = d_period
        self.candle_buffer = deque(maxlen=k_period)
        self.k_values = deque(maxlen=1000)
        self.d_values = deque(maxlen=1000)
        self.k_buffer = deque(maxlen=d_period)
        
        self.colors = {
            'k': '#3498DB',
            'd': '#E74C3C'
        }
    
    def create_plot_widget(self, master_plot_widget) -> pg.PlotWidget:
        """Create Stochastic plot widget"""
        from backtesting.misc import TimeAxisItem
        
        plot_widget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')},
            title=f"Stochastic ({self.k_period}, {self.d_period})"
        )
        plot_widget.setBackground('#2d2d2d')
        plot_widget.setLabel('left', 'Stochastic %')
        plot_widget.setLabel('bottom', 'Time')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        plot_widget.setYRange(0, 100)
        
        # Link to master chart
        plot_widget.setXLink(master_plot_widget)
        
        # Add reference lines
        overbought = pg.InfiniteLine(pos=80, angle=0, pen=pg.mkPen(color='#ff4444', style=QtCore.Qt.PenStyle.DashLine))
        oversold = pg.InfiniteLine(pos=20, angle=0, pen=pg.mkPen(color='#00ff88', style=QtCore.Qt.PenStyle.DashLine))
        plot_widget.addItem(overbought)
        plot_widget.addItem(oversold)
        
        # Create plot lines
        self.plot_items['k_line'] = plot_widget.plot(
            pen=pg.mkPen(color=self.colors['k'], width=2),
            name="%K"
        )
        
        self.plot_items['d_line'] = plot_widget.plot(
            pen=pg.mkPen(color=self.colors['d'], width=2),
            name="%D"
        )
        
        return plot_widget
    
    def update(self, candle_data: Dict) -> bool:
        self.candle_buffer.append(candle_data)
        
        if len(self.candle_buffer) >= self.k_period:
            # Calculate %K
            highs = [c['high'] for c in self.candle_buffer]
            lows = [c['low'] for c in self.candle_buffer]
            current_close = candle_data['close']
            
            highest_high = max(highs)
            lowest_low = min(lows)
            
            if highest_high != lowest_low:
                k_value = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
            else:
                k_value = 50
            
            self.k_values.append(k_value)
            self.k_buffer.append(k_value)
            
            # Calculate %D (SMA of %K)
            if len(self.k_buffer) >= self.d_period:
                d_value = sum(self.k_buffer) / len(self.k_buffer)
                self.d_values.append(d_value)
                self.is_ready = True
                return True
        
        return False
    
    def update_plot(self, time_data: List[float]):
        """Update Stochastic plot"""
        if not self.is_ready:
            return
        
        k_data = list(self.k_values)
        d_data = list(self.d_values)
        
        # Update %K line
        if k_data and 'k_line' in self.plot_items:
            min_len = min(len(time_data), len(k_data))
            if min_len > 0:
                self.plot_items['k_line'].setData(time_data[-min_len:], k_data[-min_len:])
        
        # Update %D line
        if d_data and 'd_line' in self.plot_items:
            min_len = min(len(time_data), len(d_data))
            if min_len > 0:
                self.plot_items['d_line'].setData(time_data[-min_len:], d_data[-min_len:])