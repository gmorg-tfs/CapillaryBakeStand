import struct
import time 
import serial
import numpy as np
import matplotlib.pyplot as plt
from Logger import * 

class NovionRGA:
    def __init__(self, com_port="COM5", baud_rate=115200):
        self.serial_port = serial.Serial(com_port, baud_rate, timeout=1)
        self.mass_start = 1
        self.mass_end = 75
        self.header = "Time (s),pressure (mbar),Temperature (C),"
        for i in range(self.mass_start, self.mass_end+1):
            self.header += f"{i},"
        self.header = self.header[:-1]

        self.logger = Logger(_base_path="C:\\Data\\toaster\\",
                             _file_name_base="toaster_rga_data_",
                             _file_extension=".csv",
                             _header= self.header)
        
        self.intensitys = np.zeros(self.mass_end-self.mass_start+1)
        self.mass_numbers = np.zeros(self.mass_end-self.mass_start+1)

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
            raise ValueError("Invalid response length")
        crc_received = response[22] | (response[23] << 8)
        crc_calculated = self.calc_crc(response[:22])
        if crc_received != crc_calculated:
            raise ValueError("CRC mismatch")
        payload = response[6:22]
        return payload

    def send_command(self, command, subcommand, payload=struct.pack('<B', 0x00)):
        #print(f"Command: {command}, Subcommand: {subcommand}, Payload: {payload.hex()}")
        frame = self.build_frame(command, subcommand, payload)
        self.serial_port.write(frame)
        while self.serial_port.in_waiting != 24:
            pass
        response = self.serial_port.read(24)
        if not response:
            print("No response received")
            return None
        return self.parse_response(response)

    def request_pressure(self):
        command = 0x20
        subcommand = 0x08
        data = self.send_command(command, subcommand)
        pressure, = struct.unpack('<f', data[:4])
        return pressure

    def request_number_of_points_available(self):
        command = 0x81
        subcommand = 0x3f
        data = self.send_command(command, subcommand)
        n, = struct.unpack('<i', data[:4])
        return n

    def request_next_point(self):
        command = 0x81
        subcommand = 0x3A
        data = self.send_command(command, subcommand)
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
        mass_number, = struct.unpack('<f', data[:4])
        return mass_number

    def get_scan_end(self):
        command = 0x81
        subcommand = 0x15
        data = self.send_command(command, subcommand)
        mass_number, = struct.unpack('<f', data[:4])
        return mass_number

    def set_scan_range(self, start_mass_number, end_mass_number):
        self.set_scan_start(start_mass_number)
        self.set_scan_end(end_mass_number)
        #assert get_scan_start(serial_port) == start_mass_number
        #assert get_scan_end(serial_port) == end_mass_number

    def scan(self, temperature_data):
        pressure = self.request_pressure()
        temperature = temperature_data[-1]
        n = self.request_number_of_points_available()
        for _ in range(n):
            ID_spec_intensity, ID_spec_mass_number, intensity, mass_number, tuple_number = self.request_next_point()
            self.intensitys[tuple_number] = intensity
            self.mass_numbers[tuple_number] = mass_number
        data_str = f"{time.time()},{pressure},{temperature},"
        for i in self.intensitys:
            data_str += f"{i},"
        data_str = data_str[:-1]
        self.logger.log(data_str)

""" 
start = time.time()
n = request_number_of_points_available(serial_port)
for _ in range(n):
    request_next_point(serial_port)
end = time.time()
print(f"Time taken: {end - start}")
 """

#set_scan_range(serial_port, 1, 75)
""" 
intensity_over_time = {}

intensitys = np.zeros(mass_end-mass_start+1)
mass_numbers = np.zeros(mass_end-mass_start+1)
while True:
    n = request_number_of_points_available(serial_port)
    for i in range(n):
        ID_spec_intensity, ID_spec_mass_number, intensity, mass_number, tuple_number = request_next_point(serial_port)
        intensitys[tuple_number] = intensity
        mass_numbers[tuple_number] = mass_number
    plt.cla()
    plt.plot(mass_numbers, intensitys)
    plt.xlabel("Mass (amu)")
    plt.ylabel("Intensity")
    plt.title(tuple_number)
    plt.pause(1e-9)

    data_str = ""
    for i in intensitys:
        data_str += f"{i},"
    data_str = data_str[:-1]

    logger.log(data_str)
 """"""     idx = np.argsort(intensitys)
    most_intense = mass_numbers[idx[-5:]]
    mass_with_most_intensity = mass_numbers[idx[-5:]]

    for i, m in zip(most_intense, mass_with_most_intensity):
        if int(m) in intensity_over_time:
            intensity_over_time[int(m)] += [i]
        else:
            intensity_over_time[int(m)] = [i]

    print(intensity_over_time[18]) """
    #print(f"Top 5 peaks: {mass_numbers[idx[-5:]]}")
    #print(f"Top 5 intensities: {intensitys[i]}")
    #break
#plt.show()
