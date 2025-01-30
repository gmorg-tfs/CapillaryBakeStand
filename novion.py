# simple inquiry example
#import bluetooth
import struct
import time 
import serial
import numpy as np
import matplotlib.pyplot as plt
"""
so it looks like you connect computer to the device via bluetooth (like you would connect to wifi) and then use like serial port
in device manager look under bluetooth and you should see novion and then in COM ports you should see standard serial over blutooth link if not try turning computer blutooth off and on 
or remove device and try to rediscover and connect
"""
com_port = "COM5"
baud_rate = 115200
serial_port = serial.Serial(com_port, baud_rate, timeout=1)


"""
OUR_DEVICE_ADDRESS = "00:06:66:75:98:66"
OUR_DEVICE_NAME = "NOVION-14908400012"
my_rga = None

service_matches = bluetooth.find_service(address=OUR_DEVICE_ADDRESS)
print(service_matches)

socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
socket.connect((OUR_DEVICE_ADDRESS, "1"))
print("hi")
#first_match = service_matches[0]
#port = first_match["port"]
#name = first_match["name"]
#host = first_match["host"]

#sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
#sock.connect((host, port))

print(f"searching for {OUR_DEVICE_NAME} this will take a few seconds")
nearby_devices = bluetooth.discover_devices(lookup_names=True, lookup_class=True)
print(nearby_devices)
i = 0
for addr, name in nearby_devices:

    if addr == OUR_DEVICE_ADDRESS and name == OUR_DEVICE_NAME:
        print(f"Found novion: {addr} - {name}")
        my_rga = nearby_devices[i]
        break
    i += 1

print(my_rga)

socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
if my_rga is not None:
    socket.connect((my_rga[0], 1))
"""

def crc16_update(crc, a):
    i = 8
    crc ^= a
    while i != 0:
        if crc & 1:
            crc = (crc >> 1) ^ 0xA001
        else:
            crc = crc >> 1
        i -= 1
    return crc

def calc_crc(data):
    crc = 0xFFFF
    for byte in data:
        crc = crc16_update(crc, byte)
    return crc

def build_frame(command, subcommand, payload):
    frame = bytearray(24)
    frame[0] = 0xA5  # Start byte
    frame[1] = 0x50  # Header byte (request command answer)
    frame[2] = 0x00  # Receiver address
    frame[3] = 0x00  # Sender address
    frame[4] = command
    frame[5] = subcommand
    #frame[6:22] = 0x00
    frame[6:22] = payload.ljust(16, b'\x00')  # Payload
    crc = calc_crc(frame[:22])
    frame[22] = crc & 0xFF
    frame[23] = (crc >> 8) & 0xFF
    #print(f"Frame being sent: {frame.hex()}")
    return frame

def parse_response(response):
    if len(response) != 24:
        print(f"Invalid response length: {len(response)}")
        raise ValueError("Invalid response length")
    crc_received = response[22] | (response[23] << 8)
    crc_calculated = calc_crc(response[:22])
    if crc_received != crc_calculated:
        raise ValueError("CRC mismatch")
    payload = response[6:22]
    #payload = response[6:22].hex()
    #data = [hex(b) for b in response[6:22]]
    #pressure, = struct.unpack('<f', payload[:4])
    return payload
    #return data

def request_pressure1(serial_port):
    command = 0x20
    subcommand = 0x08
    payload = struct.pack('<B', 0x00)
    #print(f"Command: {command}, Subcommand: {subcommand}, Payload: {payload.hex()}")
    frame = build_frame(command, subcommand, payload)
    serial_port.write(frame)
    time.sleep(0.1)
    response = serial_port.read(24)
    if not response:
        print("No response received")
        return None
    #print(f"Response received: {response}")
    return parse_response(response)

