import time
import struct
from usb_peripheral_bridge import Bridge
from usb_peripheral_bridge.protocol import *

# ==========================================
# CONSTANTS & PARAMETERS
# ==========================================
I2C_ADDRESS = 0x27  # PCF8574T I2C address (try 0x3F if 0x27 does not work)
STOP_BIT    = 0x01  # 1: STOP signal required at the end of I2C transaction

# PCF8574 bit mapping for HD44780 LCD:
# Bit 0: RS (0: Command, 1: Data)
# Bit 1: RW (0: Write)
# Bit 2: EN (Enable pulse)
# Bit 3: Backlight (1: ON)
# Bits 4-7: D4-D7 data lines
MASK_RS_DATA   = 0b00000001
MASK_ENABLE    = 0b00000100
MASK_BACKLIGHT = 0b00001000

# ==========================================
# LOW-LEVEL I2C OPERATIONS
# ==========================================
def i2c_write_byte(bridge, data_byte: int):
    """
    Sends a single byte to the PCF8574 IC according to the protocol specification.
    Payload structure: [I2C Address, Stop Flag, Data Length, Data Bytes...]
    """
    payload = bytes([I2C_ADDRESS, STOP_BIT, 1, data_byte])
    raw_response = bridge.command(CMD_I2C_WRITE, payload=payload)
    
    if not raw_response or raw_response[0] != 0x00:
        raise RuntimeError(f"I2C write error! Response: {raw_response}")

# ==========================================
# LCD CONTROL FUNCTIONS
# ==========================================
def lcd_write_nibble(bridge, nibble: int, mode: int = 0):
    """
    Sends a 4-bit nibble to the LCD accompanied by an Enable pulse.
    """
    byte_to_send = mode | (nibble & 0xF0) | MASK_BACKLIGHT
    
    # Set EN to High
    i2c_write_byte(bridge, byte_to_send | MASK_ENABLE)
    
    # Set EN to Low (LCD latches data on falling edge)
    i2c_write_byte(bridge, byte_to_send & ~MASK_ENABLE)

def lcd_send_byte(bridge, value: int, mode: int = 0):
    """
    Sends an 8-bit command or data byte in two 4-bit steps (High nibble, then Low nibble).
    """
    lcd_write_nibble(bridge, value & 0xF0, mode)          # High nibble
    lcd_write_nibble(bridge, (value << 4) & 0xF0, mode)   # Low nibble
    time.sleep(0.00005) #50 usec

def lcd_init(bridge):
    """
    Initializes the HD44780 LCD in 4-bit I2C mode.
    """
    time.sleep(0.05)
    
    # Force 4-bit mode initialization sequence
    lcd_write_nibble(bridge, 0x30)
    time.sleep(0.005) # 4 msec
    lcd_write_nibble(bridge, 0x30)
    time.sleep(0.0001) # 100 usec
    lcd_write_nibble(bridge, 0x30)
    time.sleep(0.0001) # 100 usec
    lcd_write_nibble(bridge, 0x20)
    time.sleep(0.0001) # 100 usec
    
    # Function set & display settings
    lcd_send_byte(bridge, 0x28)  # 4-bit mode, 2 lines, 5x8 font
    lcd_send_byte(bridge, 0x0C)  # Display ON, Cursor OFF, Blink OFF
    lcd_send_byte(bridge, 0x01)  # Clear display
    time.sleep(0.002) # 2 msec
    lcd_send_byte(bridge, 0x06)  # Entry mode: Move cursor right

def lcd_print(bridge, text: str, line: int = 1):
    """
    Prints a text string on line 1 or line 2 of the display.
    """
    addr = 0x80 if line == 1 else 0xC0
    lcd_send_byte(bridge, addr)  # Set cursor position
    
    for char in text:
        lcd_send_byte(bridge, ord(char), MASK_RS_DATA)

# ==========================================
# MAIN PROGRAM
# ==========================================
def main():
    # Adjust port name according to your system (e.g., /dev/ttyACM0 or COM3)
    port = "/dev/ttyACM0"
    
    with Bridge(port) as bridge:
        
        print("Initializing LCD...")
        lcd_init(bridge)
        
        
        print("Printing text...")
        lcd_print(bridge, "USB/I2C  Bridge", line=1)
        lcd_print(bridge, "HD44780 1602 LCD", line=2)
        
        print("Done! The text should now be visible on the display.")

if __name__ == "__main__":
    main()
    
