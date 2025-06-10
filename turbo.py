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

            self.speed.set(f"Speed: {speed['speed']} {speed['unit']}")
            self.power.set(f"Power: {power['power']} {power['unit']}")
            self.temperature.set(f"Temperature: {temperature['temperature']} {temperature['unit']}")
        except Exception as e:
            print(f"Error updating GUI: {e}")
        
        self.after(1000, self.update)

class PumpBase:
    def start_pump(self):
        raise NotImplementedError("start_pump must be implemented.")

    def stop_pump(self):
        raise NotImplementedError("stop_pump must be implemented.")

    def get_rotation_speed(self):
        raise NotImplementedError("get_rotation_speed must be implemented.")

    def get_power_usage(self):
        raise NotImplementedError("get_power_usage must be implemented.")

    def get_temperature(self):
        raise NotImplementedError("get_temperature must be implemented.")
    
    def is_pumping(self):
        try:
            return self.get_rotation_speed() > 0
        except Exception as e:
            return False

class PfeifferTurboPumpSim(PumpBase):
    def __init__(self):
        self._speed = 0
        self._power = 0.0
        self._temperature = 25.0
        self._pumping = False

    def start_pump(self):
        self._pumping = True
        self._speed = 0

    def stop_pump(self):
        self._pumping = False
        self._speed = 0

    def get_rotation_speed(self):
        if self._pumping:
            if self._speed < 1500:
                self._speed += 10  # Simulate speed increase
        return self._speed

    def get_power_usage(self):
        if self._pumping:
            self._power = 50.0  # Simulate constant power usage
        else:
            self._power = 0.0
        return self._power

    def get_temperature(self):
        # Simulate the temperature changing slowly
        if self._pumping:
            if self._temperature < 12:
                self._temperature += 0.1
        return self._temperature


class PfeifferTurboPump(PumpBase):
    import serial
    import time

    def __init__(self, port='COM1', baudrate=9600, address=101):
        import serial
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

    def _send_telegram(self, telegram):
        self.ser.write(telegram)
        self.time.sleep(0.1)
        response = b""
        while self.ser.in_waiting > 0:
            response += self.ser.read(self.ser.in_waiting)
            self.time.sleep(0.05)
        return response.decode('ascii')

    def _parse_response(self, response):
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
        # Basic attempt to reconnect if needed
        if self.failed_calls >= 2:
            try:
                self.ser.close()
                self.time.sleep(1)
                self.ser.open()
                self.failed_calls = 0
            except Exception as e:
                print(e)

    def start_pump(self):
        telegram = self._build_telegram(1, "010", "1", 6)
        response = self._send_telegram(telegram)
        parsed = self._parse_response(response)
        return parsed

    def stop_pump(self):
        telegram = self._build_telegram(1, "010", "0", 6)
        response = self._send_telegram(telegram)
        parsed = self._parse_response(response)
        return parsed

    def get_rotation_speed(self):
        telegram = self._build_telegram(0, "309")
        response = self._send_telegram(telegram)
        parsed = self._parse_response(response)
        if "data" in parsed:
            return int(parsed["data"])
        else:
            return None

    def get_power_usage(self):
        telegram = self._build_telegram(0, "316")
        response = self._send_telegram(telegram)
        parsed = self._parse_response(response)
        if "data" in parsed:
            return float(parsed["data"])
        else:
            return None

    def get_temperature(self):
        telegram = self._build_telegram(0, "326")
        response = self._send_telegram(telegram)
        parsed = self._parse_response(response)
        if "data" in parsed:
            return float(parsed["data"])
        else:
            return None