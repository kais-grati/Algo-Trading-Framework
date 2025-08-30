from pyqtgraph import AxisItem
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class TimeAxisItem(AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).strftime("%H:%M:%S") for value in values]

@dataclass
class PlotData:
    """Data structure for sending comprehensive plotting information."""
    def __init__(self, stats, candle, recent_events=None, current_position=None, overlay_indicator_data=None, seperate_chart_indicator_data=None):
        self.stats = stats
        self.candle = candle
        self.recent_events = recent_events or []
        self.current_position = current_position
        self.overlay_indicator = overlay_indicator_data or {}
        self.seperate_chart_indicator = seperate_chart_indicator_data or {}

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
            'current_position': self.current_position,
            'overlay_indicator': self.overlay_indicator,
            'seperate_chart_indicator': self.seperate_chart_indicator
        }
    
    def __str__(self):
        return f"PlotData(stats={self.stats}, candle={self.candle}, recent_events={self.recent_events}, current_position={self.current_position}, overlay_indicator={self.overlay_indicator}, seperate_chart_indicator={self.seperate_chart_indicator})"
    
class ChartType(Enum):
    CANDLESTICK = 1
    HOLLOW_CANDLESTICK = 2
    LINE = 3
