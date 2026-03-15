import threading
import serial
import serial.tools.list_ports
import time
from enum import Enum

class Serial_Man_State(Enum):
    CLEAR_ON_START = 0
    CONNECTING_TO_DEVICE = 1
    PACKET_HANDLING = 2
    ERROR = 3

class Connection_State(Enum):
    CONNECTED = 0
    DISCONNECTED = 1
    DEVICE_BUSY = 2

class Warning_State(Enum):
    TOO_LOW = 0
    GOOD = 1
    TOO_HIGH = 2

class System_SM_state(Enum):
    IDLE = 0
    CALIBRATING = 1
    RUNNING = 2
    ERROR = 3
class SerialManager:

    CONNECTION_RETRY_INTERVAL = 0.1     # .1s

    def __init__(self, plot_queue, log_queue, datalogger):

        self.plot_queue = plot_queue
        self.log_queue = log_queue
        # Serial Variables
        self.serial_port = None
        self.serial_manager_state = Serial_Man_State.CLEAR_ON_START

        # Connection Variables
        self.connection_last_retry = 0
        self.connection_status = Connection_State.DISCONNECTED
        
        # Micro Variables
        self.micro_start_time = None
        self.running = True
        self.micro_state_machine_running = None
        self.send_stop_on_reconnect = False

        # App Objects
        self.logger = datalogger

        # GUI Params
        self.enable_start_btn = False
        self.enable_stop_btn = False

        self.start_button_pushed = False
        self.stop_button_pushed  = False

        self.plotting_active = False
    def start(self):
        threading.Thread(target=self.worker, daemon=True).start()

    def _connect_device(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "Arduino" in port.description or "STMicroelectronics" in port.description:
                try:
                    serial_port = serial.Serial(port.device, 115200, timeout=0.15)
                    return serial_port
                except serial.SerialException:
                    print("Device found but busy")

        return None
    
    def _process_data_packet(self,raw):

            try:
                line = raw.decode("utf-8", errors="ignore").strip()
            except:
                return None

            # Reject anything that doesn't have "S" at the start
            if not line.startswith("S,"):
                return None

            parts = line.split(",")
            parts = parts[1:]      # Removes the S

            if len(parts) < 7:
                return None

            try:
                vals = [float(p) for p in parts[:7]]
                vals.extend(int(p) for p in parts[7:])
            except ValueError:
                return None

            if self.micro_start_time is None:
                self.micro_start_time = vals[0]
            vals[0] = (vals[0] - self.micro_start_time)/1000

            return vals
    def write_to_micro(self):
        if self.send_stop_on_reconnect:
            self.serial_port.write(b"Stop\n")
            self.send_stop_on_reconnect = False
            return

        if self.start_button_pushed:
            self.serial_port.write(b"R")          # Run State Machine
            self.micro_state_machine_running = True
            self.start_button_pushed = False

        elif self.stop_button_pushed:
            self.serial_port.write(b"S")          # Stop State Machine
            self.micro_state_machine_running = False
            self.stop_button_pushed = False
    def worker(self):
        while self.running:
            match self.serial_manager_state:
                case Serial_Man_State.CLEAR_ON_START:
                    self.start_button_pushed = False
                    self.stop_button_pushed = False
                    self.enable_start_btn = False
                    self.enable_stop_btn = False

                    self.plotting_active = False
                    self.logger.stop()

                    # empty queues from previous run
                    while not self.plot_queue.empty():
                        self.plot_queue.get()
                    while not self.log_queue.empty():
                        self.log_queue.get()

                    self.micro_start_time = None
                    self.micro_state_machine_running = False
                    self.connection_status = Connection_State.DISCONNECTED
                    self.serial_manager_state = Serial_Man_State.CONNECTING_TO_DEVICE
                case Serial_Man_State.CONNECTING_TO_DEVICE:
                    current_time = time.perf_counter()

                    if current_time - self.connection_last_retry > self.CONNECTION_RETRY_INTERVAL:
                        self.connection_last_retry = current_time
                        self.serial_port = self._connect_device()

                        if self.serial_port:
                            print("Connected")
                            self.connection_status = Connection_State.CONNECTED
                            self.enable_start_btn = True
                            self.enable_stop_btn = False

                            time.sleep(0.1) # delay to prevent data alignment issues from reset_input_buffer()
                            self.serial_port.reset_input_buffer()
                            self.serial_port.reset_output_buffer()
                            self.plotting_active = True
                            self.logger.start()

                            self.serial_manager_state = Serial_Man_State.PACKET_HANDLING
                case Serial_Man_State.PACKET_HANDLING:
                    self.write_to_micro()

                    try:
                        raw_data_packet = self.serial_port.readline()

                    except Exception as e:
                        print("serial read error:", e)
                        self.serial_manager_state = Serial_Man_State.ERROR

                    if not raw_data_packet:
                        continue

                    parsed_packet = self._process_data_packet(raw_data_packet)
                    
                    if parsed_packet is None:
                        continue

                    if not self.plot_queue.full():
                        self.plot_queue.put(parsed_packet)

                    if not self.log_queue.full():
                        self.log_queue.put(parsed_packet)

                case Serial_Man_State.ERROR:
                    # Record Error & try to Reinitialize
                    print("Error Reading From Device, Attempting to Re-Connect")
                    self.send_stop_on_reconnect = True
                    self.serial_manager_state = Serial_Man_State.CLEAR_ON_START
            time.sleep(0.02)