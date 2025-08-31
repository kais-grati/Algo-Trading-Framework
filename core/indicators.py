from abc import ABC, abstractmethod
from collections import deque
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from data import BaseCandle

class BaseIndicator(ABC):
    """Base class for all indicators"""
    
    def __init__(self, period: int, name: Optional[str] = None):
        self.period = period
        self.name = name or self.__class__.__name__
        self.values = deque(maxlen=1000)  # Store indicator values
        self.is_ready = False
        self.color = "#FFFFFF"  # Default color for plotting
        
    @abstractmethod
    def calculate(self, candles: List[Dict]) -> Optional[Any]:
        """Calculate indicator value from candle data"""
        pass
    
    def update(self, candle_data: Dict) -> Optional[Any]:
        """Update indicator with new candle and return current value"""
        # This will be called by IndicatorManager
        pass
    
    def get_current_value(self) -> Optional[float]:
        """Get the most recent indicator value"""
        return self.values[-1] if self.values else None
    
    def get_values(self, n: Optional[int] = None) -> List[float]:
        """Get last n indicator values"""
        if n is None:
            return list(self.values)
        return list(self.values)[-n:] if len(self.values) >= n else list(self.values)

class SMA(BaseIndicator):
    """Simple Moving Average"""
    
    def __init__(self, period: int, source: str = 'close'):
        super().__init__(period, f"SMA_{period}")
        self.source = source
        self.candle_buffer = deque(maxlen=period)
    
    def calculate(self, candles: List[Dict]) -> Optional[float]:
        """Calculate SMA from a list of candles"""
        if len(candles) < self.period:
            return None
        
        recent_candles = candles[-self.period:]
        prices = [c[self.source] for c in recent_candles]
        return sum(prices) / len(prices)
    
    def update(self, candle_data: Dict) -> Optional[float]:
        self.candle_buffer.append(candle_data[self.source])
        
        if len(self.candle_buffer) >= self.period:
            value = sum(self.candle_buffer) / len(self.candle_buffer)
            self.values.append(value)
            self.is_ready = True
            return value
        return None

class EMA(BaseIndicator):
    """Exponential Moving Average"""
    
    def __init__(self, period: int, source: str = 'close'):
        super().__init__(period, f"EMA_{period}")
        self.source = source
        self.multiplier = 2 / (period + 1)
        self.ema_value = None
    
    def calculate(self, candles: List[Dict]) -> Optional[float]:
        """Calculate EMA from a list of candles"""
        if not candles:
            return None
        
        prices = [c[self.source] for c in candles]
        ema = prices[0]  # Start with first price
        
        for price in prices[1:]:
            ema = (price * self.multiplier) + (ema * (1 - self.multiplier))
        
        return ema
    
    def update(self, candle_data: Dict) -> Optional[float]:
        price = candle_data[self.source]
        
        if self.ema_value is None:
            self.ema_value = price
        else:
            self.ema_value = (price * self.multiplier) + (self.ema_value * (1 - self.multiplier))
        
        self.values.append(self.ema_value)
        self.is_ready = True
        return self.ema_value

class RSI(BaseIndicator):
    """Relative Strength Index"""
    
    def __init__(self, period: int = 14, source: str = 'close'):
        super().__init__(period, f"RSI_{period}")
        self.source = source
        self.gains = deque(maxlen=period)
        self.losses = deque(maxlen=period)
        self.prev_price = None
    
    def calculate(self, candles: List[Dict]) -> Optional[float]:
        """Calculate RSI from a list of candles"""
        if len(candles) < self.period + 1:
            return None
        
        prices = [c[self.source] for c in candles[-self.period-1:]]
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        if len(gains) < self.period:
            return None
        
        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def update(self, candle_data: Dict) -> Optional[float]:
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
                
                self.values.append(rsi)
                self.is_ready = True
                self.prev_price = price
                return rsi
        
        self.prev_price = price
        return None

