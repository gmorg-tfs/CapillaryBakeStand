import time
import matplotlib.pyplot as plt
from Logger import *
import tkinter as tk
import threading
import subprocess
import random
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from novion import *
from collections import deque
from datetime import date
import traceback
from threading import Thread
import sys
from turbo import PfeifferTurboPump, PfeifferTurboPumpSim

MAX_DATA_POINTS = 2048
def main():
    #controller = CapillaryBakeStandControllerSimulator()
    controller = CapillaryBakeStandController()
    gui = CapillaryBakeStandGui(controller)
    controller.gui = gui
    controller.start_monitoring()  # Start monitoring immediately
    gui.mainloop()

class CapillaryBakeStandGui(tk.Tk):
    def __init__(self, _controller):
        super().__init__()
        self.controller = _controller
        self.title("Capillary Bake Stand Controller")

        # Create main frames for organization
        control_frame = tk.LabelFrame(self, text="Controls", font=("Arial", 12))
        status_frame = tk.LabelFrame(self, text="Status", font=("Arial", 12))
        settings_frame = tk.LabelFrame(self, text="Settings", font=("Arial", 12))

        # Control buttons
        self.start_button = tk.Button(control_frame, text="Start Cycling", command=self.start_btn_clicked, width=20, font=("Arial", 12))
        self.heat_button = tk.Button(control_frame, text="Start Heating", command=self.heat_btn_clicked, width=20, font=("Arial", 12))
        self.cool_button = tk.Button(control_frame, text="Start Cooling", command=self.cool_btn_clicked, width=20, font=("Arial", 12))
        self.turbo_start_button = tk.Button(control_frame, text="Start Turbo", command=self.turbo_btn_clicked, width=20, font=("Arial", 12))
        self.turbo_stop_button = tk.Button(control_frame, text="Stop Turbo", command=self.turbo_stop_clicked, width=20, font=("Arial", 12))
        self.plot_button = tk.Button(control_frame, text="Create Plots", command=self.create_plots, width=20, font=("Arial", 12))

        # Status displays
        self.cycle_status = tk.StringVar(value="Cycle: 0/0")
        self.state_status = tk.StringVar(value="State: Idle")
        self.time_remaining_status = tk.StringVar(value="Time Remaining: 00:00")
        self.temperature_status = tk.StringVar(value="Temperature: 0.00°C")
        self.pressure_status = tk.StringVar(value="Pressure: 0.00e-6 torr")
        self.water_content_status = tk.StringVar(value="Water Content: 0.00")
        self.turbo_speed_status = tk.StringVar(value="Turbo Speed: 0 RPM")
        self.turbo_temperature_status = tk.StringVar(value="Turbo Temperature: 0.00°C")
        self.turbo_power_status = tk.StringVar(value="Turbo Power: 0.00 W")

        # State tracking
        self.cycling = False
        self.heating = False
        self.cooling = False
        self.turbo_running = False

        status_labels = [
            (self.cycle_status, "Cycle"),
            (self.state_status, "State"),
            (self.time_remaining_status, "Time Remaining"),
            (self.temperature_status, "Temperature"),
            (self.pressure_status, "Pressure"),
            (self.water_content_status, "Water Content"),
            (self.turbo_speed_status, "Turbo Speed"),
            (self.turbo_temperature_status, "Turbo Temperature"),
            (self.turbo_power_status, "Turbo Power")
        ]

        for i, (var, _) in enumerate(status_labels):
            tk.Label(status_frame, textvariable=var, font=("Arial", 12)).grid(row=i, column=0, padx=10, pady=5, sticky="w")        
        
        # Settings inputs
        settings = [
            ("Total Cycles:", "number_of_cycles_to_run", "168"),  # 24 * 7 cycles by default
            ("Heating Time (min):", "HEATING_TIME", "20"),  # 20 min = 1200 sec
            ("Cooling Time (min):", "COOLING_TIME", "40"),  # 40 min = 2400 sec
            ("Log Rate (sec):", "LOGGING_PERIOD", "10"),
            ("Turbo Trip Level (torr):", "turbo_pressure_too_high", "1e-1"),
            ("Turbo Start Level (torr):", "turbo_on_threshold", "1e-2")
        ]

        self.setting_vars = {}
        for i, (label, var_name, default) in enumerate(settings):
            tk.Label(settings_frame, text=label, font=("Arial", 12)).grid(row=i, column=0, padx=10, pady=5, sticky="e")
            var = tk.StringVar(value=default)
            self.setting_vars[var_name] = var
            entry = tk.Entry(settings_frame, textvariable=var, font=("Arial", 12), width=10)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="w")

        # Add Apply Settings button
        self.apply_settings_button = tk.Button(settings_frame, text="Apply Settings", command=self.apply_settings_clicked, width=20, font=("Arial", 12))
        self.apply_settings_button.grid(row=len(settings), column=0, columnspan=2, padx=10, pady=10)

        # Layout frames
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        status_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        settings_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        # Layout control buttons
        for i, btn in enumerate([self.start_button, self.heat_button, self.cool_button, 
                               self.turbo_start_button, self.turbo_stop_button, self.plot_button]):
            btn.grid(row=i, column=0, padx=10, pady=5)        
        
        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        # Initial button states
        self.update_button_states()
        
    def update_button_states(self):
        # Update cycling button
        if self.cycling:
            self.start_button.configure(text="Stop Cycling")
            self.heat_button.configure(state="disabled")
            self.cool_button.configure(state="disabled")
        else:
            self.start_button.configure(text="Start Cycling")
            self.heat_button.configure(state="normal")
            self.cool_button.configure(state="normal")

        # Update heating/cooling buttons
        if self.heating:
            self.heat_button.configure(text="Stop Heating")
            self.cool_button.configure(state="disabled")
        else:
            self.heat_button.configure(text="Start Heating")
            if not self.cycling:
                self.cool_button.configure(state="normal")

        if self.cooling:
            self.cool_button.configure(text="Stop Cooling")
            self.heat_button.configure(state="disabled")
        else:
            self.cool_button.configure(text="Start Cooling")
            if not self.cycling:
                self.heat_button.configure(state="normal")

        # Update turbo buttons
        #if self.turbo_running:
        #    self.turbo_start_button.configure(state="disabled")
        #    self.turbo_stop_button.configure(state="normal")
        #else:
        #    self.turbo_start_button.configure(state="normal")
        #    self.turbo_stop_button.configure(state="disabled")

    def start_btn_clicked(self):
        try:
            if not self.cycling:
                self.controller.Start()
                self.cycling = True
                self.heating = True
                self.cooling = False
            else:
                self.controller.Stop()
                self.cycling = False
                self.heating = False
                self.cooling = False
            self.update_button_states()
        except Exception as e:
            print(f"Error in start button handler: {e}")

    def heat_btn_clicked(self):
        try:
            if not self.heating:
                self.controller.StartHeating()
                self.heating = True
                self.cooling = False
            else:
                self.controller.TurnHeaterOff()
                self.heating = False
                self.state_status.set("State: Idle")
            self.update_button_states()
        except Exception as e:
            print(f"Error in heat button handler: {e}")

    def cool_btn_clicked(self):
        try:
            if not self.cooling:
                self.controller.StartCooling()
                self.cooling = True
                self.heating = False
            else:
                self.controller.TurnFanOff()
                self.cooling = False
                self.state_status.set("State: Idle")
            self.update_button_states()
        except Exception as e:
            print(f"Error in cool button handler: {e}")

    def turbo_btn_clicked(self):
        try:
            self.controller.start_turbo()
            self.turbo_running = True
            self.update_button_states()
        except Exception as e:
            print(f"Error starting turbo: {e}")

    def turbo_stop_clicked(self):
        try:
            self.controller.stop_turbo()
            self.turbo_running = False
            self.update_button_states()
        except Exception as e:
            print(f"Error stopping turbo: {e}")

    def create_plots(self):
        def run_plotting():
            try:
                subprocess.run(["python", "graph_stuff.py"], check=True)
            except Exception as e:
                print(f"error creating plots: {e}")
        plot_thread = threading.Thread(target=run_plotting, daemon=True)
        plot_thread.start()

            
    def apply_settings_clicked(self):
        try:
            # Apply all settings at once
            for var_name, var in self.setting_vars.items():
                value = var.get()
                if var_name in ["HEATING_TIME", "COOLING_TIME"]:
                    # Convert minutes to seconds
                    value = float(value) * 60
                elif var_name in ["turbo_pressure_too_high", "turbo_on_threshold"]:
                    value = float(value)
                else:
                    value = int(value)
                setattr(self.controller, var_name, value)
        except Exception as e:
            print(f"Error applying settings: {e}")

    def update(self, status_dict): 
        try:
            self.cycle_status.set(f"Cycle: {status_dict['cycle']}")
            self.state_status.set(f"State: {status_dict['state']}")
            self.time_remaining_status.set(f"Time left: {status_dict['time_remaining']}")
            self.temperature_status.set(f"Temperature: {status_dict['temperature']}°C")
            self.pressure_status.set(f"Pressure: {status_dict['pressure']}")
            self.water_content_status.set(f"Water Content %: {status_dict.get('water_content', '0.00')}")
            self.turbo_speed_status.set(f"Turbo Speed: {status_dict['turbo_speed']} RPM")
            self.turbo_temperature_status.set(f"Turbo Temperature: {status_dict['turbo_temperature']:.2f}°C")
            self.turbo_power_status.set(f"Turbo Power: {status_dict['turbo_power']:.2f} W")

            # Update turbo state based on speed
            if status_dict['turbo_speed'] > 0 and not self.turbo_running:
                self.turbo_running = True
                self.update_button_states()
            elif status_dict['turbo_speed'] == 0 and self.turbo_running:
                self.turbo_running = False
                self.update_button_states()
        except Exception as e:
            print(f"Error updating GUI: {e}")

    def update_status(self, message):
        self.after(0, self.update, message)

