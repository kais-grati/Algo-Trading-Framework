import threading
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

class EquityPlotter(threading.Thread):
    def __init__(self, backtester, stop_event, interval_ms: int = 100):
        super().__init__(daemon=True) 
        self.backtester = backtester
        self.stop_event = stop_event
        self.interval_ms = interval_ms

    def run(self):
        app = QtWidgets.QApplication([])

        # Window + plot
        win = pg.GraphicsLayoutWidget(show=True, title="Strategy Performance")
        plot = win.addPlot(title="Equity Curve")
        curve = plot.plot(pen='y')  

        equity_curve = []

        def update():
            equity = self.backtester.stats.total_pnl + self.backtester.stats.pnl
            equity_curve.append(equity)
            curve.setData(equity_curve)

            if self.stop_event.is_set():
                timer.stop()
                app.quit()
    
        # Timer for live updates
        timer = QtCore.QTimer()
        timer.timeout.connect(update)
        timer.start(self.interval_ms)

        app.exec_()
