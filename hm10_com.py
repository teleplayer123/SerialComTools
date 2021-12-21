import serial
import time

class SerialPort:
    def __init__(self, device, baud, timeout=1):
        self.port = serial.Serial(device, baudrate=baud, timeout=timeout)

    def write_cmd(self, cmd):
        self.port.write("{}\r\n".format(cmd).encode())
        time.sleep(1)
        self.port.flush()
        time.sleep(2)

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
            res = [str(m.decode()).strip("\r\n") for m in msg]
        elif type(size) == int:
            msg = self.port.read(size)
            res = msg.decode()
        else:
            raise ValueError("size must be an integer or None")
        return res

class HM10:
    def __init__(self, dev_path, baud, timeout=1):
        self.port = SerialPort(dev_path, baud, timeout)
        self.attr_obj = {}
    
    def _get_att(self, at_cmd: str) -> str:
        if at_cmd[-1] != "?":
            at_cmd = at_cmd+"?"
        self.port.write_no_crlf(at_cmd)
        time.sleep(2)
        res = self.port.read_response()
        return str(res).decode()

    def advi_params(self):
        """Advertising interval"""
        return {
            "0": "100 ms",
            "1": "152.5 ms",
            "2": "211.25 ms",
            "3": "318.75 ms",
            "4": "417.5 ms",
            "5": "546.25 ms",
            "6": "760 ms",
            "7": "852.5 ms",
            "8": "1022.5 ms",
            "9": "1285 ms",
            "A": "2000 ms",
            "B": "3000 ms",
            "C": "4000 ms",
            "D": "5000 ms",
            "E": "6000 ms",
            "F": "7000 ms"
        } 

    def adty_params(self):
        """Advertising Type"""
        return {
            "0": "Advertising ScanResponse, Connectable",
            "1": "Only allow last device connection in 1.28s",
            "2": "Only allow Advertising and ScanResponse",
            "3": "Only allow Advertising"
        }
        
    def baud_params(self):
        """BAUD Rate"""
        return {
            "0": "9600",
            "1": "19200",
            "2": "38400",
            "3": "57600",
            "4": "115200",
            "5": "4800",
            "6": "2400",
            "7": "1200",
            "8": "230400"
        }

    def comi_coma_params(self):
        """Minimum/Maximum Link Layer Connection Interval"""
        return {
            "0": "7.5 ms",
            "1": "10 ms",
            "2": "15 ms",
            "3": "20 ms",
            "4": "25 ms",
            "5": "30 ms",
            "6": "35 ms",
            "7": "40 ms",
            "8": "45 ms",
            "9": "4000 ms"  
        }

    def __setitem__(self, cmd, p1):
        """set characteristic: 0x0001-0xFFFE"""
        self.port.write_no_crlf(f"{cmd}{p1}")
        self.attr_obj[cmd] = p1
        time.sleep(1)
    
    def __getitem__(self, cmd):
        """get value of AT query"""
        return self._get_att(cmd)
        

#hm10_mac = 0x64694E8C9F02

s = SerialPort("/dev/ttyACM0", 9600)
s.write_no_crlf("AT")
s.write_no_crlf("AT+COMI?")