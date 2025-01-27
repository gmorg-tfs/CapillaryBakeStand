import u3
import time
import tkinter as tk
import matplotlib.pyplot as plt
import logging

from LabJackPython import TCVoltsToTemp, LJ_ttK, eDAC, eAIN
from Logger import *
from math import log10

class BakerOuter:
    def __init__(self):
        self.device = u3.U3()
        self.number_of_cycles_to_run = 10
        self.start_time = 0
        self.states = {"heating": 1, "cooling": 2}
        self.current_state = 0
        self.pressure_data = []
        self.pressure_data_buffer = []
        self.temperature_data = []
        self.temperature_data_buffer = []
        self.THERMOCOUPLE_VOLTAGE_GAIN = 51
        self.THERMOCOUPLE_VOLTAGE_OFFSET = 1.254 #volts
        self.THERMOCOUPLE_CHANNEL = 6
        self.PRESSURE_SENSOR_CHANNEL = 0
        self.HEATER_CHANNEL = 0
        self.COOLER_CHANNEL = 1
        self.HEATER_VOLTAGE = 5 #volts
        self.COOLER_VOLTAGE = 5 #volts
        self.HEATING_TIME = 20 * 60 #seconds
        self.COOLING_TIME = 40 * 60 #seconds
        self.CONTROL_LOOP_PERIOD = 0.5 #seconds
        self.logger = Logger(_base_path="C:\\Data\\toaster\\",
                             _file_name_base="toaster_data_",
                             _file_extension=".csv",
                             _header="Time, Temperature Voltage (V), Temperature (C), Pressure Voltage (V), Pressure (mbar)")
        self._default_log_frequency = 1 #seconds
        self.last_log = 0
        self.message = ""
        self.relative_temperature_change_to_log = 0.02
        self.relative_pressure_change_to_log = 0.02
        self.fig, self.temperature_axis = plt.subplots()
        self.pressure_axis = self.temperature_axis.twinx()

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

    def StartHeating(self):
        self.current_state = self.states["heating"]
        #print("Heating")
        self.SetVoltageOnDac(self.COOLER_CHANNEL, 0)
        self.SetVoltageOnDac(self.HEATER_CHANNEL, self.HEATER_VOLTAGE)
        self.start_time = time.time()

    def StartCooling(self):
        self.current_state = self.states["cooling"]
        #print("Cooling")
        self.SetVoltageOnDac(self.HEATER_CHANNEL, 0)
        self.SetVoltageOnDac(self.COOLER_CHANNEL, self.COOLER_VOLTAGE)
        self.start_time = time.time()
    
    def LogData(self):
        temperature_voltage_raw, temperature = self.MeasureTemperature()
        pressure_voltage_raw, pressure = self.MeasurePressure()

        self.temperature_data_buffer += [temperature]
        self.pressure_data_buffer += [pressure]

        if len(self.temperature_data_buffer) == 32 and len(self.pressure_data_buffer) == 32:
            temperature_ave = sum(self.temperature_data_buffer) / 32
            pressure_ave = sum(self.pressure_data_buffer) / 32
            self.temperature_data += [temperature_ave]
            self.pressure_data += [pressure_ave] 
            self.temperature_data_buffer = []
            self.pressure_data_buffer = []
            self.message = f"{time.ctime()}, {temperature_voltage_raw}, {self.temperature_data[-1]},  {pressure_voltage_raw}, {self.pressure_data[-1]}"
            
        

        #if len(self.temperature_data) == 0:
        #    self.temperature_data += [temperature]
        #    self.pressure_data += [pressure]
        #    self.last_log = time.time()
        #    self.logger.log(message)
        #    return

        cond1 = time.time() - self.last_log >= self._default_log_frequency
        #cond2 = temperature * self.relative_temperature_change_to_log <= abs(temperature - self.temperature_data[-1])
        #cond3 = pressure * self.relative_pressure_change_to_log <= abs(pressure - self.pressure_data[-1])
        #print(cond1, cond2, cond3)
        #if cond1 or cond2 or cond3:
        if cond1:
            #self.temperature_data += [temperature]
            #self.pressure_data += [pressure]
            #self.last_log = time.time()
            #if self.message != "":
            self.logger.log(self.message)
            self.last_log = time.time()
            #self.logger.log(f"{time.ctime()}, {temperature_voltage_raw}, {temperature},  {pressure_voltage_raw}, {pressure}")
            self.temperature_axis.cla()
            self.pressure_axis.cla()
            self.temperature_axis.plot(self.temperature_data, color='red')
            self.pressure_axis.semilogy(self.pressure_data)
            plt.pause(1e-9)

            #self.temperature_axis.plot(self.temperature_data)
            #self.pressure_axis.plot(self.pressure_data)
        #if len(self.temperature_data) == 0 or len(self.pressure_data) == 0:
        #    return

        #if abs(temperature - self.temperature_data[-1]) >= 1:
        #    self.temperature_axis.cla()
        #    self.temperature_axis.plot(self.temperature_data)
        
        #if abs(pressure - self.pressure_data[-1]) >= 1:
        #    self.pressure_axis.cla()
        #    self.pressure_axis.plot(self.pressure_data)
            #plt.cla()
            #plt.plot(self.temperature_data)
            #plt.plot(self.pressure_data)
            #plt.pause(1e-9)


    def ControlLoop(self):
        cycle_count = 0
        while True:
            if self.current_state == self.states["heating"] and time.time() - self.start_time >= self.HEATING_TIME:
                self.StartCooling()
            elif self.current_state == self.states["cooling"] and time.time() - self.start_time >= self.COOLING_TIME:
                cycle_count += 1
                if cycle_count >= self.number_of_cycles_to_run:
                    break                    
                self.StartHeating()
                    
            self.LogData()

            #time.sleep(self.CONTROL_LOOP_PERIOD)

    def Go(self):
        self.StartHeating()
        self.ControlLoop()

    def Stop(self):
        self.SetVoltageOnDac(self.HEATER_CHANNEL, 0)
        self.SetVoltageOnDac(self.COOLER_CHANNEL, 0)


try:
    bakerouter = BakerOuter()
    #bakerouter.Go()
    #bakerouter.Stop()
    #bakerouter.StartHeating()
    #bakerouter.StartCooling()

    #print(bakerouter.MeasureTemperature()) 
    #print(bakerouter.MeasurePressure())
    #bakerouter.device.setDefaults()


    # GUI 
    root = tk.Tk()
    root.title('Jupiter Capillary Bake Stand')
    window_width = 300
    window_height = 600

    # get the screen dimension
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # find the center point
    center_x = int(screen_width/2 - window_width / 2)
    center_y = int(screen_height/2 - window_height / 2)

    # set the position of the window to the center of the screen
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

    message = tk.Label(root,text="Hello")
    message.pack()

    def quitGUI():
        root.quit()
        bakerouter.Stop()
        quit()

    tk.Button(root, text="Start", command=bakerouter.Go).pack() #button to start the bake stand
    tk.Button(root, text="Quit", command=quitGUI).pack() #button to close the window
    lbl = tk.Label(root, textvariable=bakerouter.message, width=40, height=5, font=('Consolas', 24, 'bold'))
    lbl.pack()
    if __name__ == "__main__":
        logging.basicConfig(filename='./myapp.log', level=logging.DEBUG, 
                        format='%(asctime)s %(levelname)s %(name)s %(message)s')
        logger=logging.getLogger(__name__)

except Exception as e:
    Logger.error("An error occurred: %s", e)
    bakerouter.Stop()
    quit()

root.mainloop()