class MACD(BaseIndicator):
    """MACD Indicator"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(slow_period, f"MACD_{fast_period}_{slow_period}_{signal_period}")
        self.fast_ema = EMA(fast_period)
        self.slow_ema = EMA(slow_period)
        self.signal_ema = EMA(signal_period)
        self.macd_values = deque(maxlen=1000)
        self.signal_values = deque(maxlen=1000)
        self.histogram_values = deque(maxlen=1000)
    
    def calculate(self, candles: List[Dict]) -> Optional[Dict[str, float]]:
        """Calculate MACD from a list of candles"""
        if len(candles) < self.period:
            return None
        
        # Calculate EMAs
        fast_ema = EMA(self.fast_ema.period)
        slow_ema = EMA(self.slow_ema.period)
        
        for candle in candles:
            fast_ema.update(candle)
            slow_ema.update(candle)
        
        fast_val = fast_ema.get_current_value()
        slow_val = slow_ema.get_current_value()
        
        if fast_val is None or slow_val is None:
            return None
        
        macd_line = fast_val - slow_val
        
        # For signal line, we'd need to calculate EMA of MACD values
        # This is simplified - in practice you'd need more historical MACD values
        return {
            'macd': macd_line,
            'signal': macd_line,  # Simplified
            'histogram': 0
        }
    
    def update(self, candle_data: Dict) -> Optional[Dict[str, float]]:
        fast_val = self.fast_ema.update(candle_data)
        slow_val = self.slow_ema.update(candle_data)
        
        if fast_val is not None and slow_val is not None:
            macd_line = fast_val - slow_val
            self.macd_values.append(macd_line)
            
            # Calculate signal line
            signal_val = self.signal_ema.update({'close': macd_line})
            
            if signal_val is not None:
                histogram = macd_line - signal_val
                
                result = {
                    'macd': macd_line,
                    'signal': signal_val,
                    'histogram': histogram
                }
                
                self.signal_values.append(signal_val)
                self.histogram_values.append(histogram)
                self.values.append(result)
                self.is_ready = True
                return result
        
        return None
    
class VWAP(BaseIndicator):
    """Volume Weighted Average Price Indicator"""
    
    def __init__(self, reset_period: str = 'daily', name: Optional[str] = None):
        """
        Initialize VWAP indicator
        
        Args:
            reset_period: When to reset VWAP calculation ('daily', 'weekly', 'session', or 'never')
            name: Optional custom name for the indicator
        """
        # VWAP doesn't use a traditional period, but we set it to 1 for base class
        super().__init__(1, name or f"VWAP_{reset_period}")
        self.reset_period = reset_period
        self.cumulative_pv = 0  # Cumulative price * volume
        self.cumulative_volume = 0  # Cumulative volume
        self.last_reset_time = None
        self.color = "#FF6B35"  # Orange color for VWAP
    
    def _should_reset(self, candle_data: Dict) -> bool:
        """Determine if VWAP should reset based on reset_period"""
        if self.reset_period == 'never':
            return False
        
        if self.last_reset_time is None:
            return True
        
        current_time = candle_data.get('timestamp', candle_data.get('time'))
        if current_time is None:
            return False
        
        # Convert timestamp to datetime if it's a number
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
        elif self.reset_period == 'session':
            # Reset at market open (9:30 AM for US markets)
            # This is a simplified version - you might want to customize for your market
            return (current_time.hour >= 9 and current_time.minute >= 30 and 
                   last_time.hour < 9 or (last_time.hour == 9 and last_time.minute < 30))
        
        return False
    
    def _get_typical_price(self, candle_data: Dict) -> float:
        """Calculate typical price (HLC/3)"""
        high = candle_data.get('high', candle_data.get('close'))
        low = candle_data.get('low', candle_data.get('close'))
        close = candle_data['close']
        
        return (high + low + close) / 3
    
    def calculate(self, candles: List[Dict]) -> Optional[float]:
        """Calculate VWAP from a list of candles"""
        if not candles:
            return None
        
        cumulative_pv = 0
        cumulative_volume = 0
        
        for candle in candles:
            typical_price = self._get_typical_price(candle)
            volume = candle.get('volume', 1)  # Default to 1 if no volume data
            
            cumulative_pv += typical_price * volume
            cumulative_volume += volume
        
        if cumulative_volume == 0:
            return None
        
        return cumulative_pv / cumulative_volume
    
    def update(self, candle_data: Dict) -> Optional[float]:
        """Update VWAP with new candle data"""
        # Check if we need to reset
        if self._should_reset(candle_data):
            self.cumulative_pv = 0
            self.cumulative_volume = 0
            self.last_reset_time = candle_data.get('timestamp', candle_data.get('time'))
        
        # Calculate typical price and volume
        typical_price = self._get_typical_price(candle_data)
        volume = candle_data.get('volume', 1)  # Default to 1 if no volume data
        
        # Update cumulative values
        self.cumulative_pv += typical_price * volume
        self.cumulative_volume += volume
        
        # Calculate VWAP
        if self.cumulative_volume > 0:
            vwap_value = self.cumulative_pv / self.cumulative_volume
            self.values.append(vwap_value)
            self.is_ready = True
            return vwap_value
        
        return None
    
    def reset(self):
        """Manually reset VWAP calculation"""
        self.cumulative_pv = 0
        self.cumulative_volume = 0
        self.last_reset_time = None
        self.values.clear()
        self.is_ready = False
    
    def get_cumulative_stats(self) -> Dict[str, float]:
        """Get current cumulative statistics"""
        return {
            'cumulative_pv': self.cumulative_pv,
            'cumulative_volume': self.cumulative_volume,
            'current_vwap': self.get_current_value()
        }


class MVWAP(BaseIndicator):
    """Moving VWAP - VWAP calculated over a rolling window"""
    
    def __init__(self, period: int = 20, name: Optional[str] = None):
        """
        Initialize Moving VWAP indicator
        
        Args:
            period: Number of periods to calculate VWAP over
            name: Optional custom name for the indicator
        """
        super().__init__(period, name or f"MVWAP_{period}")
        self.candle_buffer = deque(maxlen=period)
        self.color = "#9B59B6"  # Purple color for MVWAP
    
    def _get_typical_price(self, candle_data: Dict) -> float:
        """Calculate typical price (HLC/3)"""
        high = candle_data.get('high', candle_data.get('close'))
        low = candle_data.get('low', candle_data.get('close'))
        close = candle_data['close']
        
        return (high + low + close) / 3
    
    def calculate(self, candles: List[Dict]) -> Optional[float]:
        """Calculate Moving VWAP from a list of candles"""
        if len(candles) < self.period:
            return None
        
        recent_candles = candles[-self.period:]
        cumulative_pv = 0
        cumulative_volume = 0
        
        for candle in recent_candles:
            typical_price = self._get_typical_price(candle)
            volume = candle.get('volume', 1)
            
            cumulative_pv += typical_price * volume
            cumulative_volume += volume
        
        if cumulative_volume == 0:
            return None
        
        return cumulative_pv / cumulative_volume
    
    def update(self, candle_data: Dict) -> Optional[float]:
        """Update Moving VWAP with new candle data"""
        self.candle_buffer.append(candle_data)
        
        if len(self.candle_buffer) >= self.period:
            cumulative_pv = 0
            cumulative_volume = 0
            
            for candle in self.candle_buffer:
                typical_price = self._get_typical_price(candle)
                volume = candle.get('volume', 1)
                
                cumulative_pv += typical_price * volume
                cumulative_volume += volume
            
            if cumulative_volume > 0:
                mvwap_value = cumulative_pv / cumulative_volume
                self.values.append(mvwap_value)
                self.is_ready = True
                return mvwap_value
        
        return None