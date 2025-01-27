import bluetooth

# Constants for your device
OUR_DEVICE_NAME = "YourDeviceName"
OUR_DEVICE_ADDRESS = "YourDeviceAddress"

# Discover nearby Bluetooth devices
print(f"Searching for {OUR_DEVICE_NAME}, this will take a few seconds...")
nearby_devices = bluetooth.discover_devices(lookup_names=True)
my_rga = None

# Find the desired device
for addr, name in nearby_devices:
    if addr == OUR_DEVICE_ADDRESS and name == OUR_DEVICE_NAME:
        print(f"Found {OUR_DEVICE_NAME}: {addr} - {name}")
        my_rga = addr
        break

if my_rga is None:
    print("Device not found.")
else:
    # Create a Bluetooth socket and connect to the device
    socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    socket.connect((my_rga, 1))
    print(f"Connected to {OUR_DEVICE_NAME}")

    # Function to build a frame (example)
    def build_frame(command, subcommand, payload):
        frame = bytearray(24)
        frame[0] = 0xA5  # Start byte
        frame[1] = 0x50  # Header byte (request command answer)
        frame[2] = 0x00  # Receiver address
        frame[3] = 0x00  # Sender address
        frame[4] = command
        frame[5] = subcommand
        frame[6:6+len(payload)] = payload
        crc = calc_crc(frame[:-2])
        frame[-2] = crc & 0xFF
        frame[-1] = (crc >> 8) & 0xFF
        return frame

    # Function to calculate CRC (already provided in your code)
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

    # Example command and payload
    command = 0x01
    subcommand = 0x02
    payload = bytearray([0x03, 0x04, 0x05])

    # Build the frame
    frame = build_frame(command, subcommand, payload)

    # Send the frame to the device
    socket.send(frame)
    print("Message sent")

    # Close the socket
    socket.close()
    print("Connection closed")