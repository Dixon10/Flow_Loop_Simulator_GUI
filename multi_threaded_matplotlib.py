import os.path
import threading
from collections import deque
from queue import Queue
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import serial
import time
import csv
# ======================
# CONFIG
# ======================
PORT = "COM3"
BAUD = 115200
TIMEOUT = 0.005

WINDOW_SIZE = 100
LOGGING_SIZE = 200 # Log Every 20 Seconds
PLOT_INTERVAL = 120   # ms

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

#Queues
x_data_queue = Queue(maxsize=WINDOW_SIZE)

water_flow_queue = Queue(maxsize=WINDOW_SIZE)
electrolyte_flow_queue = Queue(maxsize=WINDOW_SIZE)
glucose_flow_queue = Queue(maxsize=WINDOW_SIZE)
mixture_ph_queue = Queue(maxsize=WINDOW_SIZE)
mixture_tds_queue = Queue(maxsize=WINDOW_SIZE)
mixture_turbidity_queue = Queue(maxsize=WINDOW_SIZE)

log_header = ['Time(s)', 'electrolyte_flow', 'glucose_flow', 'mixture_ph', 'mixture_tds', 'mixture_turbidity']
log_buffer = []
first_log = True
log_number = 0
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
    "Water Flow",
    "Electrolyte Flow",
    "Glucose Flow",
    "Mixture pH",
    "Mixture TDS",
    "Mixture Turbidity"
]

for p, t in zip(plots, titles):
    p.clear()
    p.set_title(t)
    p.set_xlabel("Time")
    p.set_ylabel("Value")
    p.grid(True)

water_line, = water_plot.plot([],[], "-o", markersize=2)
electrolyte_line, = electrolyte_plot.plot([],[], "-o", markersize=2)
glucose_line, = glucose_plot.plot([],[], "-o", markersize=2)
ph_line, = ph_plot.plot([],[], "-o", markersize=2)
tds_line, = tds_plot.plot([],[], "-o", markersize=2)
turb_line, = turb_plot.plot([],[], "-o", markersize=2)

lines = [
    water_line,
    electrolyte_line,
    glucose_line,
    ph_line,
    tds_line,
    turb_line
]

queues = [
    water_flow_queue,
    electrolyte_flow_queue,
    glucose_flow_queue,
    mixture_ph_queue,
    mixture_tds_queue,
    mixture_turbidity_queue
]

deques = [
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

            if not x_data_queue.full():
                x_data_queue.put(vals[0])
                water_flow_queue.put(vals[1])
                electrolyte_flow_queue.put(vals[2])
                glucose_flow_queue.put(vals[3])
                mixture_ph_queue.put(vals[4])
                mixture_tds_queue.put(vals[5])
                mixture_turbidity_queue.put(vals[6])

            if x_data_queue.full():
                print("error")
            log_buffer.append(vals)
            if len(log_buffer) > 0.95 * LOGGING_SIZE:
                threading.Thread(target=log).start()
        except Exception as e:
            print("parse error:", e)


# ======================
# ANIMATION
# ======================
def animate(frame):
    #print("bytes waiting:", ser.in_waiting)

    #no new data, just return
    if x_data_queue.empty():
        return lines
    else:
        while not x_data_queue.empty():
            x_data_deque.append(x_data_queue.get())

    # remove all queue elements to add to dequeue for moving window
    for queue, deque in zip(queues, deques):
        while not queue.empty():
            deque.append(queue.get())

    for line, deque in zip(lines, deques):
        line.set_data(x_data_deque, deque)

    xmin = x_data_deque[0]
    xmax = x_data_deque[-1]

    if xmin == xmax:
        xmax = xmin + 1

    for plot in plots:
        plot.set_xlim(xmin, xmax)
        plot.relim()
        plot.autoscale_view(scalex=False, scaley=True)

    print(f"xdata: {list(x_data_deque)}")
    print(f"xdata: {list(water_flow_deque)}")
    return lines


# ======================
# LOGGING
# ======================
def log():
    # start a new log if app has just started
    global log_number
    global first_log
    if first_log:
        while os.path.exists(f"Flow-Sim-Data-Log-{log_number}.csv"):
            log_number += 1
        first_log = False

    log_file = f"Flow-Sim-Data-Log-{log_number}.csv"
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
    interval=PLOT_INTERVAL,
    blit=False,
    cache_frame_data=False
)

plt.tight_layout()
plt.show()