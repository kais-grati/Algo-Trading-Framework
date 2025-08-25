import sys
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout
)
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore


class TradingDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Dashboard")
        self.resize(1200, 800)

        # ---- Central Chart ----
        self.chart = pg.PlotWidget()
        self.setCentralWidget(self.chart)
        self.curve = self.chart.plot(pen='y')
        self.data = []

        # ---- Positions Table (Docked Bottom) ----
        self.positions_table = QTableWidget(5, 3)  # 5 rows, 3 columns
        self.positions_table.setHorizontalHeaderLabels(["Symbol", "Qty", "PnL"])
        dock_positions = QDockWidget("Open Positions", self)
        dock_positions.setWidget(self.positions_table)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock_positions)

        # ---- Trade Log (Docked Right) ----
        self.trade_log = QTableWidget(10, 4)  # 10 rows, 4 columns
        self.trade_log.setHorizontalHeaderLabels(["Time", "Symbol", "Side", "Price"])
        dock_trades = QDockWidget("Trade Log", self)
        dock_trades.setWidget(self.trade_log)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_trades)

        # ---- Timer for Live Updating ----
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_chart)
        self.timer.start(500)  # update every 500ms

    def update_chart(self):
        """Simulate live price updates"""
        if len(self.data) > 100:
            self.data = self.data[1:]
        self.data.append(random.uniform(100, 110))  # fake price data
        self.curve.setData(self.data)

        # Randomly update PnL
        for row in range(self.positions_table.rowCount()):
            self.positions_table.setItem(row, 2, QTableWidgetItem(f"{random.uniform(-50, 50):.2f}"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TradingDashboard()
    win.show()
    sys.exit(app.exec_())
