import os.path
import threading
from collections import deque
from queue import Queue
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import serial
import time
import csv
from pathlib import Path
# ======================
# CONFIG
# ======================
PORT = "COM3"
BAUD = 115200
TIMEOUT = 0.005

WINDOW_SIZE = 200
LOGGING_SIZE_MAX = 200 # 200 Elements max = log every 20 seconds
PLOT_INTERVAL_ms = 150   # ms

# ======================
# BUFFERS
# ======================
#Deques
x_data_deque = deque(maxlen=WINDOW_SIZE)

water_flow_deque = deque(maxlen=WINDOW_SIZE)
electrolyte_flow_deque = deque(maxlen=WINDOW_SIZE)
glucose_flow_deque = deque(maxlen=WINDOW_SIZE)
mixture_ph_deque = deque(maxlen=WINDOW_SIZE)
mixture_tds_deque = deque(maxlen=WINDOW_SIZE)
mixture_turbidity_deque = deque(maxlen=WINDOW_SIZE)

# GUI Queue
gui_packet_queue = Queue(maxsize=WINDOW_SIZE)

# Log Queue & Log Variables
log_header = [
    'Time (s)',
    'Electrolyte Flow (mL/s)',
    'Glucose Flow (mL/s)',
    'Mixture pH',
    'Mixture TDS (ppm)',
    'Mixture Turbidity (NTU)'
]
log_buffer = [] #basically a queue, but csv module wants it as a list
first_log = True
log_number = 0
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# ======================
# SERIAL
# ======================
ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
micro_offset_start_time = None
# ======================
# PLOT SETUP
# ======================
fig, ax = plt.subplots(2, 3, figsize=(12,6))

water_plot = ax[0,0]
electrolyte_plot = ax[0,1]
glucose_plot = ax[0,2]
ph_plot = ax[1,0]
tds_plot = ax[1,1]
turb_plot = ax[1,2]

plots = [
    water_plot,
    electrolyte_plot,
    glucose_plot,
    ph_plot,
    tds_plot,
    turb_plot
]

titles = [
    "Water Flow vs Time",
    "Electrolyte Flow vs Time",
    "Glucose Flow vs Time",
    "Mixture pH vs Time",
    "Mixture TDS vs Time",
    "Mixture Turbidity vs Time"
]

y_axises = [
    'Water Flow (mL/s)',
    'Electrolyte Flow (mL/s)',
    'Glucose Flow (mL/s)',
    'Mixture pH',
    'Mixture TDS (ppm)',
    'Mixture Turbidity (NTU)'
]

units = [
    '(mL/s)',
    '(mL/s)',
    '(mL/s)',
    '(pH)',
    '(ppm)',
    '(NTU)'
]

for p, t, y in zip(plots, titles, y_axises):
    p.clear()
    p.set_title(t)
    p.set_xlabel("Time(s)")
    p.set_ylabel(y)
    p.grid(True)

water_line, = water_plot.plot([],[], "-o", markersize=2)
electrolyte_line, = electrolyte_plot.plot([],[], "-o", markersize=2)
glucose_line, = glucose_plot.plot([],[], "-o", markersize=2)
ph_line, = ph_plot.plot([],[], "-o", markersize=2)
tds_line, = tds_plot.plot([],[], "-o", markersize=2)
turb_line, = turb_plot.plot([],[], "-o", markersize=2)

value_texts = []
for plot in plots:
    txt = plot.text(
        0.02, 0.95, "",
        transform=plot.transAxes,
        verticalalignment='top',
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.7)
    )
    value_texts.append(txt)

lines = [
    water_line,
    electrolyte_line,
    glucose_line,
    ph_line,
    tds_line,
    turb_line
]

deques = [
    x_data_deque,
    water_flow_deque,
    electrolyte_flow_deque,
    glucose_flow_deque,
    mixture_ph_deque,
    mixture_tds_deque,
    mixture_turbidity_deque
]
# ======================
# SERIAL THREAD
# ======================
def serial_worker():

    while True:
        global micro_offset_start_time
        raw = ser.readline()

        if not raw:
            continue

        try:

            line = raw.decode().strip()
            parts = line.split(",")

            if len(parts) < 7:
                continue

            vals = [float(p) for p in parts[:7]]

            if micro_offset_start_time is None:
                micro_offset_start_time = vals[0]
            vals[0] = (vals[0] - micro_offset_start_time)/1000

            if not gui_packet_queue.full():
                gui_packet_queue.put(vals)
            
            log_buffer.append(vals)
            if len(log_buffer) > 0.95 * LOGGING_SIZE_MAX:
                threading.Thread(target=log).start()
        except Exception as e:
            print("parse error:", e)


# ======================
# ANIMATION
# ======================
def animate(frame):
    #print("bytes waiting:", ser.in_waiting)

    #no new flow sim data, just return
    if gui_packet_queue.empty():
        return lines

    # remove all queue elements to add to dequeue for moving window
    while not gui_packet_queue.empty():
        packet = gui_packet_queue.get()
        i = 0
        for deque in deques:
            deque.append(packet[i])
            i += 1

    for line, data_deque in zip(lines, deques[1:]):
        line.set_data(x_data_deque, data_deque)

    xmin = x_data_deque[0]
    xmax = x_data_deque[-1]

    if xmin == xmax:
        xmax = xmin + 1

    for plot in plots:
        plot.set_xlim(xmin, xmax)
        plot.relim()
        plot.autoscale_view(scalex=False, scaley=True)

    for txt, data_deque, unit in zip(value_texts, deques[1:], units):
        if data_deque:
            txt.set_text(f"{data_deque[-1]:.2f} {unit}")

    return lines + value_texts


# ======================
# LOGGING
# ======================
def log():
    # start a new log if app has just started
    global log_number
    global first_log
    if first_log:
        while os.path.exists(f"{logs_dir}/Flow-Sim-Data-Log-{log_number}.csv"):
            log_number += 1
        first_log = False

    log_file = f"{logs_dir}/Flow-Sim-Data-Log-{log_number}.csv"
    file_exists = os.path.exists(log_file)
    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(log_header)

        writer.writerows(log_buffer)
    log_buffer.clear()

# ======================
# START THREAD
# ======================
ser.reset_input_buffer()
ser.reset_output_buffer()
thread = threading.Thread(target=serial_worker, daemon=True)
thread.start()

# ======================
# START ANIMATION
# ======================
ani = animation.FuncAnimation(
    fig,
    animate,
    interval=PLOT_INTERVAL_ms,
    blit=False,
    cache_frame_data=False
)

plt.tight_layout()
plt.show()