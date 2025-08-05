import serial
import time
import tkinter as tk


class GUI(tk.Tk):
    def __init__(self, _pump):
        super().__init__()
        self.title("'omnicontrol'")
        self.pump = _pump
        self.speed = tk.StringVar()
        self.speed.set("Speed: N/A")
        self.speed_label = tk.Label(textvariable=self.speed)

        self.power = tk.StringVar()
        self.power.set("Power: N/A")
        self.power_label = tk.Label(textvariable=self.power)

        self.temperature = tk.StringVar()
        self.temperature.set("Temperature: N/A")
        self.temperature_label = tk.Label(textvariable=self.temperature)

        self.start_button = tk.Button(text="Start Pump", command=self.pump.start_pump)
        self.stop_button = tk.Button(text="Stop Pump", command=self.pump.stop_pump)


        self.start_button.grid(row=0)
        self.stop_button.grid(row=1)

        self.speed_label.grid(row=2)
        self.power_label.grid(row=3)
        self.temperature_label.grid(row=4)
        
        self.update()

    def update(self):
        try:
            speed = self.pump.get_rotation_speed()
            power = self.pump.get_power_usage()
            temperature = self.pump.get_temperature()

            self.speed.set(f"Speed: {speed}")
            self.power.set(f"Power: {power}")
            self.temperature.set(f"Temperature: {temperature}")
        except Exception as e:
            print(f"Error updating GUI: {e}")
        
        self.after(1000, self.update)

class PumpBase:
    # Common parameters that represent real pump characteristics
    MAX_SPEED = 1500  # Maximum RPM for this pump model
    ROOM_TEMPERATURE = 25.0  # °C

    def __init__(self):
        # Common state
        self._speed = 0
        self._power = 0.0
        self._temperature = self.ROOM_TEMPERATURE
        self._pumping = False
        self._last_update = time.time()

    def start_pump(self):
        """Start the pump. Implementation should call _on_start() after hardware command."""
        raise NotImplementedError("start_pump must be implemented.")

    def stop_pump(self):
        """Stop the pump. Implementation should call _on_stop() after hardware command."""
        raise NotImplementedError("stop_pump must be implemented.")

    def get_rotation_speed(self):
        """Get current rotation speed."""
        raise NotImplementedError("get_rotation_speed must be implemented.")

    def get_power_usage(self):
        """Get current power usage."""
        raise NotImplementedError("get_power_usage must be implemented.")

    def get_temperature(self):
        """Get current temperature."""
        raise NotImplementedError("get_temperature must be implemented.")

    def is_pumping(self):
        """Check if pump is currently running."""
        return self._pumping

    def _on_start(self):
        """Called after successful pump start."""
        self._pumping = True

    def _on_stop(self):
        """Called after successful pump stop."""
        self._pumping = False

class PfeifferTurboPumpSim(PumpBase):
    # Simulation-specific parameters
    SPEED_INCREASE_RATE = 10  # RPM per update
    SPEED_DECREASE_RATE = 20  # RPM per update
    TEMPERATURE_CHANGE_RATE = 0.1  # °C per update
    MAX_TEMPERATURE_RISE = 15.0  # Maximum °C above room temp
    MAX_POWER = 50.0  # Maximum power usage in Watts

    def __init__(self):
        super().__init__()

    def start_pump(self):
        self._on_start()

    def stop_pump(self):
        self._on_stop()

    def get_rotation_speed(self):
        self._update_sim_state()
        return self._speed

    def get_power_usage(self):
        self._update_sim_state()
        return self._power

    def get_temperature(self):
        self._update_sim_state()
        return self._temperature

    def _update_sim_state(self):
        """Update simulated pump state."""
        now = time.time()
        dt = now - self._last_update
        self._last_update = now

        # Update speed based on pump state
        if self._pumping:
            if self._speed < self.MAX_SPEED:
                self._speed = min(self.MAX_SPEED, self._speed + self.SPEED_INCREASE_RATE)
        else:
            if self._speed > 0:
                self._speed = max(0, self._speed - self.SPEED_DECREASE_RATE)

        # Update power based on speed
        self._power = self.MAX_POWER * (self._speed / self.MAX_SPEED) if self._speed > 0 else 0.0

        # Update temperature based on speed
        target_temp = self.ROOM_TEMPERATURE + (self.MAX_TEMPERATURE_RISE * self._speed / self.MAX_SPEED)
        if self._temperature < target_temp:
            self._temperature = min(target_temp, self._temperature + self.TEMPERATURE_CHANGE_RATE)
        elif self._temperature > target_temp:
            self._temperature = max(target_temp, self._temperature - self.TEMPERATURE_CHANGE_RATE)

