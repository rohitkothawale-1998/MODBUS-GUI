"""
xbee.py

By Paul Malmsten, 2010
Inspired by code written by Amit Synderman and Marco Sangalli
pmalmsten@gmail.com

XBee superclass module

This class defines data and methods common to all XBee modules.
This class should be subclassed in order to provide
series-specific functionality.
"""
import struct, threading, time
from frame import APIFrame
#from ieee import XBee
from python2to3 import byteToInt, intToByte


class ThreadQuitException(Exception):
    pass

class CommandFrameException(KeyError):
	pass

api_responses = {b"\x05":
                        {'name':'SDP',
                         'structure':
                            [{'name':'SDP_version', 'len':1},
                             {'name':'Port1',        'len':1},
                             {'name':'Port2',        'len':1},
                             {'name':'Port3',        'len':1},
                             {'name':'rssi',        'len':1},
                             {'name':'int_temp',     'len':2},
                             {'name':'int_humid',    'len':2},
                             {'name':'battery',    'len':2},
                             {'name':'Port1_Reading',  'len':2},
                             {'name':'Port2_Reading',  'len':2},
                             {'name':'Port3_Reading',  'len':2},
                             {'name':'deviceType',    'len':1},
                             {'name':'Channel_ID',  'len':1},
                             {'name':'HW_version',    'len':2},
                             {'name':'FW_version',    'len':3},
                             {'name':'Mfg_date',    'len':8},
                             {'name':'Serial',    'len':12},
                             {'name':'SKU',    'len':8},
                             {'name':'UTC_Time',    'len':4},
                             {'name':'downLoadedVersion', 'len':4},
                             {'name':'tranID',    'len':1},
                             {'name':'flags',     'len':1}]},
                b"\x06":
                        {'name':'NDP',
                         'structure':
                            [{'name':'ieee_address', 'len':8},
                             {'name':'sA',        'len':2},
                             {'name':'parent_ieee_address',        'len':8},
                             {'name':'parent_sA',        'len':2},
                             {'name':'rxLQI',        'len':1},
                             {'name':'deviceUpTime',     'len':4},
                             {'name':'txCounter',    'len':1},
                             {'name':'workingMemory',    'len':2},
                             {'name':'packetLoss',  'len':2},
                             {'name':'txFailure',  'len':2},
                             {'name':'bl_version',  'len':4},
                             {'name':'hopCount',    'len':1},
                             {'name':'neighbors',   'len':35}]},
                b"\x03":
                        {'name':'STATUS',
                         'structure':
                            [{'name':'Reboot_Reason', 'len':1},
                             {'name':'Serial',    'len':12}]},
                b"\x13":
                        {'name':'PANID',
                         'structure':
                            [{'name':'Rotary_Switch', 'len':1},
                             {'name':'PANID',    'len':2},
                             {'name':'Security_key',    'len':16}]},
                b"\x0b":
                        {'name':'Query_Next_Package_REQ',
                         'structure':
                            [{'name':'CONTROL', 'len':1},
                             {'name':'MANID',    'len':2},
                             {'name':'PKGTYPE',    'len':2},
                             {'name':'FILEVER',    'len':4}]},
                b"\x0c":
                        {'name':'Package_Block_REQ',
                         'structure':
                            [{'name':'CONTROL', 'len':1},
                             {'name':'MANID',    'len':2},
                             {'name':'PKGTYPE',    'len':2},
                             {'name':'FILEVER',    'len':4},
                             {'name':'OFFSET',    'len':4},
			     {'name':'MAX_BLOCK_SIZE', 'len':1}]},
                b"\x0d":
                        {'name':'Package_End_REQ',
                         'structure':
                            [{'name':'CONTROL', 'len':1},
                             {'name':'MANID',    'len':2},
                             {'name':'PKGTYPE',    'len':2},
                             {'name':'FILEVER',    'len':4}]},
                b"\x09":
                        {'name':'SJOIN_REQ',
                         'structure':
                            [{'name':'XAddr', 'len':8}]},
                b"\xD1":
                        {'name':'DBG_INFO',
                         'structure':
                            [{'name':'ERROR_CODE', 'len':8}]},
                b"\xdd":
                        {'name':'DBG_INFO_2',
                         'structure':
                            [{'name':'ERROR_MSG', 'len':26}]},
                b"\x80":
                        {'name':'ACK',
                         'structure':
                            [{'name':'TRANSID', 'len':1},
                             {'name':'RESULT', 'len':1}]},
                b"\x21":
                        {'name':'REMOTE_CMD',
                         'structure':
                            [{'name':'LENGTH', 'len':1},
                             {'name':'CMD', 'len':60}]},
                b"\x0f":
                        {'name':'TIME_REQ',
                         'structure':
                            [{'name':'CMD',  'len':0}]}
                }

