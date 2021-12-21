#!/usr/bin/python3


from collections import deque
import logging
import re
import serial
import sys
from time import sleep
import threading

logging.basicConfig(filename=f"serial_poller.log", filemode="a", 
            format="%(asctime)s - %(module)s - %(funcName)s - %(levelname)s - %(message)s",
            level=logging.DEBUG)
logger = logging.getLogger()



class SerialPort:
    def __init__(self, device, baud, timeout=1, rtscts=False):
        self.port = serial.Serial(device, baudrate=baud, timeout=timeout, rtscts=rtscts)
        self.queue = deque()

    def write_cmd(self, cmd):
        self.port.write("{}\r\n".format(cmd).encode())
        sleep(0.5)

    def flush_port(self):
        self.port.flush()

    def write_cust_crlf(self, cmd, cr=False, lf=True):
        if cr == False:
            if lf == False:
                self.port.write(str(cmd).encode())
            else:
                self.port.write("{}\n".format(cmd).encode())
        else:
            if lf == False:
                self.port.write("{}\r".format(cmd).encode())
            else:
                self.port.write("{}\r\n".format(cmd).encode())
        sleep(0.5)

    @property
    def rtscts_set(self):
        return self.port._rtscts

    @property
    def in_waiting(self):
        return self.port.in_waiting

    @property
    def out_waiting(self):
        return self.port.out_waiting

    def wait_for_cts(self):
        while True:
            if self.port.cts == True:
                break
        return True

    @property
    def get_cts(self):
        return self.port.cts

    @property
    def get_rts(self):
        return self.port.rts

    def set_rts(self, val):
        self.port.rts = val

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

    def read_lines(self, end=None):
        if not self.port.is_open:
            self.port.open()
        while True:
            data = self.port.readline().decode()
            if end is not None:
                if re.match(end, data):
                    break
            elif len(data) < 1:
                break
            else:
                self.queue.append(data)
        
    def read_line(self):
        for line in self.port.readlines():
            yield line.decode()

    def close_port(self):
        if self.port.is_open():
            self.port.close()
            print("Serial port has been closed.")
        else:
            print("Serial port already closed.")


class SerialPortException(Exception):
    pass


class SerialPoll:

    def __init__(self, ser, interact=True, timeout=None, impl_rtscts=False, nl=None):
        if not isinstance(ser, SerialPort):
            raise SerialPortException("First parameter must be instance of SerialPort class.")
        self.ser = ser
        if interact == True:
            self.callback = lambda x: input(x)
        else:
            self.callback = lambda x: print(x)
        self.timeout = float(timeout) if timeout is not None else None
        self.impl_rtscts = impl_rtscts if not self.ser.rtscts_set else False
        self.nl = self.process_nl_opts(nl) if nl is not None else None
        self.proc = threading.Event()
        self.proc.clear()
        self.lock = threading.Lock()
        self.read_has_lock = True

    def process_nl_opts(self, nl):
        if nl.lower() not in {"cr", "lf", "no_crlf"}:
            raise ValueError("If nl is not None, it must be a string with value of either [cr|nl|no_crlf]")
        else:
            cr, lf = False, False
            if nl.lower() == "cr":
                cr = True
            elif nl.lower() == "lf":
                lf = True
            elif nl.lower() == "no_crlf":
                cr = False
                lf = False
        return cr, lf

    def run(self):
        self.proc.set()
        logger.info("""     
                    +============+=============+=============+
                    +       Polling process starting.        +
                    +============+=============+=============+
                    """)
        self.worker()

    def _read(self):
        res = None
        self.lock.acquire()
        self.read_has_lock = True
        logger.info("Read has acquired lock.")
        if self.impl_rtscts == True:
            if self.ser.get_rts == True:
                self.ser.set_rts(False)
            logger.debug("RTS set to false, reading from serial port: {}".format(self.ser.get_rts))
        lines = self.ser.read_response()
        if len(lines) == 1:
            res = self.callback(lines[0])
        elif len(lines) > 1:
            for line in lines:
                if line != lines[-1]:
                    print(line)
                    sys.stdout.flush()
                    logger.info("Response: {}".format(line))
                else:
                    res = self.callback(line)
                    logger.info("Callback Response: {}".format(res))
                    break
        else:
            info_dict = self._info_dict()
            logger.error("Serial Error: {}".format(info_dict))
        self.lock.release()
        self.read_has_lock = False
        logger.info("Read has released lock.")
        return res

    def _info_dict(self):
        return {
                "in_waiting": self.ser.in_waiting,
                "out_waiting": self.ser.out_waiting,
                "is_open": self.ser.port.is_open,
                "rts": self.ser.get_rts,
                "rts_state": self.ser.port._rts_state,
                "cts": self.ser.get_cts,
                "rtscts": self.ser.rtscts_set,
                "dtr": self.ser.port.dtr,
                "dtr_state": self.ser.port._dtr_state,
                "dsr": self.ser.port.dsr
            } 
        
    def _write(self, cmd=None):
        self.lock.acquire()
        self.read_has_lock = False
        logger.info("Write has acquired lock.")
        if self.impl_rtscts == True:
            self.ser.set_rts(True)
            logger.debug("RTS set to True, ready to write data: {}".format(self.ser.get_rts))
        if cmd is None:
            cmd = input("> ")
        if str(cmd).lower() == "q":
            self.lock.release()
            logger.info("Write has released lock.")
            self.stop()
        else:
            if self.impl_rtscts == True:
                if self.ser.get_rts != True:
                    self.ser.set_rts(True)
                logger.debug("Waiting for CTS to write data: {}".format(self.ser.get_cts))
                is_ready = self.ser.wait_for_cts()
                if is_ready:
                    logger.debug("CTS set true, ready to receive data: {}".format(self.ser.get_cts))
                    logger.info("Writing command to serial port: {}".format(cmd))
                    if self.nl is not None:
                        self.ser.write_cust_crlf(cmd, cr=self.nl[0], lf=self.nl[1])
                    else:
                        self.ser.write_cmd(cmd)
                self.ser.set_rts(False)
                logger.debug("RTS set to False: {}".format(self.ser.get_rts))
            else:
                if self.nl is not None:
                    self.ser.write_cust_crlf(cmd, cr=self.nl[0], lf=self.nl[1])
                else:
                    self.ser.write_cmd(cmd)
            self.lock.release()
            self.read_has_lock = True
            logger.info("Write has released lock")


    def worker(self):
        res = None
        while True:
            if self.proc.is_set():
                if self.read_has_lock == False:
                    logger.debug("Main process is writing to serial port.")
                    if res != None:
                        logger.debug("Before write info: {}".format(self._info_dict()))
                        self._write(cmd=res)
                        logger.debug("After write info: {}".format(self._info_dict()))
                    else:
                        self._write()
                    self.ser.flush_port()
                    logger.debug("Finished writing to serial port, read has lock: {}".format(self.read_has_lock))
                else:
                    logger.debug("Main process is reading from serial port.")
                    logger.debug("Before read info: {}".format(self._info_dict()))
                    res = self._read()
                    logger.debug("After read info: {}".format(self._info_dict()))
                    sys.stdout.flush()
                    logger.debug("Finished reading from serial port, read has lock: {}".format(self.read_has_lock))
            else:
                break
    
    def stop(self):
        logger.info("Stop process has been called, program exiting.")
        self.proc.clear()


#current setup used for buspirate
ser = SerialPort("/dev/ttyUSB0", 115200)
poll = SerialPoll(ser, timeout=0.5, nl="lf")

try:
    poll.run()
except KeyboardInterrupt:
    poll.stop()

