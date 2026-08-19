from usb_peripheral_bridge import Bridge
from usb_peripheral_bridge.protocol import CMD_PING


with Bridge("/dev/ttyACM0") as bridge:

    result = bridge.command(
        CMD_PING
    )

    print(result)
