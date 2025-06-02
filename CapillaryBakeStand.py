import time
import matplotlib.pyplot as plt
from Logger import *
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
from novion import *
from collections import deque
from datetime import date
import traceback
from threading import Thread
import sys

MAX_DATA_POINTS = 2048
def main():
    #controller = CapillaryBakeStandControllerSimulator()
    controller = CapillaryBakeStandController()

    #switch which line is commented out for quick turn off oven turn on fan
    controller.Start()    
    #controller.StartCooling()


class CapillaryBakeStandControllerBase(Thread):
    def __init__(self):
        #state
        self.running = False
        self.thread_running = True
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
        self.thread_running = False
        self.current_state = 0
        self.TurnOffHeaterAndCooler()

    def Start(self):
        self.cycle_count = 0
        self.running = True
        self.thread_running = True
        self.Go()
        self.run()
    
    def Go(self):
        self.StartHeating()
        #self.ControlLoop()

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

            if (self.running and self.logging_complete_event.is_set() and self.TimeForNextLog()) or (time.time() - self.last_log_time >= self.CONTROL_LOOP_TIMEOUT):
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
            print(f"\nError scanning and saving data: {e}")
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
    
    def run(self):
        while self.thread_running:
            try:
                if self.current_state == self.states["heating"] and time.time() - self.start_time >= self.HEATING_TIME:
                    self.StartCooling()
                elif self.current_state == self.states["cooling"] and time.time() - self.start_time >= self.COOLING_TIME:
                    self.cycle_count += 1
                    if self.cycle_count < self.number_of_cycles_to_run:
                        self.StartHeating()
                    else:
                        self.Stop()
                self.MeasureTemperaurePressure()
                self.RGAScanAndSaveData()
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
                state = "Heating" if self.current_state == self.states["heating"] else "Cooling"
                status_msg = (f"Cycle: {self.cycle_count}/{self.number_of_cycles_to_run}, "
                                f"State: {state}, Time remaining: {minutes}:{seconds}, "
                                f"Temperature: {self.last_temperature:.2f}C, "
                                f"Pressure: {self.last_pressure:.2e}torr")
                sys.stdout.write(f"\r{status_msg}   ")
                sys.stdout.flush()
                #print(f"Cycle: {self.cycle_count}/{self.number_of_cycles_to_run}, State: {state}, Time remaining: {minutes}:{seconds}, Temperature: {self.last_temperature:.2f}C, Pressure: {self.last_pressure:.2e}torr",end="\r")

            except Exception as e:
                print(f"\nError in control loop: {e}")
            time.sleep(0.1)



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
    main()
    """
    try:
        root = tk.Tk()
        gui = CapillaryBakeStandGui(root)
        gui.root.mainloop()
    except Exception as e:
        print(f"unhandeled exception: {e}")
        traceback.print_exc()
    """ 
    