#State Imports
from enum import Enum

#Serial Imports
import serial
import serial.tools.list_ports
import time

# State Variables
class State(Enum):
    INIT = 0
    IDLE = 1
    RUNNING = 2
    ERROR = 3

state = State.INIT

#Serial Logic
class Connection_State(Enum):
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    DEVICE_BUSY = 3
ports = None
ser = None
connection_last_retry = 0
connection_retry_interval = 0.1 # 100 ms
connection_timeout = 1.0 #1 second
start_time_no_arduino = time.perf_counter()
arduino_found = False
connection_status = Connection_State.CONNECTING


def connect_device():
    ports = serial.tools.list_ports.comports()
    for port in ports:

        if "Arduino" in port.description or "STMicroelectronics" in port.description:
            try:
                # port.device = COM#
                serial_port = serial.Serial(port.device, 115200, timeout=1)
                print("Connected:", port.device)
                return serial_port
            except serial.SerialException:
                print("Device found but busy")

    return None

while True:
    # Allow for logs to be opened simulatenously to logging live data
    match state:
        case State.INIT:
            current_time = time.perf_counter()

            if current_time - connection_last_retry > connection_retry_interval:
                connection_last_retry = current_time
                ser = connect_device()

                if ser:
                    arduino_found = True
                    connection_status = Connection_State.CONNECTED
                    state = State.IDLE
                else:
                    arduino_found = False

            # 5 seconds have past and arduino has not been found
            if (arduino_found == False) and (time.perf_counter() - start_time_no_arduino) > 5:
                print("arduino not found")
                connection_status = Connection_State.DISCONNECTED
        case State.IDLE:
            # Enable Both Stop/Start Button
            # Wait for Start Button to be pushed
            state = State.RUNNING
        case State.RUNNING:
            try:
                packet = ser.readline()
            except:
                state = State.ERROR
            packet_formatted = packet.decode().strip()
            print(packet_formatted)
        case State.ERROR:
            # Record Error & try to Reinitialize
            print("Error Reading From Device, Attempting to Re-Connect")
            start_time_no_arduino = time.perf_counter()
            connection_status = Connection_State.CONNECTING
            state = State.INIT
    time.sleep(0.01)