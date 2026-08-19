from usb_peripheral_bridge import Bridge
from usb_peripheral_bridge.protocol import *

with Bridge("/dev/ttyACM0") as bridge:
    result = bridge.command(CMD_GET_INFO)

    # Making sure that the expected 7 bytes have arrived
    if len(result) >= 7:
        protocol_version = result[0]
        max_payload_size = result[1]
        flags = result[2]
        wire_buffer_size = result[3]

        
        # Join the three bytes and decode it as text
        mcu_id = result[4:7].decode('ascii')

        print(f"Protokoll verzió: {protocol_version}")
        print(f"Max Payload:      {max_payload_size} bájt")
        print(f"Flags:            {flags:#010b}")  # Bináris formátumban
        print(f"Wire Buffer:      {wire_buffer_size} bájt")
        print(f"MCU Azonosító:    {mcu_id}")
    else:
        print("Error: Not enough data arrived!")
