from queue import Queue
from serial_manager import SerialManager
from logger import Logger
import time
from gui import TkinterGUI
# from plotter import Plotter

WINDOW_SIZE = 150
LOGGING_SIZE_MAX = 100

def main():

    plot_queue = Queue(maxsize=WINDOW_SIZE)
    log_queue = Queue(maxsize=LOGGING_SIZE_MAX)

    data_logger = Logger(log_queue, LOGGING_SIZE_MAX)
    serial_mgr = SerialManager(plot_queue, log_queue, data_logger)

    serial_mgr.start()

    gui = TkinterGUI(plot_queue, data_logger, serial_mgr, WINDOW_SIZE)
    gui.run()

if __name__ == "__main__":
    main()