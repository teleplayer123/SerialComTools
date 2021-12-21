#!/usr/bin/python3

import serial
import time

"""
esptool.py --chip auto --port /dev/ttyUSB0 --baud 115200 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 40m --flash_size 4MB 0x0 ~/ESP32-WROOM-32-V2.2.0.0/factory/factory_WROOM-32.bin
"""

class SerialPort:
    def __init__(self, device, baud, timeout=1, rtscts=False):
        self.port = serial.Serial(device, baudrate=baud, timeout=timeout, rtscts=rtscts)

    def write_cmd(self, cmd):
        self.port.write("{}\r\n".format(cmd).encode())
        time.sleep(1)
        self.port.flush()
        time.sleep(1)

    def write_no_crlf(self, cmd):
        self.port.write(str(cmd).encode())
        time.sleep(1)
        self.port.flush()
        time.sleep(1)

    def read_response(self, size=None):
        res = None
        if not self.port.is_open:
            self.port.open()
        if size is None:
            msg = self.port.readlines()
            res = [str(m.decode()) for m in msg]
            res = [m.strip("\r\n") for m in res if m.find("\r\n")]
        elif type(size) == int:
            msg = self.port.read(size)
            res = msg.decode()
        else:
            raise ValueError("size must be an integer or None")
        return res

port = SerialPort("/dev/ttyUSB0", baud=9600, rtscts=True)
port.write_cmd("AT")
print(port.read_response())
port.write_cmd("AT+HELP")
print(port.read_response())
port.write_cmd("AT+DBGSTACKDUMP")
print(port.read_response())