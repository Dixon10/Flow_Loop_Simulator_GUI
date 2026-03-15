import time
import os.path
import threading
import csv
from pathlib import Path
from datetime import datetime

class Logger:

    LOGS_DIR = Path("logs")
    LOG_HEADER = [
        'Time (s)',

        'Water Flow (mL/s)',
        'Electrolyte Flow (mL/s)',
        'Glucose Flow (mL/s)',
        'Mixture pH',
        'Mixture TDS (ppm)',
        'Mixture Turbidity (NTU)',

        'Water Warning',
        'Electrolyte Warning',
        'Glucose Warning',
        'pH Warning',
        'TDS Warning',
        'Turbidity Warning',

        'System State'
    ]
    LOG_THRESHOLD_PERCENT = 0.90

    def __init__(self, log_queue, log_size_max):
        self.log_queue = log_queue
        self.log_size_max = log_size_max
        self.log_list = []
        self.log_file = None
        self.new_log = None
        self.running = None

    def init_logger(self):
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.new_log = True
        self.running = True

    def start(self):
        self.init_logger()
        threading.Thread(target=self.worker, daemon=True).start()

    def stop(self):
        self.running = False

        if self.log_list:
            self.log_data()

    def log_data(self):
        if self.new_log:
            raw_time = datetime.now()
            log_timestamp = raw_time.strftime("_Date_%m-%d-%Y_Time_%H-%M-%S")
            self.log_file = f"{self.LOGS_DIR}/Sim Log {log_timestamp}.csv"
            self.new_log = False

        file_exists = os.path.exists(self.log_file)

        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow(self.LOG_HEADER)

            writer.writerows(self.log_list)
        self.log_list.clear()

    def worker(self):
        while self.running:
            packet = self.log_queue.get()
            self.log_list.append(packet)
            if len(self.log_list) > self.log_size_max * self.LOG_THRESHOLD_PERCENT:
                print("new log")
                self.log_data()

