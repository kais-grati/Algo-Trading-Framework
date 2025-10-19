from collections import deque
from typing import Dict, List, Optional, Any, Union
from data import BaseCandle
from core.indicators import BaseIndicator, IndicatorValue
from dataclasses import dataclass

@dataclass
class IndicatorMeta:
    indicator: BaseIndicator
    plottable: bool = True
    separate_chart: bool = False

class BaseIndicatorManager:
    """Manages multiple indicators and handles updates"""
    
    def __init__(self):
        self.indicators: Dict[str, IndicatorMeta] = {}
        self.candle_history = deque(maxlen=1000)
    
    def add_indicator(
        self,
        indicator: BaseIndicator,
        plottable: bool = True,
        separate_chart: bool = False,
        color: str = "#FFFFFF",
        alias: Optional[str] = None
    ) -> str:
        key = alias or indicator.name

        if isinstance(indicator, BaseIndicator) and color:
            indicator.color = color


        self.indicators[key] = IndicatorMeta(
            indicator=indicator,
            plottable=plottable,
            separate_chart=separate_chart
        )

        # Initialize with history
        for candle_data in self.candle_history:
            indicator.update(candle_data)

        return key

    
    def remove_indicator(self, key: str):
        """Remove an indicator"""
        if key in self.indicators:
            del self.indicators[key]
    
    def update_all(self, candle: BaseCandle) -> Dict[str, Any]:
        """Update all indicators with new candle data"""
        candle_data = {
            'timestamp': candle.timestamp,
            'open': candle.open,
            'high': candle.high,
            'low': candle.low,
            'close': candle.close,
            'volume': getattr(candle, 'volume', 0)
        }
        
        self.candle_history.append(candle_data)
        
        results = {}
        for key, meta in self.indicators.items():
            ind = meta.indicator
            try:
                value = ind.update(candle_data)
                if value is not None:
                    results[key] = value
            except Exception as e:
                print(f"Error updating indicator {key}: {e}")

        
        return results
    
    def get_plottable_indicators(self, separate_chart: Optional[bool] = None):
        """Return plottable indicators, optionally filtered by chart type"""
        result = {}
        for key, meta in self.indicators.items():
            if meta.plottable and (separate_chart is None or meta.separate_chart == separate_chart):
                result[key] = meta.indicator
        return result
    

    def get_indicator(self, key: str) -> Optional[BaseIndicator]:
        """Get indicator by key"""
        meta = self.indicators.get(key)
        return meta.indicator if meta else None

    def get_value(self, key: str) -> Optional[Union[IndicatorValue, Any]]:
        """Get current value of an indicator"""
        indicator = self.get_indicator(key)
        return indicator.get_current_value()
    
    def get_values(self, key: str, n: Optional[int] = None) -> List[Any]:
        """Get historical values of an indicator"""
        indicator = self.get_indicator(key)
        return indicator.get_values(n)
    
    def is_ready(self, key: str) -> bool:
        """Check if indicator is ready (has enough data)"""
        indicator = self.get_indicator(key)
        return indicator.is_ready if indicator else False
    
    def get_all_current_values(self) -> Dict[str, Any]:
        """Get current values of all simple indicators"""
        results = {}
        for key, meta in self.indicators.items():
            if isinstance(meta.indicator, BaseIndicator):
                value = meta.indicator.get_current_value()
                if value is not None:
                    results[key] = value
        return results
    
