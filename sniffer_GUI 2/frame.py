"""
frame.py

By Paul Malmsten, 2010
pmalmsten@gmail.com

Represents an API frame for communicating with an XBee
"""
import struct
from python2to3 import byteToInt, intToByte

class APIFrame:
    """
    Represents a frame of data to be sent to or which was received 
    from an XBee device
    """
    
    START_BYTE = b'\xFE'
    """
    ESCAPE_BYTE = b'\x7D'
    XON_BYTE = b'\x11'
    XOFF_BYTE = b'\x13'
    """
    #ESCAPE_BYTES = (START_BYTE)
    ESCAPE_BYTES = ()
    
    def __init__(self, data=b'', escaped=False):
        self.data = data
        self.raw_data = b''
        self.escaped = escaped
        self._unescape_next_byte = False
        
    def checksum(self):
        """
        checksum: None -> single checksum byte
        
        checksum adds all bytes of the binary, unescaped data in the 
        frame, saves the last byte of the result, and subtracts it from 
        0xFF. The final result is the checksum
        """
        total = 0
        
        # Add together all bytes
        for byte in self.data:
            total += byteToInt(byte)
            
        # Only keep the last byte
        total = total & 0xFF
        
        return intToByte(0xFF - total)

    def verify(self, chksum):
        """
        verify: 1 byte -> boolean
        
        verify checksums the frame, adds the expected checksum, and 
        determines whether the result is correct. The result should 
        be 0xFF.
        """
        total = 0
        
        # Add together all bytes
        for byte in self.data:
            total += byteToInt(byte)
        # Add checksum too
        #total += byteToInt(chksum)
        
        # Only keep low bits
        # print("total = "), total&0xFF
        total &= 0xFF
        
        # Check result
        if (total == byteToInt(chksum)):
            print("Good check Sum!")
        return total == byteToInt(chksum) 

    def len_bytes(self):
        """
        len_data: None -> 8-bit integer length, one byte
        
        """
        count = len(self.data)
        return struct.pack("> h", count)
        
    @staticmethod
    def escape(data):
        """
        escape: byte string -> byte string

        When a 'special' byte is encountered in the given data string,
        it is preceded by an escape byte and XORed with 0x20.
        """

        escaped_data = b""
        for byte in data:
            if intToByte(byteToInt(byte)) in APIFrame.ESCAPE_BYTES:
                escaped_data += APIFrame.ESCAPE_BYTE
                escaped_data += intToByte(0x20 ^ byteToInt(byte))
            else:
                escaped_data += intToByte(byteToInt(byte))
                    
        return escaped_data

    def fill(self, byte):
        """
        fill: byte -> None

        Adds the given raw byte to this APIFrame. If this APIFrame is marked
        as escaped and this byte is an escape byte, the next byte in a call
        to fill() will be unescaped.
        """
        #print("gets APIFrame.fill()")
        if self._unescape_next_byte:
            byte = intToByte(byteToInt(byte) ^ 0x20)
            self._unescape_next_byte = False
        elif self.escaped and byte == APIFrame.ESCAPE_BYTE:
            print("gets escape charactor", byte.hex())
            self._unescape_next_byte = True
            return

        self.raw_data += intToByte(byteToInt(byte))

    def remaining_bytes(self):
        remaining = 2

        if len(self.raw_data) >= 2:
            # First byte is the length of the data
            raw_len = self.raw_data[1]
            data_len = byteToInt(raw_len) + 10 
            #print("length of the data is:"), data_len 

            remaining += data_len

            # Don't forget the checksum
            remaining += 1
        # print("remaining is: "), remaining - len(self.raw_data)
        return remaining - len(self.raw_data)

        
    def parse(self):
        """
        parse: None -> None
        
        Given a valid API frame, parse extracts the data contained
        inside it and verifies it against its checksum
        """
        if len(self.raw_data) < 2:
            ValueError("parse() may only be called on a frame containing at least 2 bytes of raw data (see fill())")

        # Second byte is the length of the payload, here add in 10 for 2(sA), 8(xA)
        raw_len = self.raw_data[1]
        # print("here's the raw_data: ===")
        # print((self.raw_data).hex())
        
        # Unpack it
        data_len = byteToInt(raw_len)+10
        
        # Read the data
        data = self.raw_data[0: 2+data_len]
        chksum = self.raw_data[-1]
        print("parse done, we get this as data: ======")
        for i in range(0, len(data)):
            print("{",i, ",", data[i].hex(), "}")

        # Checksum check
        print("check checksum ====> ", end=" ")
        self.data = data
        if not self.verify(chksum):
            raise ValueError("Invalid checksum")
