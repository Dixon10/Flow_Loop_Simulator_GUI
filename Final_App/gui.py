import ttkbootstrap as tb
from ttkbootstrap.constants import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib as mpl
from serial_manager import Connection_State
from serial_manager import Serial_Man_State
from serial_manager import Warning_State
from serial_manager import System_SM_state
from collections import deque
from matplotlib import style

class TkinterGUI:
    TITLES = [
        "Water Flow vs Time",
        "Electrolyte Flow vs Time",
        "Glucose Flow vs Time",
        "Mixture pH vs Time",
        "Mixture TDS vs Time",
        "Mixture Turbidity vs Time"
    ]

    Y_AXISES = [
        'Water Flow (mL/s)',
        'Electrolyte Flow (mL/s)',
        'Glucose Flow (mL/s)',
        'Mixture pH',
        'Mixture TDS (ppm)',
        'Mixture Turbidity (NTU)'
    ]

    UNITS = [
        '(mL/s)',
        '(mL/s)',
        '(mL/s)',
        '(pH)',
        '(ppm)',
        '(NTU)'
    ]

    GUI_REFRESH_PERIOD = 170
    def __init__(self, plot_queue, data_logger, serial_manager, WINDOW_SIZE):
        self.data_logger = data_logger
        self.serial_manager = serial_manager

        self.root = tb.Window(themename="superhero")
        self.style = tb.Style()

        self.notebook = tb.Notebook(self.root)
        self.live_data_window = tb.Frame(self.notebook)
        self.logging_window = tb.Frame(self.notebook)

        self.separator = None
        # Buttons
        self.start_button = None
        self.stop_button = None

        # Status indicators
        self.water_flow_label = None
        self.water_flow_status = None

        self.electrolyte_flow_label = None
        self.electrolyte_flow_status = None

        self.glucose_flow_label = None
        self.glucose_flow_status = None

        self.pH_label = None
        self.pH_status = None

        self.TDS_label = None
        self.TDS_status = None

        self.turbidity_label = None
        self.turbidity_status = None

        self.warning_widgets = []

        self.device_label = None
        self.device_status = None

        self.system_state_label = None
        self.system_state_status = None

        # LED Legend
        self.legend_label = None

        self.legend_low_led = None
        self.legend_low_text = None

        self.legend_good_led = None
        self.legend_good_text = None

        self.legend_high_led = None
        self.legend_high_text = None

        # MatplotLib Params
        self.fig = None
        self.ax = None

        self.water_plot = None
        self.electrolyte_plot = None
        self.glucose_plot = None
        self.ph_plot = None
        self.tds_plot = None
        self.turb_plot = None
        self.plots = []

        self.water_line = None
        self.electrolyte_line = None
        self.glucose_line = None
        self.ph_line = None
        self.tds_line = None
        self.turb_line= None
        self.lines = []

        self.value_texts = []

        self.water_status_data = None
        self.electrolyte_status_data = None
        self.glucose_status_data = None
        self.ph_status_data = None
        self.tds_status_data = None
        self.turb_status_data = None
        self.statuses = []

        self.system_state_status_data = None

        self.last_plotting_active_state = False
        # Plot Data
        # packet queue
        self.plot_queue = plot_queue
        # deques
        self.x_data_deque = deque(maxlen=WINDOW_SIZE)
        self.water_flow_deque = deque(maxlen=WINDOW_SIZE)
        self.electrolyte_flow_deque = deque(maxlen=WINDOW_SIZE)
        self.glucose_flow_deque = deque(maxlen=WINDOW_SIZE)
        self.mixture_ph_deque = deque(maxlen=WINDOW_SIZE)
        self.mixture_tds_deque = deque(maxlen=WINDOW_SIZE)
        self.mixture_turbidity_deque = deque(maxlen=WINDOW_SIZE)
        self.deques = []
    def run(self):
        self.init_plots()
        self.init_tkinter_gui()
        self.root.after(self.GUI_REFRESH_PERIOD, self.gui_update_loop)
        self.root.mainloop()

    def init_plots(self):
        # Styling Text
        mpl.rcParams["font.weight"] = "bold"
        mpl.rcParams["axes.titleweight"] = "bold"
        mpl.rcParams["axes.labelweight"] = "bold"

        # Plots
        self.fig, self.ax = plt.subplots(2, 3, figsize=(12, 6))

        self.water_plot = self.ax[0, 0]
        self.electrolyte_plot = self.ax[0, 1]
        self.glucose_plot = self.ax[0, 2]
        self.ph_plot = self.ax[1, 0]
        self.tds_plot = self.ax[1, 1]
        self.turb_plot = self.ax[1, 2]

        self.plots = [
            self.water_plot,
            self.electrolyte_plot,
            self.glucose_plot,
            self.ph_plot,
            self.tds_plot,
            self.turb_plot
        ]

        for p, t, y in zip(self.plots, self.TITLES, self.Y_AXISES):
            p.clear()
            p.set_title(t)
            p.set_xlabel("Time(s)")
            p.set_ylabel(y)
            p.grid(True)

        # Styling Plots
        self.fig.subplots_adjust(hspace=0.35)
        self.fig.subplots_adjust(wspace=0.35)

        tkinter_background_color = self.style.colors.get("bg")
        self.fig.set_facecolor(tkinter_background_color)

        for a in self.ax.flatten():
            # Whitten Plots
            a.set_facecolor("white")

            # Whitten Text
            a.title.set_color("white")
            a.xaxis.label.set_color("white")
            a.yaxis.label.set_color("white")
            a.tick_params(colors="white")

            # Make the border visible on white
            for spine in a.spines.values():
                spine.set_edgecolor("white")

        # Lines
        self.water_line, = self.water_plot.plot([], [], "-o", markersize=2)
        self.electrolyte_line, = self.electrolyte_plot.plot([], [], "-o", markersize=2)
        self.glucose_line, = self.glucose_plot.plot([], [], "-o", markersize=2)
        self.ph_line, = self.ph_plot.plot([], [], "-o", markersize=2)
        self.tds_line, = self.tds_plot.plot([], [], "-o", markersize=2)
        self.turb_line, = self.turb_plot.plot([], [], "-o", markersize=2)

        self.lines = [
            self.water_line,
            self.electrolyte_line,
            self.glucose_line,
            self.ph_line,
            self.tds_line,
            self.turb_line
        ]

        # Current Value Text:
        self.value_texts = []
        for plot in self.plots:
            txt = plot.text(
                0.02, 0.95, "",
                transform=plot.transAxes,
                verticalalignment='top',
                fontsize=9,
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.7)
            )
            self.value_texts.append(txt)

        self.statuses = [
            self.water_status_data,
            self.electrolyte_status_data,
            self.glucose_status_data,
            self.ph_status_data,
            self.tds_status_data,
            self.turb_status_data
        ]

        self.deques = [
            self.x_data_deque,
            self.water_flow_deque,
            self.electrolyte_flow_deque,
            self.glucose_flow_deque,
            self.mixture_ph_deque,
            self.mixture_tds_deque,
            self.mixture_turbidity_deque

        ]
    def init_tkinter_gui(self):

        # Window Properties
        self.root.title("Flow Loop Simulator")
        self.root.geometry("1920x1080")

        # Style
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 18, "bold"))
        self.style.configure("success.TButton", font=("Segoe UI", 13, "bold"), padding=(30, 10))
        self.style.configure("danger.TButton", font=("Segoe UI", 13, "bold"), padding=(30, 10))

        # Notebook
        self.notebook.pack(expand=True, fill='both')

        # Button Row
        button_row = tb.Frame(self.live_data_window, padding=20)
        button_row.pack(fill="x", side="top")

        # Start / Stop Buttons
        self.start_button = tb.Button(button_row, text="Start", bootstyle="success", command=self.start_button_pressed)
        self.stop_button = tb.Button(button_row, text="Stop", bootstyle="danger", command=self.stop_button_pressed)

        # Water Flow
        self.water_flow_label = tb.Label(button_row, text="Water:", font=("Segoe UI", 13, "bold"), foreground="white")
        self.water_flow_status = tb.Label(button_row, text="●", font=("Segoe UI", 13, "bold"), foreground="white")

        # Electrolyte Flow
        self.electrolyte_flow_label = tb.Label(button_row, text="Electrolyte:", font=("Segoe UI", 13, "bold"), foreground="white")
        self.electrolyte_flow_status = tb.Label(button_row, text="●", font=("Segoe UI", 13, "bold"), foreground="white")

        # Glucose Flow
        self.glucose_flow_label = tb.Label(button_row, text="Glucose:", font=("Segoe UI", 13, "bold"), foreground="white")
        self.glucose_flow_status = tb.Label(button_row, text="●", font=("Segoe UI", 13, "bold"), foreground="white")

        # pH
        self.pH_label = tb.Label(button_row, text="pH:", font=("Segoe UI", 13, "bold"), foreground="white")
        self.pH_status = tb.Label(button_row, text="●", font=("Segoe UI", 13, "bold"), foreground="white")

        # TDS
        self.TDS_label = tb.Label(button_row, text="TDS:", font=("Segoe UI", 13, "bold"), foreground="white")
        self.TDS_status = tb.Label(button_row, text="●", font=("Segoe UI", 13, "bold"), foreground="white")

        # Turbidity
        self.turbidity_label = tb.Label(button_row, text="Turbidity:", font=("Segoe UI", 13, "bold"), foreground="white")
        self.turbidity_status = tb.Label(button_row, text="●", font=("Segoe UI", 13, "bold"), foreground="white")

        # Device Connection State
        self.device_label = tb.Label(button_row, text="Device:", font=("Segoe UI", 13, "bold"), foreground="white")
        self.device_status = tb.Label(button_row, text="Disconnected", font=("Segoe UI", 13, "bold"), foreground="white")

        # System State Machine State
        self.system_state_label = tb.Label(button_row, text="System State:", font=("Segoe UI", 13, "bold"), foreground="white")
        self.system_state_status = tb.Label(button_row, text="Idle", font=("Segoe UI", 13, "bold"), foreground="white")

        # Legend label
        self.legend_label = tb.Label(
            button_row,
            text="Legend:",
            font=("Segoe UI", 13, "bold"),
            foreground="white"
        )

        # Low
        self.legend_low_led = tb.Label(button_row, text="●", font=("Segoe UI", 13, "bold"), foreground="red")
        self.legend_low_text = tb.Label(button_row, text="Low", font=("Segoe UI", 13, "bold"), foreground="white")

        # Good
        self.legend_good_led = tb.Label(button_row, text="●", font=("Segoe UI", 13, "bold"), foreground="lime")
        self.legend_good_text = tb.Label(button_row, text="Good", font=("Segoe UI", 13, "bold"), foreground="white")

        # High
        self.legend_high_led = tb.Label(button_row, text="●", font=("Segoe UI", 13, "bold"), foreground="orange")
        self.legend_high_text = tb.Label(button_row, text="High", font=("Segoe UI", 13, "bold"), foreground="white")


        # Pack buttons
        self.start_button.pack(side="left", padx=10)
        self.stop_button.pack(side="left", padx=25)

        # Pack status indicators
        widgets = [
            self.water_flow_label, self.water_flow_status,
            self.electrolyte_flow_label, self.electrolyte_flow_status,
            self.glucose_flow_label, self.glucose_flow_status,
            self.pH_label, self.pH_status,
            self.TDS_label, self.TDS_status,
            self.turbidity_label, self.turbidity_status,
        ]

        self.warning_widgets = [
            self.water_flow_status,
            self.electrolyte_flow_status,
            self.glucose_flow_status,
            self.pH_status,
            self.TDS_status,
            self.turbidity_status,
        ]

        for w in widgets:
            w.pack(side="left", padx=8)

        self.device_label.pack(side="left", padx=(15,0))
        self.device_status.pack(side="left", padx=(2,15))

        self.system_state_label.pack(side="left", padx=(15, 0))
        self.system_state_status.pack(side="left", padx=(2, 15))

        self.legend_label.pack(side="left", padx=(30, 10))
        self.legend_low_led.pack(side="left", padx=(0, 2))
        self.legend_low_text.pack(side="left", padx=(0, 10))

        self.legend_good_led.pack(side="left", padx=(0, 2))
        self.legend_good_text.pack(side="left", padx=(0, 10))

        self.legend_high_led.pack(side="left", padx=(0, 2))
        self.legend_high_text.pack(side="left", padx=(0, 20))
        # Separator
        self.separator = tb.Separator(self.live_data_window, orient="horizontal")
        self.separator.pack(fill="x")

        # Matplotlib Graphs
        canvas = FigureCanvasTkAgg(self.fig, master=self.live_data_window)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=BOTH, expand=True)

        # Tabs
        self.notebook.add(self.live_data_window, text='Live Data')
        self.notebook.add(self.logging_window, text='Logging')


    def start_button_pressed(self):
        self.serial_manager.start_button_pushed = True


    def stop_button_pressed(self):
        self.serial_manager.stop_button_pushed = True

    def gui_update_loop(self):

        self.update_serial_status()
        self.serial_manager_widgets()

        if self.serial_manager.plotting_active:
            if self.last_plotting_active_state == False:
                self.reset_plots()
            self.update_live_graphs()
            self.update_warning_statuses()
            self.update_system_state()
        self.last_plotting_active_state = self.serial_manager.plotting_active
        # run again in 50 ms
        self.root.after(self.GUI_REFRESH_PERIOD, self.gui_update_loop)

    def update_serial_status(self):
        serial_status = self.serial_manager.connection_status
        match serial_status:
            case Connection_State.CONNECTED:
                self.device_status.config(text="Connected", foreground="lime")
            case Connection_State.DEVICE_BUSY:
                self.device_status.config(text="Port Busy", foreground="orange")
            case Connection_State.DISCONNECTED:
                self.device_status.config(text="Disconnected", foreground="red")
            case _:
                self.device_status.config(text="Disconnected", foreground="red")

    def serial_manager_widgets(self):
        manager_state = self.serial_manager.serial_manager_state

        if manager_state != Serial_Man_State.PACKET_HANDLING:
            self.start_button.config(text="Start", state="disabled")
            self.stop_button.config(text="Stop", state="disabled")
            return

        if self.serial_manager.micro_state_machine_running:
            self.start_button.config(text="Running", state="disabled")
            self.stop_button.config(state="normal")
        else:
            self.start_button.config(text="Start", state="normal")
            self.stop_button.config(state="disabled")

    def update_live_graphs(self):
        if self.last_plotting_active_state == False:
            for line in self.lines:
                line.set_data([], [])
            self.last_plotting_active_state = self.serial_manager.plotting_active
        if self.plot_queue.empty():
            return

        while not self.plot_queue.empty():
            packet = self.plot_queue.get()
            i = 0
            for deque in self.deques:
                deque.append(packet[i])
                i += 1

            for j in range(len(self.statuses)):
                self.statuses[j] = Warning_State(packet[i])
                i += 1

            self.system_state_status_data = System_SM_state(packet[i])

        for line, data_deque in zip(self.lines, self.deques[1:]):
            line.set_data(self.x_data_deque, data_deque)

        xmin = self.x_data_deque[0]
        xmax = self.x_data_deque[-1]

        if xmin == xmax:
            xmax = xmin + 1

        for plot in self.plots:
            plot.set_xlim(xmin, xmax)
            plot.relim()
            plot.autoscale_view(scalex=False, scaley=True)

        for txt, data_deque, unit in zip(self.value_texts, self.deques[1:], self.UNITS):
            if data_deque:
                txt.set_text(f"{data_deque[-1]:.2f} {unit}")

        self.fig.canvas.draw_idle()

    def update_warning_statuses(self):
        for j in range(len(self.statuses)):
            warning_state = self.statuses[j]
            match warning_state:
                case Warning_State.TOO_LOW:
                    self.warning_widgets[j].config(foreground="red")
                case Warning_State.GOOD:
                    self.warning_widgets[j].config(foreground="lime")
                case Warning_State.TOO_HIGH:
                    self.warning_widgets[j].config(foreground="orange")
                case _:
                    self.warning_widgets[j].config(foreground="blue")

    def update_system_state(self):
        match self.system_state_status_data:
            case System_SM_state.IDLE:
                self.system_state_status.config(text="Idle", foreground="white")
            case System_SM_state.CALIBRATING:
                self.system_state_status.config(text="Calibrating", foreground="orange")
            case System_SM_state.RUNNING:
                self.system_state_status.config(text="Running", foreground="green")
            case System_SM_state.ERROR:
                self.system_state_status.config(text="Error", foreground="red")
            case _:
                self.system_state_status.config(text="Unknown", foreground="white")
    def reset_plots(self):

        # clear deques
        for dq in self.deques:
            dq.clear()

        # reset line objects
        for line in self.lines:
            line.set_data([], [])

        # reset axes
        for plot in self.plots:
            plot.set_xlim(0, 1)
            plot.relim()
            plot.autoscale_view(scalex=False, scaley=True)

        self.fig.canvas.draw_idle()
