import serial
import struct
import time


from .protocol import *
from .crc16 import calculate



class Bridge:


    def __init__(
        self,
        port,
        baudrate=115200,
        timeout=1
    ):

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.serial = None

        self.sequence = 0



    def open(self):

        self.serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.timeout
        )


        # Time it takes the Arduino to startup
        # >1.6 seconds
        time.sleep(1.8)
        
        # Emptying because of Arduino bootloader
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()



    def close(self):

        if self.serial:
            self.serial.close()



    def __enter__(self):

        self.open()
        return self



    def __exit__(
        self,
        exc_type,
        exc,
        tb
    ):

        self.close()



    def _next_sequence(self):

        self.sequence += 1

        if self.sequence > 65535:
            self.sequence = 0

        return self.sequence



    def _build_packet(
        self,
        cmd,
        payload=b''
    ):


        seq = self._next_sequence()


        header = struct.pack(
            "<BBBHH",
            PROTOCOL_VERSION,
            cmd,
            0,
            seq,
            len(payload)
        )


        crc = calculate(
            header + payload
        )


        packet = (
            SOF
            +
            header
            +
            payload
            +
            struct.pack(
                "<H",
                crc
            )
        )


        return packet, seq



    def _receive_packet(self):


        # looking for SOF
        while True:

            b = self.serial.read(1)


            if not b:
                raise TimeoutError()

            if b == b'\x55':

                b2 = self.serial.read(1)

                if b2 == b'\xaa':
                    break



        header = self.serial.read(7)


        if len(header)!=7:
            raise IOError(
                "short header"
            )


        (
            version,
            cmd,
            flags,
            seq,
            length
        ) = struct.unpack(
            "<BBBHH",
            header
        )



        payload = b''


        if length:

            payload = self.serial.read(
                length
            )


        crc_bytes = self.serial.read(2)


        crc_recv = struct.unpack(
            "<H",
            crc_bytes
        )[0]


        crc_calc = calculate(
            header + payload
        )


        if crc_recv != crc_calc:
            raise IOError(                "CRC error")
         


        return {
            "cmd":cmd,
            "flags":flags,
            "seq":seq,
            "payload":payload
        }



    def command(
        self,
        cmd,
        payload=b''
    ):


        packet, seq = self._build_packet(
            cmd,
            payload
        )


        self.serial.write(packet)
        
        response = self._receive_packet()


        if response["seq"] != seq:
            raise IOError(
                "sequence mismatch"
            )


        return response["payload"]




# Segédfunkciók: I2C    
    
    def scan(self):
        payload = self.command(        CMD_SCAN    )
        return [
         addr
         for addr in payload    ]



# Segédfunkciók: Serial   
    
    def serial_config(
        self,
        baudrate: int,
    ):
        payload = baudrate.to_bytes(4, "little")
    
        return self.command(
            CMD_SERIAL_CONFIG,
            payload,
        )
    def serial_write(
        self,
        data: bytes,
    ):
        return self.command(
            CMD_SERIAL_WRITE,
            data,
        )
    def serial_read(
        self,
        length: int,
    ):
        result = self.command(
            CMD_SERIAL_READ,
            bytes([length]),
        )
    
        return result
        
    def serial_transfer(
        self,
        data: bytes,
        read_length: int,
    ):
        payload = bytes([
            read_length,
        ]) + data
    
        return self.command(
            CMD_SERIAL_TRANSFER,
            payload,
        )         
            
    
    