class CapillaryBakeStandControllerBase(Thread):
    def __init__(self, _gui=None):
        super().__init__()
        self.daemon = True  # Thread will stop when main program stops
        #state
        self.gui = _gui
        self.turbo = PfeifferTurboPumpSim()
        self.running = False
        self.monitoring = False
        self.cycle_count = 0
        self.update_interval = 0.1  # 100ms between updates
        self.number_of_cycles_to_run = 24 * 7
        self.start_time = 0
        self.states = {"heating": 1, "cooling": 2}
        self.current_state = 0
        self.manual_override = False
        self.heater_on = False
        self.cooler_on = False
        self.last_pressure = 0
        self.last_temperature = 0
        #process times
        self.HEATING_TIME = 20 *60 #seconds
        self.COOLING_TIME = 40 *60 #seconds
        #data
        self.temperature_data = deque(maxlen=MAX_DATA_POINTS)
        self.pressure_data = deque(maxlen=MAX_DATA_POINTS)
        self.time_data = deque(maxlen=MAX_DATA_POINTS)  # Renamed from 'time' to avoid shadowing built-in
        #novion 
        self.novion = NovionMock()
        self.logging_thread = threading.Thread(target=self.RGAScanAndSaveData)
        self.logging_complete_event = threading.Event()
        self.logging_complete_event.set()

        self.control_loop_completed_event = threading.Event()
        self.control_loop_completed_event.set()
        self.last_control_loop_time = 0
        self.CONTROL_LOOP_TIMEOUT = 20 #seconds

        self.logging_for_plotting_complete_event = threading.Event()
        self.logging_for_plotting_complete_event.set()
        self.last_log_for_plot_time = 0 #seconds
        self.LOGGING_THREAD_TIMEOUT = 20 #seconds

        #logging
        header = "Time (s),Pressure (torr),Temperature (C)"
        for i in range(self.novion.mass_start, self.novion.mass_end + 1):
            header += f",{i}"
        self.logger = Logger(_base_path="C:\\Data\\toaster\\",
                             _file_name_base=f"{date.today().isoformat().replace("-", "_")}_toaster_data_",
                             _file_extension=".csv",
                             _header=header)
        self.last_log_time = 0
        self.LOGGING_PERIOD = 10 #seconds
        self.data_lock = threading.Lock()

        self.turbo_on_threshold = 1e-2 #torr
        self.turbo_pressure_too_high = 1e-1
        self.turbo_speed = 0
        self.turbo_temperature = 0
        self.turbo_power = 0    
    
    def start_monitoring(self):
        """Start monitoring temperature, pressure, and turbo pump without starting the cycling."""
        self.monitoring = True
        if not self.is_alive():
            self.start()  # Start the controller thread

    def stop_monitoring(self):
        """Stop all monitoring and control."""
        self.monitoring = False
        self.running = False
        self.TurnOffHeaterAndCooler()

    def Stop(self):
        """Stop cycling but continue monitoring."""
        self.running = False
        self.current_state = 0
        self.TurnOffHeaterAndCooler()

    def Start(self):
        """Start the heating/cooling cycles."""
        self.cycle_count = 0
        self.running = True
        self.logger.create_new_file()
        self.Go()

    def Go(self):
        self.StartHeating()

    def StartHeating(self):
        self.current_state = self.states["heating"]
        self.start_time = time.time()
        self.TurnFanOff()
        self.TurnHeaterOn()

    def StartCooling(self):
        self.current_state = self.states["cooling"]
        self.start_time = time.time()
        self.TurnHeaterOff()
        self.TurnFanOn()

    def TimeForNextLog(self):
        return time.time() - self.last_log_time >= self.LOGGING_PERIOD


    def RGAScanAndSaveData(self):
        self.logging_complete_event.clear()
        try:
            temperature = 0
            pressure = 0
            with self.data_lock:
                temperature = self.last_temperature
                pressure = self.last_pressure
            
            if self.novion.mode == RGA_MODE and self.novion.can_scan():
                rga_scan = self.novion.scan()
                self.logger.log(f"{time.time()},{pressure},{temperature},{rga_scan}")
                self.last_log_time = time.time()
        except Exception as e:
            print(f"\nError scanning and saving data: {e}")
        self.logging_complete_event.set()

    def MeasureTemperaurePressure(self):
        self.logging_for_plotting_complete_event.clear()
        temperature = self.MeasureTemperature()

        if temperature is None:
            self.last_log_for_plot_time = time.time()
            return self.logging_for_plotting_complete_event.set()
        
        pressure_novion = self.MeasurePressure()
        if pressure_novion is None:
            self.last_log_for_plot_time = time.time()
            return self.logging_for_plotting_complete_event.set()
        
        with self.data_lock:
            self.temperature_data.append(temperature)
            self.pressure_data.append(pressure_novion)
            time_struct = time.localtime()
            self.time_data.append(f"{time_struct.tm_hour}:{time_struct.tm_min}:{time_struct.tm_sec}")
            self.last_temperature = temperature
            self.last_pressure = pressure_novion
        self.last_log_for_plot_time = time.time()
        return self.logging_for_plotting_complete_event.set()

    def TimeTemperaturePressure(self):
        with self.data_lock:
            time_data = list(self.time_data)
            temperature = list(self.temperature_data)   
            pressure = list(self.pressure_data)
        return time_data, temperature, pressure

    def MeasureTemperature(self):
        raise Exception("Not Implemented")

    def MeasurePressure(self):
        raise Exception("Not Implemented")
    
    def TurnOffHeaterAndCooler(self):
        self.TurnHeaterOff()
        self.TurnFanOff()
    
    def TurnFanOn(self):
        self.cooler_on = True
    
    def TurnFanOff(self):
        self.cooler_on = False
    
    def TurnHeaterOn(self):
        self.heater_on = True
    
    def TurnHeaterOff(self):
        self.heater_on = False
    
    def figure_out_state(self):
        if self.current_state == self.states["heating"]:
            return "Heating"
        elif self.current_state == self.states["cooling"]:
            return "Cooling"
        else:
            return "Idle"

    def check_turbo(self):
        if self.turbo is not None:
            try:
                if self.turbo.is_pumping() and self.last_pressure >= self.turbo_pressure_too_high:
                    self.turbo.stop_pump()
                    print(f"\nPressure too high: {self.last_pressure:.2e}, stopping turbo pump.")

                #elif self.last_pressure <= self.turbo_on_threshold and not self.turbo.is_pumping():
                #    self.turbo.start_pump()
                
                turbo_speed = self.turbo.get_rotation_speed()
                turbo_temperature = self.turbo.get_temperature()
                turbo_power = self.turbo.get_power_usage()
                #print(turbo_power)
                if turbo_speed is not None: 
                    self.turbo_speed = turbo_speed
                if turbo_temperature is not None:
                    self.turbo_temperature = turbo_temperature
                if turbo_power is not None:
                    self.turbo_power = turbo_power
            except Exception as e:
                print(f"\nError checking turbo pump: {e}")
    
    def start_turbo(self):
        """Start the turbo pump manually."""
        if self.turbo is not None:
            try:
                self.turbo.start_pump()
                return True
            except Exception as e:
                print(f"\nError starting turbo pump: {e}")
                return False
        return False
    
    def stop_turbo(self):
        """Stop the turbo pump manually."""
        if self.turbo is not None:
            try:
                self.turbo.stop_pump()
                return True
            except Exception as e:
                print(f"\nError stopping turbo pump: {e}")
                return False
        return False

    def monitor_conditions(self):
        """Monitor and control based on current conditions."""
        # Monitor temperature and pressure
        self.MeasureTemperaurePressure()
        
        # Check and control turbo pump
        self.check_turbo()
        
        # Log data if it's time
        if self.TimeForNextLog():
            self.RGAScanAndSaveData()

    def run(self):
        """Main control loop running in its own thread."""
        while self.monitoring:
            try:
                # Always monitor conditions when monitoring is enabled
                if self.monitoring:
                    self.monitor_conditions()

                # Handle cycling if running
                if self.running:
                    current_time = time.time()
                    if self.current_state == self.states["heating"]:
                        if current_time - self.start_time >= self.HEATING_TIME:
                            self.StartCooling()
                    elif self.current_state == self.states["cooling"]:
                        if current_time - self.start_time >= self.COOLING_TIME:
                            self.cycle_count += 1
                            if self.cycle_count < self.number_of_cycles_to_run:
                                self.StartHeating()
                            else:
                                self.Stop()

                # Update GUI if available
                if self.gui is not None:
                    self.update_gui()

            except Exception as e:
                print(f"\nError in control loop: {e}")

            time.sleep(self.update_interval)

    def update_gui(self):
        """Send current status to GUI."""
        try:
            time_elapsed = time.time() - self.start_time
            time_remaining = 0
            if self.current_state == self.states["heating"]:
                time_remaining = self.HEATING_TIME - time_elapsed
            elif self.current_state == self.states["cooling"]:
                time_remaining = self.COOLING_TIME - time_elapsed

            minutes = int(time_remaining // 60)
            seconds = int(time_remaining % 60)
            if seconds < 10:
                seconds = f"0{seconds}"
            
            state = self.figure_out_state()
            
            # Create a complete status dictionary including water content
            water_content = "0.00"
            try:
                water_content = f"{self.novion.get_water_content()*100:.2f}"
            except Exception:
                pass
            #print(f"p: {self.turbo_power}")
            status_dict = {
                "cycle": f"{self.cycle_count}/{self.number_of_cycles_to_run}",
                "state": state,
                "time_remaining": f"{minutes}:{seconds}",
                "temperature": f"{self.last_temperature:.2f}",
                "pressure": f"{self.last_pressure:.2e}",
                "water_content": water_content,
                "turbo_speed": self.turbo_speed,
                "turbo_temperature": self.turbo_temperature,
                "turbo_power": self.turbo_power
            }
            
            # Use after_idle to update GUI from this thread safely
            self.gui.after_idle(self.gui.update_status, status_dict)
        except Exception as e:
            print(f"\nError updating GUI: {e}")


class CapillaryBakeStandControllerSimulator(CapillaryBakeStandControllerBase):
    def __init__(self):
        super().__init__()

    def RandomInstrumentResponseTime(self):
        time.sleep(0.05 + random.random() * 0.5)

    def MeasureTemperature(self):
        self.RandomInstrumentResponseTime()
        if len(self.temperature_data) == 0:
            return 25
        delta = random.random()

        if self.heater_on and not self.cooler_on:
            return self.temperature_data[-1] + delta
        elif self.cooler_on and not self.heater_on:
            return self.temperature_data[-1]  - delta
        elif self.heater_on and self.cooler_on:
            return self.temperature_data[-1] + (delta / 2)
        else:
            if self.temperature_data[-1] > 25:
                return self.temperature_data[-1] - (delta / 4)
            else:
                return self.temperature_data[-1]
                        
    def MeasurePressure(self):
        self.RandomInstrumentResponseTime()
        if len(self.pressure_data) == 0:
            return 1e-6
        delta = random.random() * 1e-7 * 10
        if self.heater_on and not self.cooler_on:
            return self.last_pressure + delta
        elif self.cooler_on and not self.heater_on:
            return self.last_pressure  - delta
        elif self.heater_on and self.cooler_on:
            return self.last_pressure + (delta / 2)
        else:
            if self.last_pressure > 1e-6:
                return self.last_pressure - (delta / 4)
            else:
                return self.last_pressure


import u3
from LabJackPython import TCVoltsToTemp, LJ_ttK, eDAC, eAIN
class CapillaryBakeStandController(CapillaryBakeStandControllerBase):
    def __init__(self):
        super().__init__()
        self.turbo = PfeifferTurboPump(port="COM6", address=1)
        self.novion = NovionRGA(com_port="COM8")
        self.device = u3.U3()
        self.THERMOCOUPLE_VOLTAGE_GAIN = 51
        self.THERMOCOUPLE_VOLTAGE_OFFSET = 1.254 #volts
        self.THERMOCOUPLE_CHANNEL = 6
        self.PRESSURE_SENSOR_CHANNEL = 0
        self.HEATER_CHANNEL = 0
        self.COOLER_CHANNEL = 1
        self.HEATER_VOLTAGE = 5 #volts
        self.COOLER_VOLTAGE = 5 #volts
   
    def Reconnect(self):
        try:
            self.device.close()
            self.device = u3.U3()
            return True
        except Exception as e:
            return False
        
    def SetVoltageOnDac(self, channel, voltage):
        try:
            eDAC(self.device.handle, channel, voltage)
            return True
        except Exception as e:
            return self.Reconnect()

    def ReadVoltage(self, channel):
        try:
            return eAIN(self.device.handle, channel)
        except Exception as e:
            self.Reconnect()
            return None

    def MeasureTemperature(self):
        voltage_raw = self.ReadVoltage(self.THERMOCOUPLE_CHANNEL)
        if voltage_raw is None:
            return None
        voltage = (voltage_raw - self.THERMOCOUPLE_VOLTAGE_OFFSET) / self.THERMOCOUPLE_VOLTAGE_GAIN
        try:
            internal_temp = self.device.getTemperature()
        except Exception as e:
            self.device.close()
            self.device = u3.U3()
            return None
        temperature = TCVoltsToTemp(LJ_ttK, voltage, internal_temp)         #K
        #t = (1.8 * t) - 459.67                                             #F
        temperature -= 278.00                                               #K
        return temperature

    def MeasurePressure(self):
        p = self.novion.request_pressure()
        if p is None or p < 1e-12:
            return None
        else:
            return p

    def TurnFanOn(self):
        self.cooler_on = True
        self.SetVoltageOnDac(self.COOLER_CHANNEL, self.COOLER_VOLTAGE)

    def TurnFanOff(self):
        self.cooler_on = False
        self.SetVoltageOnDac(self.COOLER_CHANNEL, 0)

    def TurnHeaterOn(self):
        self.heater_on = True
        self.SetVoltageOnDac(self.HEATER_CHANNEL, self.HEATER_VOLTAGE)

    def TurnHeaterOff(self):
        self.heater_on = False
        self.SetVoltageOnDac(self.HEATER_CHANNEL, 0)


if __name__ == "__main__":
    main()
