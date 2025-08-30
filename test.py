import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from backtesting.candle_item import CandlestickItem   # your class file

class StreamingCandlestickDemo(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Streaming Candlestick Demo")
        self.resize(1000, 600)

        # Central widget with Plot
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        self.plot_widget.showGrid(x=True, y=True)

        # Add candlestick item
        self.candlestick_item = CandlestickItem()
        self.plot_widget.addItem(self.candlestick_item)

        # Storage for OHLC data
        self.n_candles = 60
        self.ohlc_data = self.generate_initial_data(self.n_candles)
        self.candlestick_item.setOHLCData(self.ohlc_data)

        # Setup timer to stream new data
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.add_new_candle)
        self.timer.start(1000)  # every 1s

    def generate_initial_data(self, n):
        """Generate initial fake OHLC data"""
        x = np.arange(n)
        prices = np.cumsum(np.random.normal(0, 1, n)) + 100
        opens = prices
        closes = opens + np.random.normal(0, 1, n)
        lows = np.minimum(opens, closes) - np.random.uniform(0.5, 1.5, n)
        highs = np.maximum(opens, closes) + np.random.uniform(0.5, 1.5, n)
        return np.column_stack([x, opens, closes, lows, highs])

    def add_new_candle(self):
        """Simulate new candle and update chart"""
        last_time = self.ohlc_data[-1, 0]
        last_close = self.ohlc_data[-1, 2]

        new_time = last_time + 1
        open_price = last_close
        close_price = open_price + np.random.normal(0, 1)
        low_price = min(open_price, close_price) - np.random.uniform(0.5, 1.0)
        high_price = max(open_price, close_price) + np.random.uniform(0.5, 1.0)

        new_candle = np.array([[new_time, open_price, close_price, low_price, high_price]])
        self.ohlc_data = np.vstack([self.ohlc_data, new_candle])

        # Keep only last N candles visible
        if len(self.ohlc_data) > self.n_candles:
            self.ohlc_data = self.ohlc_data[-self.n_candles:]

        self.candlestick_item.setOHLCData(self.ohlc_data)

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = StreamingCandlestickDemo()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
