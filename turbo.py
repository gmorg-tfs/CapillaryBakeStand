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

class PfeifferTurboPump:    
    def __init__(self, port='COM1', baudrate=9600, address=101):
        self.address = str(address).zfill(3)  # Format as 3 digits
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        
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
        time.sleep(0.1)
        
        response = b""
        while self.ser.in_waiting > 0:
            response += self.ser.read(self.ser.in_waiting)
            time.sleep(0.05)
            
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
            data = response[data_start:data_start+data_length]
            
            return {"data": data}
        except Exception as e:
            return {"error": f"Error parsing response: {str(e)}"}
    
    def is_pumping(self):
        try:
            return self.get_rotation_speed()["speed"] > 0
        except Exception as e:
            return False

    # Control commands
    
    def start_pump(self):
        telegram = self._build_telegram(1, "010", "1", 6)
        response = self._send_telegram(telegram)
        return self._parse_response(response)
    
    def stop_pump(self):
        telegram = self._build_telegram(1, "010", "0", 6)
        response = self._send_telegram(telegram)
        return self._parse_response(response)
    
    def get_rotation_speed(self):
        telegram = self._build_telegram(0, "309")
        response = self._send_telegram(telegram)
        result = self._parse_response(response)
        if "data" in result:
            speed = int(result["data"])
            return speed
        return result
    
    def get_temperature(self):
        telegram = self._build_telegram(0, "326")
        response = self._send_telegram(telegram)
        result = self._parse_response(response)
        if "data" in result:
            temp = float(result["data"])
            return temp
        return result
    
    def get_power_usage(self):
        telegram = self._build_telegram(0, "316")
        response = self._send_telegram(telegram)
        result = self._parse_response(response)
        if "data" in result:
            power = float(result["data"])
            return power
        return result


#print(pump.get_rotation_speed())

#frame = pump._build_telegram(0, "740",data_type=10)
#frame = bytes(b'01100010030302=?101\r')
#frame = bytes(b'0010000902=?104\r')


"""
this worked when only pc was connected to pump
frame = '0010030902=?107\r'
print(frame)
frame = frame.encode('ascii')
print(frame)
response = pump._send_telegram(frame)
result = pump._parse_response(response)
print(result)
"""
def try_find_pump_addr_speed_query():
    pump = PfeifferTurboPump(port='COM4', baudrate=9600, address=122)
    for i in range(400):
        addr = str(i).zfill(3)
        frame = addr + '0030902=?'
        frame += pump._calculate_checksum(frame)
        frame += '\r'
        frame = frame.encode('ascii')
        print(frame)
        response = pump._send_telegram(frame)
        result = pump._parse_response(response)
        if "data" in result:
            print(f"Address: {addr}, Speed: {result['data']}")
    
def try_find_gauge_addr_pressure_query():
    pump = PfeifferTurboPump(port='COM4', baudrate=9600, address=122)
    for i in range(400):
        addr = str(i).zfill(3)
        frame = addr + '0074002=?'
        frame += pump._calculate_checksum(frame)
        frame += '\r'
        frame = frame.encode('ascii')
        print(frame)
        response = pump._send_telegram(frame)
        result = pump._parse_response(response)
        if "data" in result:
            print(f"Address: {addr}, Speed: {result['data']}")



#def main():
    #pump = PfeifferTurboPump(port='COM4', baudrate=9600, address=1)
    #gui = GUI(pump)
    #gui.mainloop()
    #try_find_pump_addr_speed_query()


try_find_pump_addr_speed_query()


#

#try_find_pump_addr_speed_query()
#try_find_gauge_addr_pressure_query()

#pump = PfeifferTurboPump(port='COM4', baudrate=9600, address=1)
#print(pump.get_rotation_speed())
#pump.start_pump()

#error ack
#frame = pump._build_telegram(1, "009", data="1", data_type=0)
#resp = pump._send_telegram(frame)
#print(resp)

#speed = pump.get_rotation_speed()
#power = pump.get_power_usage()
#temperature = pump.get_temperature()
#print(speed)
#print(power)
#print(temperature)
"""
print(f"Speed: {speed['speed']} {speed['unit']}, Power: {power['power']} {power['unit']}, Temperature: {temperature['temperature']} {temperature['unit']}", end='\r')
pump.start_pump()
while True:
    speed = pump.get_rotation_speed()
    power = pump.get_power_usage()
    temperature = pump.get_temperature()
    print(f"Speed: {speed['speed']} {speed['unit']}, Power: {power['power']} {power['unit']}, Temperature: {temperature['temperature']} {temperature['unit']}", end='\r')
    time.sleep(1)
#gauge responded to b'1220074002=?110\r'
'''
frame = '0220074002=?'
frame += pump._calculate_checksum(frame)
frame += '\r'

#frame = '0010030902=?107\r'
#print(frame)
frame = frame.encode('ascii')
#print(frame)
response = pump._send_telegram(frame)
result = pump._parse_response(response)
print(result)
'''
#measure pump temperature 0010033002=?101\r
#meausre pump speed 0010030902=?107\r
#address = 001
#action 00
#parameter = 309
#data length = 02
#rsponse            0011030906001500026\r

#b'01100010030302=?101\r
"""