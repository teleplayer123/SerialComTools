import datetime
import logging
import serial
import sys
import threading
import time


TODAY = datetime.datetime.now().strftime("%m-%d-%Y")
MAX_BUFFER_SIZE = 4096

logging.basicConfig(
    filename=f"serial_com_{TODAY}_{int(time.time())}.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)


class SerialPort:
    def __init__(self, device, baud, timeout=0, rtscts=False, dsrdtr=False):
        self.device = device
        self.port = serial.Serial(
            device,
            baudrate=baud,
            timeout=timeout,
            rtscts=rtscts,
            dsrdtr=dsrdtr,
        )

    def write(self, data: bytes):
        self.port.write(data)

    def write_line(self, line: str, cr=True, lf=True):
        suffix = ""
        if cr:
            suffix += "\r"
        if lf:
            suffix += "\n"
        self.write((line + suffix).encode())

    def read_available(self):
        """Read all currently available bytes."""
        if self.port.in_waiting:
            return self.port.read(self.port.in_waiting)
        return b""

    def close(self):
        if self.port.is_open:
            self.port.close()


class SerialReader(threading.Thread):
    def __init__(self, ser: SerialPort, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.ser = ser
        self.stop_event = stop_event

    def run(self):
        logger.info("Serial reader thread started")
        while not self.stop_event.is_set():
            try:
                data = self.ser.read_available()
                if data:
                    sys.stdout.write(data.decode(errors="replace"))
                    sys.stdout.flush()
                else:
                    time.sleep(0.01)
            except serial.SerialException as e:
                logger.error(f"Serial error: {e}")
                break
        logger.info("Serial reader thread exiting")


def main():
    USAGE = """
    Usage:
        serial_com.py <serial_name> [baudrate] [rtscts] [endline]

    Args:
        serial_name : tty device (e.g. ttyUSB0, COM3)
        baudrate    : default 115200
        rtscts      : 0 or 1
        endline     : cr | lf | crlf | no_crlf
    """

    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    tty = sys.argv[1]
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    rtscts = bool(int(sys.argv[3])) if len(sys.argv) > 3 else False
    nl = sys.argv[4] if len(sys.argv) > 4 else "crlf"

    cr = lf = True
    if nl == "cr":
        lf = False
    elif nl == "lf":
        cr = False
    elif nl == "no_crlf":
        cr = lf = False
    elif nl != "crlf":
        print("Invalid endline option")
        sys.exit(1)

    if sys.platform in ("linux", "darwin"):
        tty = f"/dev/{tty}"

    ser = SerialPort(tty, baudrate, rtscts=rtscts)
    stop_event = threading.Event()

    reader = SerialReader(ser, stop_event)
    reader.start()

    print(f"Connected to {tty} @ {baudrate}")
    print("Type commands, Ctrl+C to exit\n")

    try:
        while True:
            line = input()
            ser.write_line(line, cr=cr, lf=lf)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        reader.join(timeout=1)
        ser.close()
        print("\nSerial port closed.")


if __name__ == "__main__":
    main()
