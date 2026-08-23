from usb_peripheral_bridge import Bridge
from usb_peripheral_bridge.protocol import *

with Bridge("/dev/ttyACM0") as bridge:


    for address in bridge.scan():

        print(
            f"I2C device: 0x{address:02X}"
        )
