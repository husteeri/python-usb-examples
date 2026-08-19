import time
from datetime import datetime
from usb_peripheral_bridge import Bridge
from usb_peripheral_bridge.protocol import *

# ==========================================
# CONSTANTS / PARAMETERS
# ==========================================
I2C_ADDRESS = 0x3C
STOP_BIT    = 0x01

CTRL_COMMAND_MULTI = 0x00
CTRL_DATA_STREAM    = 0x40

FONT_DIGITS = {
    '0': [0x3E, 0x51, 0x49, 0x45, 0x3E],
    '1': [0x00, 0x42, 0x7F, 0x40, 0x00],
    '2': [0x42, 0x61, 0x51, 0x49, 0x46],
    '3': [0x21, 0x41, 0x45, 0x4B, 0x31],
    '4': [0x18, 0x14, 0x12, 0x7F, 0x10],
    '5': [0x27, 0x45, 0x45, 0x45, 0x39],
    '6': [0x3C, 0x4A, 0x49, 0x49, 0x30],
    '7': [0x01, 0x71, 0x09, 0x05, 0x03],
    '8': [0x36, 0x49, 0x49, 0x49, 0x36],
    '9': [0x06, 0x49, 0x49, 0x29, 0x1E],
    ':': [0x00, 0x36, 0x36, 0x00, 0x00],
    ' ': [0x00, 0x00, 0x00, 0x00, 0x00]
}

# ==========================================
# HARDWARE AND FIXED SCALING OPERATIONS
# ==========================================

def write_oled_commands(bridge, cmd_list):
    payload = bytes([I2C_ADDRESS, STOP_BIT, len(cmd_list) + 1, CTRL_COMMAND_MULTI] + cmd_list)
    return bridge.command(CMD_I2C_WRITE, payload=payload)

def send_data_chunks(bridge, data_bytes, chunk_size=16):
    for i in range(0, len(data_bytes), chunk_size):
        chunk = data_bytes[i:i + chunk_size]
        payload = bytes([I2C_ADDRESS, STOP_BIT, len(chunk) + 1, CTRL_DATA_STREAM] + chunk)
        bridge.command(CMD_I2C_WRITE, payload=payload)

def expand_2bits_to_byte(val_2bits):
    """
Expands 2 bits into a full, continuous 8-bit byte.
    0b00 -> 0x00 (00000000)
    0b01 -> 0x0F (00001111)
    0b10 -> 0xF0 (11110000)
    0b11 -> 0xFF (11111111)
    """
    res = 0x00
    if val_2bits & 0x01:
        res |= 0x0F
    if val_2bits & 0x02:
        res |= 0xF0
    return res

def draw_giant_clock_string(bridge, start_page, col_offset, time_str):
    p0_bytes, p1_bytes, p2_bytes, p3_bytes = [], [], [], []

    for char in time_str:
        pattern = FONT_DIGITS.get(char, FONT_DIGITS[' '])
        
        for col_byte in pattern:
            # Split the 8-bit column into 4x2 bits and expand each into a full 8-bit byte
            b0 = expand_2bits_to_byte((col_byte >> 0) & 0x03)
            b1 = expand_2bits_to_byte((col_byte >> 2) & 0x03)
            b2 = expand_2bits_to_byte((col_byte >> 4) & 0x03)
            b3 = expand_2bits_to_byte((col_byte >> 6) & 0x03)

            # Double/quadruple width (4 columns wide)
            p0_bytes.extend([b0] * 4)
            p1_bytes.extend([b1] * 4)
            p2_bytes.extend([b2] * 4)
            p3_bytes.extend([b3] * 4)

        # Character spacing (4 empty columns)
        p0_bytes.extend([0x00] * 4)
        p1_bytes.extend([0x00] * 4)
        p2_bytes.extend([0x00] * 4)
        p3_bytes.extend([0x00] * 4)

    pages_data = [p0_bytes, p1_bytes, p2_bytes, p3_bytes]
    actual_col = col_offset + 2  # SH1106 2-pixel offset

    for i, page_bytes in enumerate(pages_data):
        target_page = start_page + i
        write_oled_commands(bridge, [
            0xB0 + target_page,
            actual_col & 0x0F,
            0x10 | ((actual_col >> 4) & 0x0F)
        ])
        send_data_chunks(bridge, page_bytes)

def clear_screen(bridge):
    for page in range(8):
        write_oled_commands(bridge, [0xB0 + page, 0x02, 0x10])
        send_data_chunks(bridge, [0x00] * 132)

def init_sh1106(bridge):
    init_sequence = [
        0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40,
        0x8D, 0x14, 0xA1, 0xC8, 0xDA, 0x12, 0x81, 0xFF,
        0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
    ]
    write_oled_commands(bridge, init_sequence)

# ==========================================
# MAIN PROGRAM
# ==========================================
if __name__ == "__main__":
    with Bridge("/dev/ttyACM0") as bridge:
        init_sh1106(bridge)
        clear_screen(bridge)

        colon_state = True
        try:
            while True:
                now = datetime.now()
                sep = ":" if colon_state else " "
                time_str = now.strftime(f"%H{sep}%M")

                draw_giant_clock_string(bridge, start_page=2, col_offset=2, time_str=time_str)

                colon_state = not colon_state
                time.sleep(0.5)

        except KeyboardInterrupt:
            pass
            
