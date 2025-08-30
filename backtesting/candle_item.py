import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore

class CandlestickItem(pg.GraphicsObject):
    """Custom candlestick chart implementation for PyQtGraph"""
    
    def __init__(self, pen_bull=None, brush_bull=None, pen_bear=None, brush_bear=None):
        pg.GraphicsObject.__init__(self)
        
        # Default styling
        self.pen_bull = pen_bull or pg.mkPen(color='#00ff88', width=1)
        self.brush_bull = brush_bull or pg.mkBrush(color='#00ff88')
        self.pen_bear = pen_bear or pg.mkPen(color='#ff4444', width=1) 
        self.brush_bear = brush_bear or pg.mkBrush(color='#ff4444')
        
        # Wick pen (thinner line for high/low wicks)
        self.wick_pen_bull = pg.mkPen(color='#00ff88', width=1)
        self.wick_pen_bear = pg.mkPen(color='#ff4444', width=1)
        
        # Use _ohlc_data instead of data to avoid conflict
        self._ohlc_data = np.array([])
        self.candle_width = 0.6  # Width of candle bodies relative to time spacing
        
    def setOHLCData(self, data):
        """
        Set OHLC data for candlesticks
        data: numpy array with columns [timestamp, open, close, low, high]
        """
        self._ohlc_data = np.array(data)
        self.informViewBoundsChanged()
        self.update()
        
    def dataBounds(self, ax, frac=1.0, orthoRange=None):
        """Return the bounding box of the data"""
        if self._ohlc_data.size == 0:
            return (None, None)
            
        if ax == 0:  # x-axis (time)
            return (self._ohlc_data[:, 0].min(), self._ohlc_data[:, 0].max())
        elif ax == 1:  # y-axis (price)
            return (self._ohlc_data[:, 3].min(), self._ohlc_data[:, 4].max())  # low to high
        
    def boundingRect(self):
        """Return the bounding rectangle of the item"""
        if self._ohlc_data.size == 0:
            return QtCore.QRectF()
            
        xmin, xmax = self._ohlc_data[:, 0].min(), self._ohlc_data[:, 0].max()
        ymin, ymax = self._ohlc_data[:, 3].min(), self._ohlc_data[:, 4].max()  # low to high
        
        # Add some padding
        padding_x = (xmax - xmin) * 0.02
        padding_y = (ymax - ymin) * 0.02
        
        return QtCore.QRectF(xmin - padding_x, ymin - padding_y, 
                           (xmax - xmin) + 2*padding_x, (ymax - ymin) + 2*padding_y)
    
    def paint(self, painter, option, widget=None):
        """Paint the candlesticks"""
        if self._ohlc_data.size == 0 or painter is None:
            return
            
        # Get the visible range from the view
        viewbox = self.getViewBox()
        if viewbox is None:
            return
            
        view_range = viewbox.viewRange()
        x_range = view_range[0]
        
        # Filter data to visible range for performance
        visible_mask = (self._ohlc_data[:, 0] >= x_range[0]) & (self._ohlc_data[:, 0] <= x_range[1])
        visible_data = self._ohlc_data[visible_mask]
        
        if len(visible_data) == 0:
            return
            
        # Calculate candle width based on time spacing
        if len(visible_data) > 1:
            time_diff = np.median(np.diff(visible_data[:, 0]))
            candle_width = time_diff * self.candle_width
        else:
            candle_width = 1
            
        # Draw each candle
        for row in visible_data:
            timestamp, open_price, close_price, low_price, high_price = row
            
            # Determine if bullish or bearish
            is_bullish = close_price >= open_price
            
            # Select colors
            if is_bullish:
                pen = self.pen_bull
                brush = self.brush_bull
                wick_pen = self.wick_pen_bull
            else:
                pen = self.pen_bear
                brush = self.brush_bear
                wick_pen = self.wick_pen_bear
            
            # Draw wick (high-low line)
            painter.setPen(wick_pen)
            wick_line = QtCore.QLineF(
                float(timestamp), float(low_price),
                float(timestamp), float(high_price)
            )

            painter.drawLine(wick_line)
            
            # Draw candle body (open-close rectangle)
            painter.setPen(pen)
            painter.setBrush(brush)
            
            # Calculate body rectangle
            body_top = max(open_price, close_price)
            body_bottom = min(open_price, close_price)
            body_height = body_top - body_bottom
            
            # Handle doji candles (open == close)
            if body_height == 0:
                body_height = (high_price - low_price) * 0.02  # Small body for doji
                body_bottom = open_price - body_height / 2
                body_top = open_price + body_height / 2
            
            body_rect = QtCore.QRectF(
                float(timestamp - candle_width/2),
                float(body_bottom),
                float(candle_width),
                float(body_height)
            )

            painter.drawRect(body_rect)

class HollowCandlestickItem(CandlestickItem):
    """Hollow candlestick variant"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.brush_bull = pg.mkBrush(color=(0, 255, 136, 0)) 
        self.brush_bear = pg.mkBrush(color='#ff4444')     