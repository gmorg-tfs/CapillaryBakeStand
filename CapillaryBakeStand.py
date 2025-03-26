import time
import matplotlib.pyplot as plt
from Logger import *
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
from novion import *
from collections import deque
from datetime import date


MAX_DATA_POINTS = 2048

class CapillaryBakeStandGui:
    def __init__(self, root):
        
        self.root = root
        self.root.title("Capillary Bake Stand")
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight() - 30
        self.test_stand_controller = CapillaryBakeStandController()
        #self.test_stand_controller = CapillaryBakeStandControllerSimulator()

        text_font = ("Helvetica", 14)
        self.state = tk.StringVar()
        self.state_label = tk.Label(root, textvariable=self.state, font=text_font)

        self.time = tk.StringVar()
        self.time.set(f"Time Left In State: ∞")
        self.time_label = tk.Label(root, textvariable=self.time, font=text_font)

        self.cycles = tk.StringVar()
        self.cycles.set(f"Cycles Completed: {self.test_stand_controller.cycle_count}")
        self.cycles_label = tk.Label(root, textvariable=self.cycles, font=text_font)

        self.water_percentage_text = tk.StringVar()
        self.water_percentage_text.set(f"Water Percentage: {self.test_stand_controller.novion.get_water_content()*100:.2f}%")
        self.water_percentage_label = tk.Label(root, textvariable=self.water_percentage_text, font=text_font)

        self.start_stop_button_text = tk.StringVar()
        self.start_stop_button_text.set("Start")
        self.start_stop_button = tk.Button(root, textvariable=self.start_stop_button_text, command=self.StartStop, font=text_font)

        self.manual_override_value = tk.BooleanVar()
        self.manual_override_value.set(False)
        self.manual_override_checkbox = tk.Checkbutton(root, command=self.toggle_manual_mode ,text="Manual Override", variable=tk.IntVar(), font=text_font)


        self.manual_fan_button_text = tk.StringVar()
        self.manual_fan_button_text.set("Fan On")
        self.manual_fan_control_button = tk.Button(root, textvariable=self.manual_fan_button_text, command=self.manual_fan_control, font=text_font)

        self.manual_heater_button_text = tk.StringVar()
        self.manual_heater_button_text.set("Heater On")
        self.manual_heater_control_button = tk.Button(root, textvariable=self.manual_heater_button_text, command=self.manual_heater_control, font=text_font)


        self.temperature_readback = tk.StringVar()
        self.temperature_readback.set(f"Temperature: n/a")
        self.temperature_readback_label = tk.Label(root, textvariable=self.temperature_readback, font=text_font)

        self.pressure_readback = tk.StringVar()
        self.pressure_readback.set(f"Pressure: n/a")
        self.pressure_readback_label = tk.Label(root, textvariable=self.pressure_readback, font=text_font)

        self.helium_readback = tk.StringVar()
        self.helium_readback.set(f"Helium: n/a")
        self.helium_readback_label = tk.Label(root, textvariable=self.helium_readback, font=text_font)

        self.helium_mode_button_text = tk.StringVar()
        if self.test_stand_controller.novion.mode == RGA_MODE:
            self.helium_mode_button_text.set("Helium: False")
        elif self.test_stand_controller.novion.mode == HELIUM_MODE:
            self.helium_mode_button_text.set("Helium: True")
        else:
            self.helium_mode_button_text.set("Helium: n/a")
        self.helium_mode_button = tk.Button(root, textvariable=self.helium_mode_button_text, command=self.handle_helium_mode_buton, font=text_font)

        self.UPDATE_PERIOD = 1000 #ms 
        self.PLOT_UPDATE_PERIOD = 0.25 #seconds 
        self.time_since_last_plot = 0
        
        self.fig,  self.temperature_axis = plt.subplots(figsize=(screen_width/100, screen_height/100), dpi=100)
        self.pressure_axis = self.temperature_axis.twinx()
        plt.subplots_adjust(top=1, bottom=0.15, left=0.1, right=0.9)

        self.temperature_axis.plot(np.array(self.test_stand_controller.time),np.array(self.test_stand_controller.temperature_data), color='red')
        self.pressure_axis.semilogy(np.array(self.test_stand_controller.time), np.array(self.test_stand_controller.pressure_data))

        self.canvas = FigureCanvasTkAgg(self.fig, master=root)

        self.canvas.get_tk_widget().grid(row=3, column=0, padx=2, pady=2, columnspan=6)


        root.protocol('WM_DELETE_WINDOW', self.exit)

        self.temperature_readback_label.grid(row=0, column=0)
        self.pressure_readback_label.grid(row=0, column=1)
        self.time_label.grid(row=0, column=2, padx=2, pady=1)
        self.state_label.grid(row=0, column=3, padx=2, pady=1)
        self.cycles_label.grid(row=0, column=4, padx=2, pady=1)
        self.helium_mode_button.grid(row=0, column=5, padx=2, pady=1)

        self.start_stop_button.grid(row=1, column=0, padx=2, pady=1)
        self.manual_override_checkbox.grid(row=1, column=1, padx=2, pady=1)
        self.manual_heater_control_button.grid(row=1, column=2, padx=2, pady=1)
        self.manual_fan_control_button.grid(row=1, column=3, padx=2, pady=1)
        self.water_percentage_label.grid(row=1, column=4, padx=2, pady=1)
        self.helium_readback_label.grid(row=1, column=5, padx=2, pady=1)

        self.update()

    def handle_helium_mode_buton(self):
        if self.test_stand_controller.novion.mode == RGA_MODE:
            self.test_stand_controller.novion.change_to_he_leak_detector()
            self.helium_mode_button_text.set("Helium: True")
        elif self.test_stand_controller.novion.mode == HELIUM_MODE:
            self.test_stand_controller.novion.change_to_rga()
            self.helium_mode_button_text.set("Helium: False")
        else:
            self.helium_mode_button_text.set("Unknown")

    def update_plot(self):
        threading.Thread(target=self._update_plot).start()

    def _update_plot(self):
        if len(self.test_stand_controller.time) == 0:
            return
        try:
            self.temperature_axis.cla()
            self.pressure_axis.cla()
            time, temperature, pressure = self.test_stand_controller.TimeTemperaturePressure()
            if len(time) < 2:
                #print("Insufficient data for plotting.")
                return
            self.temperature_axis.plot(time, temperature, color='red')
            self.pressure_axis.semilogy(time, pressure)
            x_axis = [time[0], time[(len(time)-1)//2], time[-1]] if len(time) > 2 else time
            self.pressure_axis.set_xticks(x_axis)
            self.canvas.draw()
            self.canvas.flush_events()
        except Exception as e:
            print(f"erroe updating plot: {e}")

    def manual_fan_control(self):
        if self.test_stand_controller.manual_override:
            if self.test_stand_controller.cooler_on:
                self.test_stand_controller.TurnFanOff()
            else:
                self.test_stand_controller.TurnFanOn()

    def manual_heater_control(self):
        if self.test_stand_controller.manual_override:
            if self.test_stand_controller.heater_on:
                self.test_stand_controller.TurnHeaterOff()
            else:
                self.test_stand_controller.TurnHeaterOn()
    
    def toggle_manual_mode(self):
        if self.test_stand_controller.manual_override:
            self.test_stand_controller.manual_override = False
        else:
            self.time.set(f"Time Left In State: ∞")
            self.test_stand_controller.manual_override = True

    def exit(self):
        self.test_stand_controller.Stop()
        quit()

    def StartStop(self):
        if self.test_stand_controller.running:
            self.test_stand_controller.Stop()
            self.start_stop_button_text.set("Start")
        else:
            self.test_stand_controller.Start()
            self.start_stop_button_text.set("Stop")

    def current_state_as_string(self):
        if not self.test_stand_controller.manual_override:
            if self.test_stand_controller.current_state == self.test_stand_controller.states["heating"]:
                return "Heating"
            elif self.test_stand_controller.current_state == self.test_stand_controller.states["cooling"]:
                return "Cooling"
            else:
                return "Idle"
        else:
            return "Manual Override"
    
    def update(self):
        try:
            if self.test_stand_controller.control_loop_completed_event.is_set() or time.time() - self.test_stand_controller.last_control_loop_time >= self.test_stand_controller.CONTROL_LOOP_TIMEOUT:
                threading.Thread(target=self.test_stand_controller.ControlLoop).start()

            self.cycles.set(f"Cycles Completed: {self.test_stand_controller.cycle_count}/{self.test_stand_controller.number_of_cycles_to_run}")
            self.state.set(f"State: {self.current_state_as_string()}")
            self.manual_heater_button_text.set(f"Heater On: {self.test_stand_controller.heater_on}")
            self.manual_fan_button_text.set(f"Cooler On: {self.test_stand_controller.cooler_on}")
            self.water_percentage_text.set(f"Water Percentage: {(self.test_stand_controller.novion.get_water_content()*100):.2f}%")
            if self.test_stand_controller.novion.mode == HELIUM_MODE:
                helium_value = self.test_stand_controller.novion.get_he_value()
                if helium_value is not None:
                    self.helium_readback.set(f"Helium: {helium_value:.2e}")

            if len(self.test_stand_controller.temperature_data) > 0:
                self.temperature_readback.set(f"Temperature: {self.test_stand_controller.last_temperature:.2f}")
                self.pressure_readback.set(f"Pressure: {self.test_stand_controller.last_pressure:.2e}")

            if not self.test_stand_controller.manual_override:
                total_remaining_time_s = 0
                minutes = 0
                seconds = 0
                if self.test_stand_controller.current_state == self.test_stand_controller.states["heating"]:
                    total_remaining_time_s = self.test_stand_controller.HEATING_TIME - (time.time() - self.test_stand_controller.start_time)
                    self.state_label.config(foreground="red")
                elif self.test_stand_controller.current_state == self.test_stand_controller.states["cooling"]:
                    total_remaining_time_s = self.test_stand_controller.COOLING_TIME - (time.time() - self.test_stand_controller.start_time)
                    self.state_label.config(foreground="blue")
                minutes = int(total_remaining_time_s // 60)
                seconds = int(total_remaining_time_s % 60)
                if seconds < 10:
                    seconds = f"0{seconds}"
                self.time.set(f"Time Left In State: {minutes}:{seconds}")
            else:
                self.time.set(f"Time Left In State: ∞")
            
            if time.time() - self.time_since_last_plot >= self.PLOT_UPDATE_PERIOD:
                self.time_since_last_plot = time.time()
                self.update_plot()

            self.root.after(self.UPDATE_PERIOD, self.update)
        except Exception as e:
            print(e)
            self.root.after(self.UPDATE_PERIOD, self.update)


class CapillaryBakeStandControllerBase:
    def __init__(self):
        #state
        self.running = False
        self.cycle_count = 0
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
        self.time = deque(maxlen=MAX_DATA_POINTS)
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

    def Stop(self):
        self.running = False
        self.current_state = 0
        self.TurnOffHeaterAndCooler()

    def Start(self):
        self.cycle_count = 0
        self.running = True
        self.Go()
    
    def Go(self):
        self.StartHeating()
        self.ControlLoop()

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

    def ControlLoop(self):
        try:
            self.control_loop_completed_event.clear()
            self.last_control_loop_time = time.time()
            if not self.manual_override:
                if self.current_state == self.states["heating"] and time.time() - self.start_time >= self.HEATING_TIME:
                    self.StartCooling()
                elif self.current_state == self.states["cooling"] and time.time() - self.start_time >= self.COOLING_TIME:
                    self.cycle_count += 1
                    if self.cycle_count < self.number_of_cycles_to_run:
                        self.StartHeating()
                    else:
                        self.Stop()

            if self.logging_for_plotting_complete_event.is_set() or time.time() - self.last_log_for_plot_time >= self.LOGGING_THREAD_TIMEOUT:
                threading.Thread(target=self.MeasureTemperaurePressure).start()

            if self.running and self.logging_complete_event.is_set() and self.TimeForNextLog():
                threading.Thread(target=self.RGAScanAndSaveData).start()

            self.control_loop_completed_event.set()
        except Exception as e:
            print(e)
            self.Stop()
            self.control_loop_completed_event.set()


    def RGAScanAndSaveData(self):
        #pressure_novion = self.MeasurePressure()
        self.logging_complete_event.clear()
        try:
            #if pressure_novion is None:
            #    self.logging_complete_event.set()
            #    return
            #temperature_voltage_raw, temperature = self.MeasureTemperature()
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
            print(f"Error scanning and saving data: {e}")
        #self.last_pressure = pressure_novion
        #self.last_temperature = temperature
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
            self.time.append(f"{time_struct.tm_hour}:{time_struct.tm_min}:{time_struct.tm_sec}")
            self.last_temperature = temperature
            self.last_pressure = pressure_novion
        self.last_log_for_plot_time = time.time()
        return self.logging_for_plotting_complete_event.set()

    def TimeTemperaturePressure(self):
        with self.data_lock:
            time = list(self.time)
            temperature = list(self.temperature_data)   
            pressure = list(self.pressure_data)
        return time, temperature, pressure

    def MeasureTemperature(self):
        Exception("Not Implemented")

    def MeasurePressure(self):
        Exception("Not Implemented")
    
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

class CapillaryBakeStandControllerSimulator(CapillaryBakeStandControllerBase):
    def __init__(self):
        super().__init__()
        #self.HEATING_TIME = 20  #seconds
        #self.COOLING_TIME = 20  #seconds
        self.number_of_cycles_to_run = 1000
    
    def RandomInstrumentResponseTime(self):
        time.sleep(0.05 + random.random() % 0.5)

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
        self.novion = NovionRGA()
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
    root = tk.Tk()
    gui = CapillaryBakeStandGui(root)
    gui.root.mainloop()
    