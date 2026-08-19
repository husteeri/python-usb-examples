from datetime import datetime
import time
from usb_peripheral_bridge import Bridge
from usb_peripheral_bridge.protocol import *

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def dec_to_bcd(val: int) -> int:
    """Converts a standard decimal number to BCD (Binary Coded Decimal) format."""
    return ((val // 10) << 4) | (val % 10)

def bcd_to_dec(val: int) -> int:
    """Converts BCD format to a standard decimal number."""
    return ((val >> 4) * 10) + (val & 0x0F)

# ==========================================
# CONSTANTS / PARAMETERS
# ==========================================
I2C_ADDRESS = 0x68       # DS3231 RTC I2C address
START_REG   = 0x00       # Starting register address (0x00: Seconds)
STOP_BIT    = 0x01       # 1: STOP signal required

# ==========================================
# DS3231 OPERATIONS
# ==========================================
def read_ds3231_time(bridge) -> datetime:
    """Reads the current time from the DS3231 RTC module."""
    # CMD_I2C_WRITE_READ payload structure based on protocol spec:
    # [0]: I2C address
    # [1]: TX length (1 byte: register address)
    # [2]: RX length (7 bytes: sec, min, hour, dow, date, month, year)
    # [3]: stop flag
    # [4]: TX data (0x00)
    tx_len = 1
    rx_len = 7
    payload = bytes([I2C_ADDRESS, tx_len, rx_len, STOP_BIT, START_REG])

    raw_response = bridge.command(CMD_I2C_WRITE_READ, payload=payload)

    if not raw_response or len(raw_response) < 1 + rx_len:
        raise RuntimeError("Incomplete or missing response while reading DS3231!")

    status_code = raw_response[0]
    if status_code != 0x00:  # STATUS_OK = 0x00
        raise RuntimeError(f"I2C read error, status code: 0x{status_code:02X}")

    data = raw_response[1:1 + rx_len]

    # Convert BCD data to decimal
    seconds = bcd_to_dec(data[0] & 0x7F)
    minutes = bcd_to_dec(data[1] & 0x7F)
    hours   = bcd_to_dec(data[2] & 0x3F)  # Assumes 24-hour mode
    day     = bcd_to_dec(data[4] & 0x3F)
    month   = bcd_to_dec(data[5] & 0x1F)
    year    = 2000 + bcd_to_dec(data[6])

    return datetime(year, month, day, hours, minutes, seconds)


def write_ds3231_time(bridge, dt: datetime) -> bool:
    """Writes the specified datetime object to the DS3231 RTC."""
    day_of_week = dt.isoweekday()

    data_bytes = [
        dec_to_bcd(dt.second),          # Reg 0x00: Seconds
        dec_to_bcd(dt.minute),          # Reg 0x01: Minutes
        dec_to_bcd(dt.hour),            # Reg 0x02: Hours (24-hour mode)
        dec_to_bcd(day_of_week),         # Reg 0x03: Day of week (1-7)
        dec_to_bcd(dt.day),             # Reg 0x04: Date
        dec_to_bcd(dt.month),           # Reg 0x05: Month
        dec_to_bcd(dt.year % 100)       # Reg 0x06: Year (2 digits)
    ]

    # CMD_I2C_WRITE payload: [Address, Stop_flag, Length, Data...]
    bytes_to_write = len(data_bytes) + 1  # 1 byte start register + 7 bytes data
    header = [I2C_ADDRESS, STOP_BIT, bytes_to_write, START_REG]
    payload = bytes(header + data_bytes)

    raw_response = bridge.command(CMD_I2C_WRITE, payload=payload)

    status_code = raw_response[0] if raw_response and len(raw_response) > 0 else None
    return status_code == 0x00

# ==========================================
# MAIN PROGRAM
# ==========================================
def main():
    with Bridge("/dev/ttyACM0") as bridge:
        print("=" * 60)
        print("                 DS3231 RTC OPERATIONS               ")
        print("=" * 60)

        # STEP 1: Read time from the RTC module
        try:
            rtc_time = read_ds3231_time(bridge)
            print(f" Current time in DS3231 module : {rtc_time.strftime('%Y.%m.%d. %H:%M:%S')}")
        except Exception as e:
            print(f" Error during read operation: {e}")
            return

        print("-" * 60)

        # STEP 2: Ask for confirmation to sync with PC time
        answer = input("Do you want to update the DS3231 with the PC system time? (y/n): ").strip().lower()

        # STEP 3: Write PC system time if confirmed
        if answer == 'y':
            pc_now = datetime.now()
            print(f"\n PC time to write : {pc_now.strftime('%Y.%m.%d. %H:%M:%S')}")

            success = write_ds3231_time(bridge, pc_now)
            if success:
                print(" -> Time synchronized SUCCESSFULLY!")
            else:
                print(" -> ERROR occurred while setting time!")
        else:
            print("\n Time overwrite skipped.")

        print("=" * 60)

if __name__ == "__main__":
    main()
