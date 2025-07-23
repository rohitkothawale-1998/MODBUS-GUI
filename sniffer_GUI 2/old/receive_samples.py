#! /usr/bin/python

"""
receive_samples.py

By Paul Malmsten, 2010
pmalmsten@gmail.com

This example continuously reads the serial port and processes IO data
received from a remote XBee.
"""

import serial
from base import XBeeBase
import wx

PORT = 'COM43'
BAUD_RATE = 38400

# Open serial port
ser = serial.Serial(PORT, BAUD_RATE)

# Create API object
xbee = XBeeBase(ser)

# Continuously read and print(packets)
while True:
    try:
	print("gets here, receive_samples.py!")
        response = xbee.wait_read_frame()
        print(response)
    except KeyboardInterrupt:
        break
        
ser.close()
