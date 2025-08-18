from datetime import datetime
import pandas as pd

class BaseCandle():
    def __init__(self, timestamp: datetime, open: float, high: float, low: float, close: float, volume: float) -> None:
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

    def to_series(self) -> pd.Series:
        return pd.Series({'timestamp': self.timestamp,
                          'open': self.open,
                          'high': self.high,
                          'low': self.low,
                          'close': self.close,
                          'volume': self.volume
                          })
    
    def __str__(self) -> str:
        return f"Candle(timestamp={self.timestamp}, open={self.open}, high={self.high}, low={self.low}, close={self.close}, volume={self.volume})"