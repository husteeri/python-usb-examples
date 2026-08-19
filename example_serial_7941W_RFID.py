import time
from usb_peripheral_bridge import Bridge
from usb_peripheral_bridge.protocol import *

# --- HELPER FUNCTIONS FOR THE PROTOCOL ---

def calculate_xor_checksum(payload: bytes) -> int:
    """Calculates XOR checksum without the protocol header."""
    checksum = 0
    for byte in payload:
        checksum ^= byte
    return checksum

def build_frame(cmd: int, data: bytes = b"", address: int = 0x00) -> bytes:
    """
    Builds the frame for the 7941W reader:
    [AB BA] [Address] [Command] [Data length] [Data...] [XOR Checksum]
    """
    header = bytes([0xAB, 0xBA])
    payload = bytes([address, cmd, len(data)]) + data
    checksum = calculate_xor_checksum(payload)
    return header + payload + bytes([checksum])

def parse_response(response: bytes):
    """Processes the response."""
    if not response or len(response) < 6:
        return {"success": False, "error": f"Incomplete/empty response (length: {len(response)})"}

    # Checking the header (0xCD 0xDC)
    if response[0] != 0xCD or response[1] != 0xDC:
        return {"success": False, "error": f"Invalid header: {response[:2].hex().upper()}"}

    address = response[2]
    status_code = response[3]
    data_len = response[4]

    expected_total_len = 5 + data_len + 1
    if len(response) < expected_total_len:
        return {"success": False, "error": f"Truncated packet: {len(response)}/{expected_total_len} bytes received"}

    data = response[5:5 + data_len]
    received_checksum = response[5 + data_len]

    # Validating the checksum (Address -> Data)
    payload_to_check = response[2:5 + data_len]
    if calculate_xor_checksum(payload_to_check) != received_checksum:
        return {"success": False, "error": "Checksum error!"}

    # 0x81: Successful operation, 0x80: No card present / Error
    if status_code == 0x81:
        return {
            "success": True,
            "status": "OK",
            "data": data,
            "hex_data": data.hex().upper()
        }
    elif status_code == 0x80:
        return {
            "success": False,
            "status": "NO_CARD",
            "error": "No card present (0x80)"
        }
    else:
        return {
            "success": False,
            "status": "UNKNOWN",
            "error": f"Unknown status code: 0x{status_code:02X}"
        }

# --- RFID OPERATIONS ---

def rfid_transceive(bridge, cmd: int, data: bytes = b"") -> dict:
    """Sends a command frame through the Bridge and reads the response."""
    frame = build_frame(cmd, data)
    bridge.serial_write(frame)
    time.sleep(0.2)  # Delay to allow data to arrive in the serial buffer
    raw_res = bridge.serial_read(32)
    return parse_response(raw_res)

def read_card_id(bridge, read_cmd: int) -> bytes:
    """Continuously polls for a card until it is successfully read."""
    print("\nPlease place the SOURCE card/tag on the reader...")
    while True:
        res = rfid_transceive(bridge, read_cmd)
        if res["success"]:
            print(f"-> Card successfully read! ID (HEX): {res['hex_data']}")
            return res["data"]
        time.sleep(0.5)

def write_card_id(bridge, write_cmd: int, card_id: bytes) -> bool:
    """Attempts to write the specified ID to the target card."""
    res = rfid_transceive(bridge, write_cmd, card_id)
    if res["success"]:
        print("-> WRITE SUCCESSFUL!")
        return True
    else:
        print(f"-> Write error: {res['error']}")
        return False

# --- MAIN PROGRAM ---

def main():
    print("=== RFID Copier Utility (125kHz & 13.56MHz) ===")
    print("1 - 125 kHz (ID Cards - EM4100/T5577)")
    print("2 - 13.56 MHz (IC Cards - Mifare/UID)")

    choice = input("Select frequency mode (1/2): ").strip()

    if choice == '1':
        read_cmd = 0x15
        write_cmd = 0x16
        mode_str = "125 kHz"
    elif choice == '2':
        read_cmd = 0x10
        write_cmd = 0x11
        mode_str = "13.56 MHz"
    else:
        print("Invalid choice. Exiting program.")
        return

    print(f"\nSelected Mode: {mode_str}")

    # Connect through USB Peripheral Bridge
    with Bridge("/dev/ttyACM0") as bridge:
        bridge.serial_config(baudrate=115200)

        # 1. READ CARD
        card_data = read_card_id(bridge, read_cmd)

        has_written_at_least_once = False

        # 2. WRITE LOOP & MULTIPLE COPIES
        while True:
            confirm = input(f"\nAre you sure you want to write this ID ({card_data.hex().upper()}) to a target card? (y/n): ").strip().lower()

            if confirm == 'y':
                print("\nPlease place the WRITABLE card on the reader...")

                # Write attempts
                while True:
                    success = write_card_id(bridge, write_cmd, card_data)
                    if success:
                        has_written_at_least_once = True
                        break

                    retry = input("Would you like to retry writing? (y/n): ").strip().lower()
                    if retry != 'y':
                        break
                    time.sleep(0.5)

            # 3. ASK FOR ADDITIONAL COPIES (ONLY IF AT LEAST ONE SUCCESSFUL WRITE OCCURRED)
            if has_written_at_least_once:
                more_copies = input("\nDo you want to make ADDITIONAL COPIES of this card ID? (y/n): ").strip().lower()
                if more_copies != 'y':
                    print("Duplication process finished.")
                    break
            else:
                print("No write performed. Exiting.")
                break

if __name__ == "__main__":
    main()
