import time
from usb_peripheral_bridge import Bridge
from usb_peripheral_bridge.protocol import *

# ==========================================
# CONSTANTS / PARAMETERS
# ==========================================
I2C_ADDRESS = 0x57       # 24C32 EEPROM I2C address
EEPROM_ADDR = 0x0000     # Starting memory address to read/write
READ_LENGTH = 24         # Number of bytes to read
STOP_BIT    = 0x01       # 1: STOP signal required

# Data bytes to be written to the EEPROM
DATA_BYTES  = [0xAA, 0xBB, 0xCC, 0xDD]


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def read_eeprom(bridge, start_addr: int, length: int):
    """Reads a block of bytes from the EEPROM starting at start_addr."""
    addr_hi = (start_addr >> 8) & 0xFF
    addr_lo = start_addr & 0xFF

    # CMD_I2C_WRITE_READ payload:
    # [0]: I2C Address
    # [1]: TX Length (2 bytes: High and Low memory address)
    # [2]: RX Length (number of bytes to read)
    # [3]: Stop flag
    # [4]: Address HI
    # [5]: Address LO
    payload = bytes([I2C_ADDRESS, 0x02, length, STOP_BIT, addr_hi, addr_lo])

    raw_response = bridge.command(CMD_I2C_WRITE_READ, payload=payload)

    status_code = raw_response[0] if len(raw_response) > 0 else None
    eeprom_data = raw_response[1:] if status_code == 0x00 else b""

    return status_code, eeprom_data


def write_eeprom(bridge, start_addr: int, data: list):
    """Writes a sequence of bytes to the EEPROM starting at start_addr."""
    addr_hi = (start_addr >> 8) & 0xFF
    addr_lo = start_addr & 0xFF

    bytes_to_write = len(data) + 2  # 2 address bytes (HI, LO) + data length

    header = [
        I2C_ADDRESS,
        STOP_BIT,
        bytes_to_write,
        addr_hi,
        addr_lo
    ]

    payload = bytes(header + data)

    raw_response = bridge.command(CMD_I2C_WRITE, payload=payload)
    status_code = raw_response[0] if len(raw_response) > 0 else None

    # Allow time for EEPROM internal write cycle (tWR max 5ms)
    time.sleep(0.01)

    return status_code


def display_hex_dump(eeprom_data, base_addr: int = 0x0000):
    """Prints a nicely formatted Hex and ASCII dump of the provided bytes."""
    print("-" * 65)
    print(" Address   Hexadecimal Content (16 bytes / line)        ASCII")
    print("-" * 65)

    bytes_per_line = 16
    for offset in range(0, len(eeprom_data), bytes_per_line):
        chunk = eeprom_data[offset:offset + bytes_per_line]

        # 1. Hex view
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        hex_str_padded = f"{hex_str:<47}"

        # 2. ASCII view (replace non-printable characters with '.')
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)

        current_addr = base_addr + offset
        print(f" 0x{current_addr:04X} | {hex_str_padded} | {ascii_str}")

    print("-" * 65)


# ==========================================
# MAIN PROGRAM
# ==========================================
def main():
    with Bridge("/dev/ttyACM0") as bridge:
        print("=" * 65)
        print("                 24C32 EEPROM READ / WRITE                  ")
        print("=" * 65)

        # --------------------------------------------------
        # STEP 1: INITIAL READ
        # --------------------------------------------------
        print("\n[STEP 1] Reading current EEPROM content...")
        status, data = read_eeprom(bridge, EEPROM_ADDR, READ_LENGTH)

        if status != 0x00:
            print(f" Error reading EEPROM! Status Code: 0x{status:02X}" if status else " No response!")
            return

        print(f" Read Status : 0x{status:02X} (OK)")
        print(f" Bytes Read  : {len(data)} bytes starting from address 0x{EEPROM_ADDR:04X}")
        display_hex_dump(data, EEPROM_ADDR)

        # --------------------------------------------------
        # STEP 2: PROMPT FOR WRITE
        # --------------------------------------------------
        written_hex = ' '.join(f'0x{b:02X}' for b in DATA_BYTES)
        print(f"\nPrepared Data to Write: [ {written_hex} ] ({len(DATA_BYTES)} bytes) to 0x{EEPROM_ADDR:04X}")

        answer = input("Do you want to write this data to the EEPROM? (y/n): ").strip().lower()

        # --------------------------------------------------
        # STEP 3: WRITE & RE-READ IF CONFIRMED
        # --------------------------------------------------
        if answer == 'y':
            print("\n[STEP 3] Writing data to EEPROM...")
            write_status = write_eeprom(bridge, EEPROM_ADDR, DATA_BYTES)

            if write_status == 0x00:
                print(f" Write Status : 0x{write_status:02X} (OK)")

                print("\nRe-reading EEPROM to verify written content...")
                _, new_data = read_eeprom(bridge, EEPROM_ADDR, READ_LENGTH)
                display_hex_dump(new_data, EEPROM_ADDR)
            else:
                print(f" Write failed! Status Code: 0x{write_status:02X}" if write_status else " Write failed! No response.")
        else:
            print("\nWrite operation skipped.")

        print("=" * 65)


if __name__ == "__main__":
    main()