class PfeifferTurboPump(PumpBase):
    import serial

    def __init__(self, port='COM6', baudrate=9600, address=1):
        super().__init__()
        self.address = str(address).zfill(3)
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        self.failed_calls = 0

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _calculate_checksum(self, data):
        checksum = sum(ord(c) for c in data) % 256
        return str(checksum).zfill(3)

    def _build_telegram(self, action, parameter, data=None, data_type=None):
        telegram = f"{self.address}{action}0{parameter}"
        if action == 0:
            telegram += "02=?"
        else:
            if data is None:
                raise ValueError("Data is required for commands")
            if data_type is None:
                raise ValueError("Data type is required for commands")
            data_length = str(len(data)).zfill(2)
            telegram += f"{data_length}{data}"
        telegram += self._calculate_checksum(telegram)
        telegram += "\r"
        return telegram.encode('ascii')

    def _send_telegram(self, telegram,expect_response=True):
        try:
            #print(telegram)
            self.ser.write(telegram)
            time.sleep(0.1)
            if expect_response:
                response = b""
                while self.ser.in_waiting > 0:
                    response += self.ser.read(self.ser.in_waiting)
                    time.sleep(0.05)
                return response.decode('ascii')
        except Exception as e:
            print(e)

    def _parse_response(self, response):
        #print(response)
        if not response:
            return {"error": "No response received"}
        if "NO_DEF" in response:
            return {"error": "Parameter does not exist"}
        if "_RANGE" in response:
            return {"error": "Data outside permissible range"}
        if "_LOGIC" in response:
            return {"error": "Logical access error"}
        try:
            data_start = 10
            data_length = int(response[8:10])
            data = response[data_start:data_start + data_length]
            return {"data": data}
        except Exception as e:
            return {"error": f"Error parsing response: {str(e)}"}

    def _reconnect_if_needed(self):
        if self.failed_calls >= 2:
            try:
                self.ser.close()
                time.sleep(1)
                self.ser.open()
                self.failed_calls = 0
            except Exception as e:
                print(e)

    def start_pump(self):
        telegram = self._build_telegram(1, "023", "1", 6)
        response = self._send_telegram(telegram)
        parsed = self._parse_response(response)
        #print(telegram)
        #print(response)
        #print(parsed)

        if "data" in parsed:
            self._on_start()
        return parsed

    def stop_pump(self):
        telegram = self._build_telegram(1, "023", "0", 6)
        response = self._send_telegram(telegram, expect_response=False)
        #parsed = self._parse_response(response)
        #if "data" in parsed:
        self._on_stop()
        #return parsed

    def get_rotation_speed(self):
        telegram = self._build_telegram(0, "309")
        response = self._send_telegram(telegram)
        parsed = self._parse_response(response)
        if "data" in parsed:
            self._speed = int(parsed["data"])
            return self._speed
        return None

    def get_power_usage(self):
        telegram = self._build_telegram(0, "316")
        response = self._send_telegram(telegram)
        parsed = self._parse_response(response)
        #print(parsed)
        if "data" in parsed:
            self._power = float(parsed["data"])
            return self._power
        return None

    def get_temperature(self):
        telegram = self._build_telegram(0, "346")
        #print(telegram)
        response = self._send_telegram(telegram)
        #print(response)
        parsed = self._parse_response(response)
        if "data" in parsed:
            self._temperature = float(parsed["data"])
            return self._temperature
        return None

#pump = PfeifferTurboPump(port='COM4', address=1)
#gui = GUI(pump)
#gui.mainloop()