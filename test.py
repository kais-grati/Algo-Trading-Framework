from multiprocessing import Process
import sys
import time
from PyQt5.QtWidgets import QApplication, QLabel

def run_qt_app():
    app = QApplication(sys.argv)
    label = QLabel("Hello from PyQt in another process!")
    label.resize(300, 100)
    label.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    # Start PyQt in a separate process
    p = Process(target=run_qt_app)
    p.daemon = False  # make sure the GUI lives independently
    p.start()

    # Main process loop continues
    try:
        while True:
            print("Main process is still running...")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Main loop stopped.")

