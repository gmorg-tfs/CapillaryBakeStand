# simple inquiry example
import bluetooth
import struct
import time 

OUR_DEVICE_ADDRESS = "00:06:66:75:98:66"
OUR_DEVICE_NAME = "NOVION-14908400012"
my_rga = None



print(f"searching for {OUR_DEVICE_NAME} this will take a few seconds")
nearby_devices = bluetooth.discover_devices(lookup_names=True)
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
    pressure, = struct.unpack('<f', payload[:4])
    return pressure

def request_pressure(serial_port):
    command = 0x20
    subcommand = 0x08
    payload = struct.pack('<B', 0)
    print(f"Command: {command}, Subcommand: {subcommand}, Payload: {payload.hex()}")
    frame = build_frame(command, subcommand, payload)
    serial_port.send(frame)
    time.sleep(0.1)
    response = serial_port.recv(24)
    if not response:
        print("No response received")
        return None
    #print(f"Response received: {response.hex()}")
    return parse_response(response)


#find_and_connect()
request_pressure(my_rga)
