import time
import matplotlib.pyplot as plt
from Logger import *
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
from novion import *

class CapillaryBakeStandGui:
    def __init__(self, root):
        self.root = root
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight() - 30
        #self.test_stand_controller = CapillaryBakeStandController()
        self.test_stand_controller = CapillaryBakeStandControllerSimulator()

        self.state = tk.StringVar()
        self.state_label = tk.Label(root, textvariable=self.state)

        self.time = tk.StringVar()
        self.time.set(f"Time Left In State: ∞")
        self.time_label = tk.Label(root, textvariable=self.time)

        self.cycles = tk.StringVar()
        self.cycles.set(f"Cycles Completed: {self.test_stand_controller.cycle_count}")
        self.cycles_label = tk.Label(root, textvariable=self.cycles)

        self.start_stop_button_text = tk.StringVar()
        self.start_stop_button_text.set("Start")
        self.start_stop_button = tk.Button(root, textvariable=self.start_stop_button_text, command=self.StartStop)

        self.manual_override_value = tk.BooleanVar()
        self.manual_override_value.set(False)
        self.manual_override_checkbox = tk.Checkbutton(root, command=self.toggle_manual_mode ,text="Manual Override", variable=tk.IntVar())


        self.manual_fan_button_text = tk.StringVar()
        self.manual_fan_button_text.set("Fan On")
        self.manual_fan_control_button = tk.Button(root, textvariable=self.manual_fan_button_text, command=self.manual_fan_control)

        self.manual_heater_button_text = tk.StringVar()
        self.manual_heater_button_text.set("Heater On")
        self.manual_heater_control_button = tk.Button(root, textvariable=self.manual_heater_button_text, command=self.manual_heater_control)


        self.temperature_readback = tk.StringVar()
        self.temperature_readback.set(f"Temperature: n/a")
        self.temperature_readback_label = tk.Label(root, textvariable=self.temperature_readback)

        self.pressure_readback = tk.StringVar()
        self.pressure_readback.set(f"Pressure: n/a")
        self.pressure_readback_label = tk.Label(root, textvariable=self.pressure_readback)

        self.UPDATE_PERIOD = 250 #ms  how often to update gui. control loop is run once per update and will log data at controller specified logging frequency

        fig, ax1 = plt.subplots(figsize=(screen_width/100, screen_height/100), dpi=100)
        plt.subplots_adjust(top=1, bottom=0.15, left=0.1, right=0.9)
        self.temperature_axis = ax1
        self.pressure_axis = ax1.twinx()

        self.fig = fig
        self.temperature_axis.plot(self.test_stand_controller.temperature_data, color='red')
        self.pressure_axis.semilogy(self.test_stand_controller.pressure_data)

        self.canvas = FigureCanvasTkAgg(fig, master=root)
        self.canvas.draw()

        self.canvas.get_tk_widget().grid(row=3, column=0, padx=2, pady=2, columnspan=5)

        root.protocol('WM_DELETE_WINDOW', self.exit)

        self.temperature_readback_label.grid(row=0, column=0)
        self.pressure_readback_label.grid(row=0, column=1)
        self.time_label.grid(row=0, column=2, padx=2, pady=1)
        self.state_label.grid(row=0, column=3, padx=2, pady=1)
        self.cycles_label.grid(row=0, column=4, padx=2, pady=1)

        self.start_stop_button.grid(row=1, column=0, padx=2, pady=1)
        self.manual_override_checkbox.grid(row=1, column=1, padx=2, pady=1)
        self.manual_heater_control_button.grid(row=1, column=2, padx=2, pady=1)
        self.manual_fan_control_button.grid(row=1, column=3, padx=2, pady=1)
        self.update()

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
        self.test_stand_controller.ControlLoop()
        self.cycles.set(f"Cycles Completed: {self.test_stand_controller.cycle_count}/{self.test_stand_controller.number_of_cycles_to_run}")
        self.state.set(f"State: {self.current_state_as_string()}")
        self.manual_heater_button_text.set(f"Heater On: {self.test_stand_controller.heater_on}")
        self.manual_fan_button_text.set(f"Cooler On: {self.test_stand_controller.cooler_on}")

        if len(self.test_stand_controller.temperature_data) > 0:
            self.temperature_readback.set(f"Temperature: {self.test_stand_controller.temperature_data[-1]:.2f}")
            self.pressure_readback.set(f"Pressure: {self.test_stand_controller.pressure_data[-1]:.2e}")
        if not self.test_stand_controller.manual_override:
            if self.test_stand_controller.current_state == self.test_stand_controller.states["heating"]:
                total_remaining_time_s = self.test_stand_controller.HEATING_TIME - (time.time() - self.test_stand_controller.start_time)
                minutes = total_remaining_time_s // 60
                seconds = total_remaining_time_s % 60
                self.time.set(f"Time Left In State: {int(minutes)}:{int(seconds)}")
            elif self.test_stand_controller.current_state == self.test_stand_controller.states["cooling"]:
                total_remaining_time_s = self.test_stand_controller.COOLING_TIME - (time.time() - self.test_stand_controller.start_time)
                minutes = total_remaining_time_s // 60
                seconds = total_remaining_time_s % 60
                self.time.set(f"Time Left In State: {int(minutes)}:{int(seconds)}")
        else:
            self.time.set(f"Time Left In State: ∞")

        self.temperature_axis.cla()
        self.pressure_axis.cla()
        x_axis = [self.test_stand_controller.time[0], self.test_stand_controller.time[(len(self.test_stand_controller.time)-1)//2]  ,self.test_stand_controller.time[-1]]
        self.temperature_axis.plot(self.test_stand_controller.time, self.test_stand_controller.temperature_data, color='red')
        self.pressure_axis.semilogy(self.test_stand_controller.time, self.test_stand_controller.pressure_data)
        self.pressure_axis.set_xticks(x_axis)
        self.canvas.draw()
        self.canvas.flush_events()

        self.root.after(self.UPDATE_PERIOD, self.update)


class CapillaryBakeStandControllerBase:
    def __init__(self):
        #state
        self.running = False
        self.cycle_count = 0
        self.number_of_cycles_to_run = 10
        self.start_time = 0
        self.states = {"heating": 1, "cooling": 2}
        self.current_state = 0
        self.manual_override = False
        self.heater_on = False
        self.cooler_on = False
        #process times
        self.HEATING_TIME = 20 *60 #seconds
        self.COOLING_TIME = 40 *60 #seconds
        #data
        self.temperature_data = []
        self.pressure_data = []
        self.time = []
        #logging
        self.logger = Logger(_base_path="C:\\Data\\toaster\\",
                             _file_name_base="toaster_data_",
                             _file_extension=".csv",
                             _header="Time, Temperature Voltage (V), Temperature (C), Pressure Voltage (V), Pressure (mbar)")
        self.LOGGING_PERIOD = 1 #seconds
        self.last_log = 0
        self.relative_temperature_change_to_log = 0.02
        self.relative_pressure_change_to_log = 0.02
        #novion 
        self.novion = NovionMock()
        self.last_rga_scan = 0
        self.RGA_SCAN_PERIOD = 10 #seconds
        self.rga_thread = threading.Thread(target=self.rga_scan)

    def Stop(self):
        if not self.manual_override:
            if self.cycle_count < self.number_of_cycles_to_run:
                self.current_state = self.states["cooling"]
                self.cycle_count = self.number_of_cycles_to_run #will cool for cooling time and then stop
            else:
                self.running = False
                self.current_state = 0
                self.TurnOffHeaterAndCooler()
        else:
            self.running = False
            self.current_state = 0
            self.TurnOffHeaterAndCooler

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

    def ControlLoop(self):
        try:
            if not self.manual_override:
                if self.current_state == self.states["heating"] and time.time() - self.start_time >= self.HEATING_TIME:
                    self.StartCooling()
                elif self.current_state == self.states["cooling"] and time.time() - self.start_time >= self.COOLING_TIME:
                    self.cycle_count += 1
                    if self.cycle_count < self.number_of_cycles_to_run:
                        self.StartHeating()
                    else:
                        self.Stop()
                    
            self.LogData()
        except Exception as e:
            print(e)
            self.Stop()

    def rga_scan(self):
        self.novion.scan(self.temperature_data)

    def do_scan(self):
        self.rga_thread = threading.Thread(target=self.rga_scan)
        self.rga_thread.start()

    def LogData(self):
        temperature_voltage_raw, temperature = self.MeasureTemperature()
        pressure_voltage_raw, pressure = self.MeasurePressure()

        if len(self.temperature_data) == 0:
            self.temperature_data+=[temperature]
            self.pressure_data+=[pressure]
            time_struct = time.localtime()
            self.time += [f"{time_struct.tm_hour}:{time_struct.tm_min}:{time_struct.tm_sec}"]

        log_condition1 = time.time() - self.last_log >= self.LOGGING_PERIOD
        log_condition2 = self.temperature_data[-1] * self.relative_temperature_change_to_log < abs(temperature - self.temperature_data[-1])
        log_condition3 = self.pressure_data[-1] * self.relative_pressure_change_to_log < abs(pressure - self.pressure_data[-1])
        if  log_condition1 or log_condition2 or log_condition3:
            self.temperature_data+=[temperature]
            self.pressure_data+=[pressure]
            self.logger.log(f"{time.time()}, {temperature_voltage_raw}, {temperature},  {pressure_voltage_raw}, {pressure}")
            self.last_log = time.time()
            time_struct = time.localtime()
            self.time += [f"{time_struct.tm_hour}:{time_struct.tm_min}:{time_struct.tm_sec}"]
        
        if time.time() - self.last_rga_scan >= self.RGA_SCAN_PERIOD:
            self.do_scan()
            self.last_rga_scan = time.time()

    def MeasureTemperature(self):
        Exception("Not Implemented")

    def MeasurePressure(self):
        Exception("Not Implemented")
    
    def TurnOffHeaterAndCooler(self):
        Exception("Not Implemented")
    
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
        self.HEATING_TIME = 20 * 60 #seconds
        self.COOLING_TIME = 40 * 60 #seconds

    def MeasureTemperature(self):
        if len(self.temperature_data) == 0:
            return 1.26, 25
        delta = random.random()
        
        if not self.manual_override:

            if self.current_state == self.states["heating"]:
                return 1.26, self.temperature_data[-1] + delta
            elif self.current_state == self.states["cooling"]:
                return 1.26, self.temperature_data[-1] - delta
            else:
                return 1.26, self.temperature_data[-1]
        else:
    
            if self.heater_on and not self.cooler_on:
                return 1.26, self.temperature_data[-1] + delta
            elif self.cooler_on and not self.heater_on:
                return 1.26, self.temperature_data[-1] - delta
            else:
                return 1.26, self.temperature_data[-1]
            
    def MeasurePressure(self):
        if len(self.pressure_data) == 0:
            return 1.26, 1e-6
        delta = random.random() * 1e-6 * 10
        if not self.manual_override:
            if self.current_state == self.states["heating"]:
                return 1.26, self.pressure_data[-1] + delta
            elif self.current_state == self.states["cooling"]:
                return 1.26, self.pressure_data[-1] - delta
            else:
                return 1.26, self.pressure_data[-1]
        else:
            if self.heater_on and not self.cooler_on:
                return 1.26, self.pressure_data[-1] + delta
            elif self.cooler_on and not self.heater_on:
                return 1.26, self.pressure_data[-1] - delta
            else:
                return 1.26, self.pressure_data[-1]
            
    def TurnOffHeaterAndCooler(self):
        pass

import u3
from LabJackPython import TCVoltsToTemp, LJ_ttK, eDAC, eAIN
import win32api
class CapillaryBakeStandController:
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

        win32api.SetConsoleCtrlHandler(self.EmergencyStop, True)
    
    def EmergencyStop(self, signum, frame):
        self.TurnHeaterOff()
        self.TurnFanOn()

    def MeasureTemperature(self):
        voltage_raw = eAIN(self.device.handle, self.THERMOCOUPLE_CHANNEL)
        voltage = (voltage_raw - self.THERMOCOUPLE_VOLTAGE_OFFSET) / self.THERMOCOUPLE_VOLTAGE_GAIN
        internal_temp = self.device.getTemperature()
        temperature = TCVoltsToTemp(LJ_ttK, voltage, internal_temp)         #K
        #t = (1.8 * t) - 459.67                                             #F
        temperature -= 278.00                                               #K
        return voltage_raw, temperature

    def MeasurePressure(self):
        voltage_raw = eAIN(self.device.handle, self.PRESSURE_SENSOR_CHANNEL)
        pressure = 10**(voltage_raw - 10)
        return voltage_raw, pressure

    def SetVoltageOnDac(self, channel, voltage):
        eDAC(self.device.handle, channel, voltage)

    def TurnFanOn(self):
        super().TurnFanOn()
        self.SetVoltageOnDac(self.COOLER_CHANNEL, self.COOLER_VOLTAGE)

    def TurnFanOff(self):
        super.TurnFanOff()
        self.SetVoltageOnDac(self.COOLER_CHANNEL, 0)

    def TurnHeaterOn(self):
        super().TurnHeaterOn()
        self.SetVoltageOnDac(self.HEATER_CHANNEL, self.HEATER_VOLTAGE)

    def TurnHeaterOff(self):
        super().TurnHeaterOff()
        self.SetVoltageOnDac(self.HEATER_CHANNEL, 0)

    def TurnOffHeaterAndCooler(self):
        self.TurnHeaterOff()
        self.TurnFanOff()


if __name__ == "__main__":
    root = tk.Tk()
    gui = CapillaryBakeStandGui(root)
    gui.root.mainloop()
    