#!/usr/bin/python3 

from collections import deque
import logging
from os import close
import serial
import sys
from time import sleep
import threading


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SerialPort:
    def __init__(self, device, baud, timeout=1, rtscts=False):
        self.port = serial.Serial(device, baudrate=baud, timeout=timeout, rtscts=rtscts)
        self.buffer = deque()

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
            b = self.buffer.popleft()
            if len(b) <= 0:
                break
            else:
                yield b


class SerialPortException(Exception): pass

class CallbackException(Exception): pass


class SerialReader(threading.Thread):

    def __init__(self, ser, timeout=1):
        """
        @param SerialPort ser: instance to communicate over serial port.
        """
        if not isinstance(ser, SerialPort):
            raise SerialPortException("First parameter must be instance of SerialPort class.")
        super(SerialReader, self).__init__()
        self.ser = ser
        self.timeout = float(timeout)
        self.read_evt = threading.Event()
        self.read_evt.clear()
        self.is_alive = True
        self.daemon = True
        self.start()
        
    def run(self):
        self.read_evt.set()
        self.worker()

    def worker(self):
        if self.read_evt.is_set():
            while self.is_alive:
                if self.ser.in_waiting:
                    self._read_from_port()
                else:
                    self.read_evt.wait(self.timeout)
        else:
            self.stop()
  
    def _read_from_port(self):
        while True:
            try:
                self.ser.read_bytes()
            except serial.SerialException as err:
                continue

    def stop(self):
        self.read_evt.clear()
        self.is_alive = False
        self.daemon = False
        self.join()
        self.close()

    def close(self):
        self.ser.close()

class SerialCom(threading.Thread):

    def __init__(self, ser, callback=None, interact=False, timeout=1):
        super(SerialCom, self).__init__()
        if not isinstance(ser, SerialPort):
            raise SerialPortException("First parameter must be instance of SerialPort class.")
        self.ser = ser
        if callback is None:
            self.callback = lambda x: print(x)
        elif not hasattr(callback, "__call__"):
            raise CallbackException("callback parameter must be callable.")
        else:
            self.callback = callback
        self.ser_reader = SerialReader(ser, timeout=timeout)
        self.interact = interact
        self.reading_from_buff = threading.Event()
        self.reading_from_buff.clear()
        self._lock = threading.Lock()
        self.is_alive = True
        self.start()

    def run(self):
        while True:
            try:
                if self.ser.data_in_buffer:
                    self.reading_from_buff.set()
                else:
                    self.reading_from_buff.clear()
                self._handle_poll()
            except KeyboardInterrupt:
                self.stop(close=True)
                break

    def _handle_poll(self):
        if self.reading_from_buff.is_set():
            self._read_buff()
        else:
            if self.interact == True:
                self._write()
        return

    def _read_buff(self):
        with self._lock:
            for data in self.ser.read_from_buff():
                self.callback(data)
        return

    def _write(self):
        with self._lock:
            cmd = input("> ")
            self.ser.write_cmd(cmd)
        return

    def stop(self, close=False):
        self.is_alive = False
        self.reading_from_buff.clear()
        if close == True:
            self.close()
    
    def close(self):
        self.join()
        