#!/usr/bin/python3 

import logging
import serial
import sys
from time import sleep
import threading


logging.basicConfig(filename=f"serial_poll.log", filemode="a", 
            format="%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s",
            level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SerialPort:
    def __init__(self, device, baud, timeout=1, rtscts=False):
        self.port = serial.Serial(device, baudrate=baud, timeout=timeout, rtscts=rtscts)
        self.buffer = []

    def write_cmd(self, cmd):
        self.port.write("{}\r\n".format(cmd).encode())
        sleep(0.5)

    def flush_port(self):
        self.port.flush()

    def write_no_crlf(self, cmd):
        self.port.write(str(cmd).encode())
        sleep(0.5)
        self.port.flush()
        sleep(0.5)

    def close(self):
        if self.port.is_open:
            self.port.close()

    @property
    def data_in_buffer(self):
        return len(self.buffer) > 0

    @property
    def in_waiting(self):
        return self.port.in_waiting > 0

    @property
    def is_open(self):
        return self.port.is_open

    def read_response(self, size=None, decode=True):
        res = None
        if not self.port.is_open:
            self.port.open()
        if size is None:
            msg = self.port.readlines()
            if decode == True:
                res = [str(m.decode()) for m in msg]
                res = [m.strip("\r\n") for m in res if m.find("\r\n")]
            else:
                res = bytearray([b for b in msg])
        elif type(size) == int:
            msg = self.port.read(size)
            if decode == True:
                res = msg.decode()
            else:
                res = msg
        else:
            raise ValueError("size must be an integer or None")
        return res

    def read_bytes(self):
        while True:
            b = self.port.read(self.port.in_waiting or 1)
            if len(b) <= 0:
                break
            else:
                self.buffer.extend(b)
        
    def read_from_buff(self):
        while True:
            if len(self.buffer) <= 0:
                break
            b = self.buffer.pop()
            yield b


class SerialPortException(Exception): pass

class CallbackException(Exception): pass


class SerialReader(threading.Thread):

    def __init__(self, ser, callback=lambda x: print(x), timeout=1):
        """
        @param SerialPort ser: instance to communicate over serial port.
        """
        if not isinstance(ser, SerialPort):
            raise SerialPortException("First parameter must be instance of SerialPort class.")
        super(SerialReader, self).__init__()
        self.ser = ser
        self.callback = callback
        self.timeout = float(timeout)
        self.read_evt = threading.Event()
        self.read_evt.clear()
        self.is_alive = True
        self.daemon = True
        
    def run(self):
        self.read_evt.set()
        self.worker()

    def worker(self):
        if self.read_evt.is_set():
            while self.is_alive:
                if self.ser.in_waiting:
                    self._read_from_port()
                else:
                    continue
        else:
            self.stop()
  
    def _read_from_port(self):
        while True:
            try:
                self.ser.read_bytes()
                self.read_data()
            except serial.SerialException as err:
                continue

    def read_data(self):
        while True:
            s = ""
            if not self.read_evt.is_set():
                break
            if self.ser.data_in_buffer:
                for data in self.ser.read_from_buff():
                    char = chr(data)
                    s += char
                    if char == "\n" or (len(s) > 64 and char == " ") :
                        self.callback("".join([s[i] for i in range(len(s)-1, 0, -1)]))
                        logger.info("".join([s[i] for i in range(len(s)-1, 0, -1)]))
                        s = ""
            else:
                sleep(1.5)
                continue

    def pause(self):
        self.read_evt.clear()
        return self.read_evt.is_set()

    def resume(self):
        self.read_evt.set()
        return self.read_evt.is_set()

    def stop(self):
        self.read_evt.clear()
        self.join()
        self.is_alive = False
        self.daemon = False
        if self.ser.is_open:
            self.ser.close()

dev = "/dev/ttyUSB0"
if len(sys.argv) > 1:
    dev = str(sys.argv[1])


ser = SerialPort(dev, 115200)
r = SerialReader(ser)
r.start()
try:
    while True:
        try:
            sleep(1)
        except KeyboardInterrupt:
            break
except KeyboardInterrupt:
    pass
finally:
    r.stop()