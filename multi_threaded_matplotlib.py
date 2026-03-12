import os.path
import threading
from collections import deque
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
LOGGING_SIZE = 200 # Log Every 2 Seconds
PLOT_INTERVAL = 150   # ms

# ======================
# BUFFERS
# ======================
x_data = deque(maxlen=WINDOW_SIZE)

water_flow = deque(maxlen=WINDOW_SIZE)
electrolyte_flow = deque(maxlen=WINDOW_SIZE)
glucose_flow = deque(maxlen=WINDOW_SIZE)
mixture_ph = deque(maxlen=WINDOW_SIZE)
mixture_tds = deque(maxlen=WINDOW_SIZE)
mixture_turbidity = deque(maxlen=WINDOW_SIZE)

log_header = ['Time(s)', 'electrolyte_flow', 'glucose_flow', 'mixture_ph', 'mixture_tds', 'mixture_turbidity']
log_buffer = []
first_log = True
log_number = 0
file_exists = os.path.exists("data.csv")
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
    p.set_title(t)
    p.set_xlabel("Time")
    p.set_ylabel("Value")
    p.grid(True)

water_line, = water_plot.plot([],[])
electrolyte_line, = electrolyte_plot.plot([],[])
glucose_line, = glucose_plot.plot([],[])
ph_line, = ph_plot.plot([],[])
tds_line, = tds_plot.plot([],[])
turb_line, = turb_plot.plot([],[])

lines = [
    water_line,
    electrolyte_line,
    glucose_line,
    ph_line,
    tds_line,
    turb_line
]

buffers = [
    water_flow,
    electrolyte_flow,
    glucose_flow,
    mixture_ph,
    mixture_tds,
    mixture_turbidity
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

            x_data.append(vals[0])
            water_flow.append(vals[1])
            electrolyte_flow.append(vals[2])
            glucose_flow.append(vals[3])
            mixture_ph.append(vals[4])
            mixture_tds.append(vals[5])
            mixture_turbidity.append(vals[6])

            log_buffer.append(vals)
            if len(log_buffer) > 0.9 * LOGGING_SIZE:
                threading.Thread(target=log).start()
        except Exception as e:
            print("parse error:", e)


# ======================
# ANIMATION
# ======================
def animate(frame):
    print("bytes waiting:", ser.in_waiting)
    if len(x_data) == 0:
        return lines

    for line, buf in zip(lines, buffers):
        line.set_data(x_data, buf)

    xmin = x_data[0]
    xmax = x_data[-1]

    if xmin == xmax:
        xmax = xmin + 1

    for plot in plots:
        plot.set_xlim(xmin, xmax)
        plot.relim()
        plot.autoscale_view(scalex=False, scaley=True)

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
    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(log_header)

        writer.writerows(log_buffer)
    log_buffer.clear()

# ======================
# START THREAD
# ======================
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