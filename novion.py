import struct
import time 
import serial
import numpy as np
from Logger import * 
import random


HELIUM_MODE = 3
RGA_MODE = 2

ION_GUAGE_ACTIVE = 2

NAK_MASK = 0b00010000

NAK_ERROR = 1
INVALID_RESPONSE_LENGTH_ERROR = 2
CRC_ERROR = 3
NO_RESPONSE_ERROR = 4

TIMEOUT_SECONDS = 0.5

class NovionBase:
    def __init__(self):
        self.mass_start = 1
        self.mass_end = 75  
        self.intensitys = np.zeros(self.mass_end-self.mass_start+1)
        self.mass_numbers = np.zeros(self.mass_end-self.mass_start+1)
        self.water_percentage = 0
        self.mode = 0
        self.scanning = False
        self.water_17 = 0
        self.water_18 = 0
        self.water_19 = 0

    def get_water_content(self):
        return self.water_17 + self.water_18 + self.water_19
    
    def request_pressure(self):
        Exception("Not Implemented")
    def request_number_of_points_available(self):
        Exception("Not Implemented")
    def request_next_point(self):
        Exception("Not Implemented")
    
    def change_to_he_leak_detector(self):
        Exception("Not Implemented")
    
    def change_to_rga(self):
        Exception("Not Implemented")
    
    def get_mode(self):
        Exception("Not Implemented")

    def get_he_value(self):
        Exception("Not Implemented")
    
    def get_active_pressure_sensor(self):
        Exception("Not Implemented")
    
    def can_scan(self):
        return self.get_active_pressure_sensor() == ION_GUAGE_ACTIVE
    
    def scan(self):
        n = self.request_number_of_points_available()
        data = np.zeros(self.mass_end-self.mass_start+1)
        if n == self.mass_end-self.mass_start+1:
            for _ in range(n):
                next_point = self.request_next_point()
                if next_point is None:
                    break #received a partial spectrum?
                ID_spec_intensity, ID_spec_mass_number, intensity, mass_number, tuple_number = next_point
                data[int(mass_number)-1] = intensity
                mn = int(mass_number)
                if mn == 17:
                    self.water_17 = intensity
                elif mn == 18:
                    self.water_18 = intensity
                elif mn == 19:
                    self.water_19 = intensity

        data_str = ",".join(map(str,data))
        return data_str


class NovionMock(NovionBase):
    def __init__(self):
        super().__init__()
        intensitys_str = "0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.038124219	0.001027685	0.001132719	0.003903615	0.016281854	0.044268493	0.062740408	0.048465732	0.026517047	0.018924827	0.016276499	0.012127393	0.00686728	0.003944158	0.002492747	0.001822589	0.00160905	0.001741622	0.002057489	0.002830798	0.004359233	0.006089322	0.006777898	0.005983817	0.004155815	0.002598252	0.0016543	0.001040925	0.000689752	0.000458384	0.000341875	0.000267734	0.000194416	0.000169114	0.000166289	0.000170643	0.000152065	0.000182926	0.000235696	0.000287523	0.000365028	0.000426985	0.000430872	0.000426631	0.000375629	0.000302364	0.000240171	0.000200477	0.000179864	0.000121794	0.000129568	0.000105774	0.000104125	0.000105303"
        self.masses = np.arange(1, 76)
        self.intensitys = np.array([float(i) for i in intensitys_str.split("\t")])
        self.current_index = 0
        self.mode = RGA_MODE
        self.random_error_threshold = 0.95
        self.random_next_point_error_threshold = 0.99

    def random_intrument_response_time(self):
        time.sleep(0.05 + random.random() % 0.1)

    def request_pressure(self):
        self.random_intrument_response_time()
        if random.random() > self.random_error_threshold:
            return None
        return 1e-6 * random.random() * 10

    def request_number_of_points_available(self):
        self.random_intrument_response_time()
        if random.random() > self.random_error_threshold:
            return None
        return 75

    def request_next_point(self):
        self.random_intrument_response_time()
        if random.random() > self.random_next_point_error_threshold:
            return None
        i = self.intensitys[self.current_index]
        m = self.masses[self.current_index]
        t = self.current_index
        self.current_index += 1
        self.current_index %= 75
        return 0, 0, i, m, t
    
    def change_to_he_leak_detector(self):
        self.random_intrument_response_time()
        self.mode = HELIUM_MODE
    
    def change_to_rga(self):
        self.random_intrument_response_time()
        self.mode = RGA_MODE

    def get_mode(self):
        self.random_intrument_response_time()
        return self.mode

    def get_he_value(self):
        self.random_intrument_response_time()
        if random.random() > self.random_error_threshold:
            return None
        helium_value = random.random() * 10**-10
        return helium_value

    def get_active_pressure_sensor(self):
        return self.mode

