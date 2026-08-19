import struct
from usb_peripheral_bridge import Bridge
from usb_peripheral_bridge.protocol import *

# ==========================================
# PARAMETERS
# ==========================================
CLOCK_SPEED = 100000  # 100 kHz Base I2C clock

# ==========================================
# 32-BIT INT CONVERSION TO 4 BYTES (LITTLE-ENDIAN)
# ==========================================
# Option A: Using the 'struct' module
# '<I' meaning: < = Little-Endian, I = unsigned 32-bit int
clock_bytes = struct.pack('<I', CLOCK_SPEED)

# Option B: Simply by the int.to_bytes method (with the same result)
# clock_bytes = CLOCK_SPEED.to_bytes(4, byteorder='little')


# ==========================================
# MAIN PROGRAM
# ==========================================
with Bridge("/dev/ttyACM0") as bridge:
    # A payload consists directly 4 bytes
    raw_response = bridge.command(
        CMD_SET_CLOCK,
        payload=clock_bytes
    )

    # Processing the result
    status_code = raw_response[0] if len(raw_response) > 0 else None

    # Just for checking printing out the TX bytes
    hex_payload = ' '.join(f'0x{b:02X}' for b in clock_bytes)

    print("=" * 50)
    print("         SETTING I2C CLOCK SPEED         ")
    print("=" * 50)
    print(f" Clock Value     : {CLOCK_SPEED} Hz ({CLOCK_SPEED / 1000:.0f} kHz)")
    print(f" Sent bytes      : [ {hex_payload} ]")
    print(f" Status response : 0x{status_code:02X}" if status_code is not None else " No response")
    print("=" * 50)
