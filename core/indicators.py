from collections import deque
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class IndicatorValue:
    """Simple standardized indicator value for overlay indicators"""
    
    def __init__(self, value: Optional[float] = None, timestamp: Optional[Any] = None, 
                 color: Optional[str] = None, metadata: Optional[Dict] = None):
        self.value = value
        self.timestamp = timestamp
        self.color = color or "#FFFFFF"
        self.metadata = metadata or {}

EMPTY_VALUE = IndicatorValue()


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
        return self.values[-1] if self.values else EMPTY_VALUE
    
    def get_values(self, n: Optional[int] = None) -> List[IndicatorValue]:
        if n is None:
            return list(self.values)
        return list(self.values)[-n:] if len(self.values) >= n else list(self.values)



# A few implementations of classical indicators
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


class RSI(BaseIndicator):
    """Relative Strength Index (RSI) - momentum indicator"""

    def __init__(self, period: int = 14, source: str = 'close'):
        super().__init__(period, f"RSI_{period}")
        self.source = source
        self.gains = deque(maxlen=period)
        self.losses = deque(maxlen=period)
        self.avg_gain = None
        self.avg_loss = None
        self.prev_price = None
        self.color = "#9B59B6"
        self.chart_type = "oscillator"  # RSI is not an overlay indicator

    def _calculate_rsi(self, avg_gain: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def update(self, candle_data: Dict) -> Optional[IndicatorValue]:
        """Update RSI with a new candle"""
        price = candle_data[self.source]

        # Skip first candle (no previous)
        if self.prev_price is None:
            self.prev_price = price
            return None

        change = price - self.prev_price
        gain = max(change, 0)
        loss = abs(min(change, 0))

        self.gains.append(gain)
        self.losses.append(loss)
        self.prev_price = price

        # Compute initial averages
        if len(self.gains) < self.period:
            return None

        if self.avg_gain is None:
            self.avg_gain = sum(self.gains) / self.period
            self.avg_loss = sum(self.losses) / self.period
        else:
            # Wilder's smoothing method
            self.avg_gain = ((self.avg_gain * (self.period - 1)) + gain) / self.period
            self.avg_loss = ((self.avg_loss * (self.period - 1)) + loss) / self.period

        rsi_value = self._calculate_rsi(self.avg_gain, self.avg_loss)

        indicator_value = IndicatorValue(
            value=rsi_value,
            timestamp=candle_data.get('timestamp'),
            color=self.color,
            metadata={'period': self.period, 'source': self.source}
        )

        self.values.append(indicator_value)
        self.is_ready = True
        return indicator_value

    def calculate(self, candles: List[Dict]) -> Optional[IndicatorValue]:
        """Calculate RSI from historical candles"""
        if len(candles) < self.period + 1:
            return None

        prices = [c[self.source] for c in candles]
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]

        avg_gain = sum(gains[:self.period]) / self.period
        avg_loss = sum(losses[:self.period]) / self.period

        # Apply Wilder's smoothing for the rest
        for i in range(self.period, len(gains)):
            avg_gain = ((avg_gain * (self.period - 1)) + gains[i]) / self.period
            avg_loss = ((avg_loss * (self.period - 1)) + losses[i]) / self.period

        rsi_value = self._calculate_rsi(avg_gain, avg_loss)

        return IndicatorValue(
            value=rsi_value,
            color=self.color,
            metadata={'period': self.period, 'source': self.source}
        )