class NovionRGA(NovionBase):
    def __init__(self, com_port="COM3", baud_rate=115200):
        super().__init__()
        self.com = com_port
        self.baud = baud_rate
        self.serial_port = serial.Serial(com_port, baud_rate, timeout=1)
        self.mode = self.get_mode()
        self.failed_calls = 0



    def crc16_update(self, crc, a):
        i = 8
        crc ^= a
        while i != 0:
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc = crc >> 1
            i -= 1
        return crc

    def calc_crc(self, data):
        crc = 0xFFFF
        for byte in data:
            crc = self.crc16_update(crc, byte)
        return crc

    def build_frame(self, command, subcommand, payload):
        frame = bytearray(24)
        frame[0] = 0xA5  # Start byte
        frame[1] = 0x50  # Header byte (request command answer)
        frame[2] = 0x00  # Receiver address
        frame[3] = 0x00  # Sender address
        frame[4] = command
        frame[5] = subcommand
        frame[6:22] = payload.ljust(16, b'\x00')  # Payload
        crc = self.calc_crc(frame[:22])
        frame[22] = crc & 0xFF
        frame[23] = (crc >> 8) & 0xFF
        return frame

    def parse_response(self, response):
        if len(response) != 24:
            print(f"Invalid response length: {len(response)}")
            return None
        header = response[1]
        if header & NAK_MASK == 0:
            return None
        crc_received = response[22] | (response[23] << 8)
        crc_calculated = self.calc_crc(response[:22])
        if crc_received != crc_calculated:
            return None
        payload = response[6:22]
        return payload

    def send_command(self, command, subcommand, payload=struct.pack('<B', 0x00)):
        #print(f"Command: {command}, Subcommand: {subcommand}, Payload: {payload.hex()}")
        frame = self.build_frame(command, subcommand, payload)
        self.serial_port.write(frame)
        start = time.time()
        while self.serial_port.in_waiting != 24 and time.time() - start < TIMEOUT_SECONDS:
            time.sleep(0.01)

        response = self.serial_port.read(24)
        if not response:
            #print("No response received")
            return NO_RESPONSE_ERROR
        
        return self.parse_response(response)
    
    def data_check(self, data):
        if data is not None:
            return data
        
        if data is None and self.failed_calls >= 2:
            try:
                print("novion lost communication")
                self.serial_port.close()
                time.sleep(1)
                self.serial_port = serial.Serial(self.com, self.baud)
                self.failed_calls = 0
                print("novion reconnected?")
            except Exception as e:
                print(e)
                print("novion failed to reconnect")
            return None
            
        elif data is None and self.failed_calls < 2:
            self.failed_calls+=1
            print("novion failed to respond correctly")

        return None

    def request_pressure(self):
        command = 0x20
        subcommand = 0x08
        data = self.send_command(command, subcommand)
        if self.data_check(data) is None:
            return data
        pressure, = struct.unpack('<f', data[:4])
        return pressure
    
    def get_active_pressure_sensor(self):
        command = 0x83
        subcommand = 0x02
        data = self.send_command(command, subcommand)
        if self.data_check(data) is None:
            return data
        sensor, = struct.unpack('<i', data[:4])
        return sensor

    def request_number_of_points_available(self):
        command = 0x81
        subcommand = 0x3f
        data = self.send_command(command, subcommand)
        if self.data_check(data) is None:
            return data
        n, = struct.unpack('<i', data[:4])
        return n

    def request_next_point(self):
        command = 0x81
        subcommand = 0x3A
        data = self.send_command(command, subcommand)
        if self.data_check(data) is None:
            return data
        ID_spec_intensity, ID_spec_mass_number, intensity, mass_number, tuple_number = struct.unpack('<hhffI', data) #this is cool
        return ID_spec_intensity, ID_spec_mass_number, intensity, mass_number, tuple_number

    def set_scan_start(self, mass_number):
        if mass_number < 0 or mass_number > 300:
            print("Invalid mass number")
            return 
        command = 0x81
        subcommand = 0x11
        payload = struct.pack('<f', mass_number)
        self.send_command(command, subcommand, payload)

    def set_scan_end(self, mass_number):
        if mass_number < 0 or mass_number > 300:
            print("Invalid mass number")
            return 
        command = 0x81
        subcommand = 0x12
        payload = struct.pack('<f', mass_number)
        self.send_command(command, subcommand, payload)


    def get_scan_start(self):
        command = 0x81
        subcommand = 0x14
        data = self.send_command(command, subcommand)
        if self.data_check(data) is None:
            return data
        mass_number, = struct.unpack('<f', data[:4])
        return mass_number

    def get_scan_end(self):
        command = 0x81
        subcommand = 0x15
        data = self.send_command(command, subcommand)
        if self.data_check(data) is None:
            return data
        mass_number, = struct.unpack('<f', data[:4])
        return mass_number

    def set_scan_range(self, start_mass_number, end_mass_number):
        self.set_scan_start(start_mass_number)
        self.set_scan_end(end_mass_number)

    def change_to_he_leak_detector(self):
        command = 0x81
        subcommand = 0x39
        payload = struct.pack('<B', 0x03)
        self.send_command(command, subcommand, payload)
        self.mode = self.get_mode()

    def change_to_rga(self):
        command = 0x81
        subcommand = 0x39
        payload = struct.pack('<B', 0x02)
        self.send_command(command, subcommand, payload)
        self.mode = self.get_mode()

    def get_mode(self):
        command = 0x81
        subcommand = 0x38
        data = self.send_command(command, subcommand)
        if self.data_check(data) is None:
            return data
        mode, = struct.unpack('<i', data[:4])
        return mode
    
    def get_he_value(self):
        command = 0x81
        subcommand = 0x31
        data = self.send_command(command, subcommand)
        if self.data_check(data) is None:
            return data
        helium_value, = struct.unpack('<f', data[:4])
        return helium_value
        