def send_command(serial_port, command, subcommand, payload=struct.pack('<B', 0x00)):
    #print(f"Command: {command}, Subcommand: {subcommand}, Payload: {payload.hex()}")
    frame = build_frame(command, subcommand, payload)
    serial_port.write(frame)
    while serial_port.in_waiting != 24:
        pass
    #time.sleep(0.1)## THIS IS WHY ITS SLOW!!!! 32 seconds for 300 points is 0.16 seconds per point
    #300 * 0.1 = 30 seconds
    response = serial_port.read(24)
    if not response:
        print("No response received")
        return None
    #print(f"Response received: {[hex(b) for b in response]}")
    #print(f"payload: {response[6:22].hex()}")
    return parse_response(response)

def request_pressure(serial_port):
    command = 0x20
    subcommand = 0x08
    data = send_command(serial_port, command, subcommand)
    pressure, = struct.unpack('<f', data[:4])
    return pressure


def request_number_of_points_available(serial_port):
    command = 0x81
    subcommand = 0x3f
    data = send_command(serial_port, command, subcommand)
    n, = struct.unpack('<i', data[0:4])
    return n

def request_next_point(serial_port):
    command = 0x81
    subcommand = 0x3A
    data = send_command(serial_port, command, subcommand)
    ID_spec_intensity, ID_spec_mass_number, intensity, mass_number, tuple_number = struct.unpack('<hhffI', data) #this is cool
    return ID_spec_intensity, ID_spec_mass_number, intensity, mass_number, tuple_number


def set_scan_start(serial_port, mass_number):
    if mass_number < 0 or mass_number < 300:
        print("Invalid mass number")
        return 
    command = 0x81
    subcommand = 0x11
    payload = struct.pack('<f', mass_number)
    send_command(serial_port, command, subcommand, payload)

def set_scan_end(serial_port, mass_number):
    if mass_number < 0 or mass_number < 300:
        print("Invalid mass number")
        return 
    command = 0x81
    subcommand = 0x12
    payload = struct.pack('<f', mass_number)
    send_command(serial_port, command, subcommand, payload)


def get_scan_start(serial_port):
    command = 0x81
    subcommand = 0x14
    data = send_command(serial_port, command, subcommand)
    mass_number, = struct.unpack('<f', data)
    return mass_number

def get_scan_end(serial_port):
    command = 0x81
    subcommand = 0x15
    data = send_command(serial_port, command, subcommand)
    mass_number, = struct.unpack('<f', data)
    return mass_number


def set_scan_range(serial_port, start_mass_number, end_mass_number):
    set_scan_start(serial_port, start_mass_number)
    set_scan_end(serial_port, end_mass_number)
    assert get_scan_start(serial_port) == start_mass_number
    assert get_scan_end(serial_port) == end_mass_number


""" 
start = time.time()
n = request_number_of_points_available(serial_port)
for _ in range(n):
    request_next_point(serial_port)
end = time.time()
print(f"Time taken: {end - start}")
 """

set_scan_range(serial_port, 1, 75)

intensity_over_time = {}

intensitys = np.zeros(300)
mass_numbers = np.zeros(300)
while True:
    n = request_number_of_points_available(serial_port)
    for i in range(n):
        plt.cla()
        D_spec_intensity, ID_spec_mass_number, intensity, mass_number, tuple_number = request_next_point(serial_port)
        intensitys[tuple_number] = intensity
        mass_numbers[tuple_number] = mass_number
        plt.plot(mass_numbers[:tuple_number], intensitys[:tuple_number]) #only plot points that have data
        plt.title(tuple_number)
        plt.pause(1e-9)

    idx = np.argsort(intensitys)
    most_intense = mass_numbers[idx[-5:]]
    mass_with_most_intensity = mass_numbers[idx[-5:]]

    for i, m in zip(most_intense, mass_with_most_intensity):
        if str(m) in intensity_over_time:
            intensity_over_time[str(m)] += [i]
        else:
            intensity_over_time[str(m)] = [i]

    print(intensity_over_time)
    #print(f"Top 5 peaks: {mass_numbers[idx[-5:]]}")
    #print(f"Top 5 intensities: {intensitys[i]}")
    #break
plt.show()