class XBeeBase(threading.Thread):
    """
    Abstract base class providing command generation and response
    parsing methods for XBee modules.

    Constructor arguments:
        ser:    The file-like serial port to use.


        shorthand: boolean flag which determines whether shorthand command
                   calls (i.e. xbee.at(...) instead of xbee.send("at",...)
                   are allowed.

        callback: function which should be called with frame data
                  whenever a frame arrives from the serial port.
                  When this is not None, a background thread to monitor
                  the port and call the given function is automatically
                  started.

        escaped: boolean flag which determines whether the library should
                 operate in escaped mode. In this mode, certain data bytes
                 in the output and input streams will be escaped and unescaped
                 in accordance with the XBee API. This setting must match
                 the appropriate api_mode setting of an XBee device; see your
                 XBee device's documentation for more information.
    """

    def __init__(self, ser, shorthand=True, callback=None, escaped=False):
        super(XBeeBase, self).__init__()
        self.serial = ser
        self.shorthand = shorthand
        self._callback = None
        self._thread_continue = False
        self._escaped = escaped

        if callback:
            self._callback = callback
            self._thread_continue = True
            self._thread_quit = threading.Event()
            self.start()

    def halt(self):
        """
        halt: None -> None

        If this instance has a separate thread running, it will be
        halted. This method will wait until the thread has cleaned
        up before returning.
        """
        if self._callback:
            self._thread_continue = False
            self._thread_quit.wait()

    def run(self):
        """
        run: None -> None

        This method overrides threading.Thread.run() and is automatically
        called when an instance is created with threading enabled.
        """
        while True:
            try:
                self._callback(self.wait_read_frame())
            except ThreadQuitException:
                break
        self._thread_quit.set()

    def _wait_for_frame(self):
        """
        _wait_for_frame: None -> binary data

        _wait_for_frame will read from the serial port until a valid
        API frame arrives. It will then return the binary data
        contained within the frame.

        If this method is called as a separate thread
        and self.thread_continue is set to False, the thread will
        exit by raising a ThreadQuitException.
        """
        print("gets here _wait_for_frame()!")
        frame = APIFrame(escaped=self._escaped)

        while True:
                if self._callback and not self._thread_continue:
                    raise ThreadQuitException

                if self.serial.inWaiting() == 0:
                    time.sleep(.01)
                    continue

                byte = self.serial.read()

                if byte != APIFrame.START_BYTE:
                #if bytearray(byte)[0] != APIFrame.START_BYTE:
                    print("first byte is: ", byte, APIFrame.START_BYTE)
                    continue

                # Save all following bytes

                frame.fill(byte)
                while(frame.remaining_bytes() > 0):
                    frame.fill(self.serial.read())

                print("We fillin Frame done! ")

                try:
                    # Try to parse and return result
                    frame.parse()
                    return frame
                except ValueError:
                    # Bad frame, so restart
                    print("value error, we re-start frame")
                    frame = APIFrame(escaped=self._escaped)


    def _split_response(self, data):
        """
        _split_response: binary data -> {'id':str,
                                         'param':binary data,
                                         ...}

        _split_response takes a data packet received from an XBee device
        and converts it into a dictionary. This dictionary provides
        names for each segment of binary data as specified in the
        api_responses spec.
        """
        # Fetch the first byte, identify the packet
        # If the spec doesn't exist, raise exception
        print("gets to _split_response()")
        print("here's the data string", data)
        length = data[1]
        packet_id = data[12]
        xA = data[2:10]
        #sA  = data[10:12] # for new SDP, the sA is deprecated.
        transID = data[10]
        controlBit  = data[11]
        data = data[12:] #from 12 to the end of the array
        try:
            packet = api_responses[packet_id]
            print("get an ", packet['name'])
        except AttributeError:
            raise NotImplementedError("API response specifications could not be found; use a derived class which defines 'api_responses'.")
        except KeyError:
            # Check to see if this ID can be found among transmittible packets
            for cmd_name, cmd in list(self.api_commands.items()):
                if cmd[0]['default'] == data[0:1]:
                    raise CommandFrameException("Incoming frame with id %s looks like a command frame of type '%s' (these should not be received). Are you sure your devices are in API mode?"
                        % (data[0], cmd_name))

            raise KeyError(
                "Unrecognized response packet with id byte {0}".format(data[0]))

        # Current byte index in the data stream
        index = 1

        # Result info
        info = {'id':packet['name']}
        packet_spec = packet['structure']
        info['transID'] = transID;
        info['controlBit'] = controlBit;
        info['xA'] = xA;

        # Parse the packet in the order specified
        for field in packet_spec:
            if field['len'] == 'null_terminated':
                field_data = b''

                while data[index:index+1] != b'\x00':
                    field_data += data[index:index+1]
                    index += 1

                index += 1
                info[field['name']] = field_data
            elif field['len'] is not None:
                # Store the number of bytes specified

                # Are we trying to read beyond the last data element?
                # print("field['len'] is:"), field['len']
                # print("len(data) is:"), len(data)
                if index + int(field['len']) > len(data):
                    raise ValueError(
                        "Response packet was shorter than expected")

                field_data = data[index:index + field['len']]
                info[field['name']] = field_data

                index += field['len']
            # If the data field has no length specified, store any
            #  leftover bytes and quit
            else:
                field_data = data[index:]

                # Were there any remaining bytes?
                if field_data:
                    # If so, store them
                    info[field['name']] = field_data
                    index += len(field_data)
                break

        # If there are more bytes than expected, raise an exception
        if (index < len(data) and packet_id != 0xD1):
        #print("packet_id is:"), str(packet_id)
            #raise ValueError(
            #    "Response packet was longer than expected; expected: %d, got: %d bytes" % (index,
            #                                                                               len(data)))
            index = len(data)

        return info

    def wait_read_frame(self):
        """
        wait_read_frame: None -> frame info dictionary

        wait_read_frame calls XBee._wait_for_frame() and waits until a
        valid frame appears on the serial port. Once it receives a frame,
        wait_read_frame attempts to parse the data contained within it
        and returns the resulting dictionary
        """

        print("gets here wait_read_frame()!")
        frame = self._wait_for_frame()
        #print("frame.data ===>"), frame.data
        return self._split_response(frame.data)

    def __getattr__(self, name):
        """
        If a method by the name of a valid api command is called,
        the arguments will be automatically sent to an appropriate
        send() call
        """

        # If api_commands is not defined, raise NotImplementedError\
        #  If its not defined, _getattr__ will be called with its name
        if name == 'api_commands':
            raise NotImplementedError("API command specifications could not be found; use a derived class which defines 'api_commands'.")

        # Is shorthand enabled, and is the called name a command?
        if self.shorthand and name in self.api_commands:
            # If so, simply return a function which passes its arguments
            # to an appropriate send() call
            return lambda **kwargs: self.send(name, **kwargs)
        else:
            raise AttributeError("XBee has no attribute '%s'" % name)


class XBee(XBeeBase):
    """
    Provides an implementation of the XBee API for IEEE 802.15.4 modules
    with recent firmware.

    Commands may be sent to a device by instansiating this class with
    a serial port object (see PySerial) and then calling the send
    method with the proper information specified by the API. Data may
    be read from a device syncronously by calling wait_read_frame. For
    asynchronous reads, see the definition of XBeeBase.
    """
    # Packets which can be received from an XBee

    # Format:
    #        {id byte received from XBee:
    #           {name: name of response
    #            structure:
    #                [ {'name': name of field, 'len':length of field}
    #                  ...
    #                  ]
    #            parse_as_io_samples:name of field to parse as io
    #           }
    #           ...
    #        }
    #
    api_responses = {b"\x05":
                        {'name':'SDP',
                         'structure':
                            [{'name':'source_addr', 'len':2},
                             {'name':'rssi',        'len':1},
                             {'name':'options',     'len':1},
                             {'name':'rf_data',     'len':None}]}
                     }

    def __init__(self, *args, **kwargs):
        # Call the super class constructor to save the serial port
        super(XBee, self).__init__(*args, **kwargs)


