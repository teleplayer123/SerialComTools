#!/usr/bin/python3

import logging
import os
import re
import serial
import time
from typing import Optional, TypeVar

FILENAME = "BLE_ESP_AT.log"
DIRNAME = os.getcwd()
PATH = os.path.join(DIRNAME, FILENAME)
PTYPE = TypeVar("PTYPE", str, int)
RTYPE = TypeVar("RTYPE", list, str)

logging.basicConfig(filename=PATH, level=logging.DEBUG, filemode="a",
                format="%(asctime)s - %(module)s - %(levelname)s - %(funcName)s - %(message)s")
logger = logging.getLogger(__name__)

class SerialPort:
    def __init__(self, device, baud, timeout=1, rtscts=False):
        self.port = serial.Serial(device, baudrate=baud, timeout=timeout, rtscts=rtscts)

    def write_cmd(self, cmd):
        self.port.write("{}\r\n".format(cmd).encode())
        time.sleep(0.5)
        self.port.flush()
        time.sleep(0.5)

    def write_no_crlf(self, cmd):
        self.port.write(str(cmd).encode())
        time.sleep(0.5)
        self.port.flush()
        time.sleep(0.5)

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

    def close_port(self):
        if self.port.is_open():
            self.port.close()
            logger.info("Serial port has been closed.")
        else:
            logger.info("Serial port already closed.")


class BLE_AT:

    def __init__(self, port, baud=115200, timeout=1, rtscts=False, verbose=False):
        self.ser = SerialPort(port, baud=baud, timeout=timeout, rtscts=rtscts)
        self.verbose = verbose
        self.attributes = {}

    def _disable_wifi_mode(self) -> None:
        self.ser.write_cmd("AT+CWMODE=0")
        resp = self.ser.read_response()
        logger.info("Disabled WIFI mode: {}".format(resp))

    def _verbose(self, msg: str) -> None:
        if self.verbose == True:
            print(msg)
        
    def ble_init(self) -> None:
        raise NotImplementedError("ble_init function must be implemented.")
    
    def ble_deinit(self) -> None:
        self.ser.write_cmd("AT+BLEINIT=0")
        resp = self.ser.read_response()
        self._verbose(resp)
        logger.info("BLE deinitialized: {}".format(resp))

    def get_ble_addr(self) -> str:
        """Get BLE address."""
        self.ser.write_cmd("AT+BLEADDR?")
        resp = self.ser.read_response()
        self._verbose(resp)
        resp = resp[1].strip("+BLEADDR:")
        logger.info("BLE address: {}".format(resp))
        return str(resp)

    def set_param(self, cmd: str, param: PTYPE) -> RTYPE:
        if type(param) == int:
            self.ser.write_cmd("{}={}".format(cmd, param))
        elif type(param) == str:
            self.ser.write_cmd("{}=\"{}\"".format(cmd, param))
        else:
            raise ValueError("Parameter must be an integer or string.")
        resp = self.ser.read_response()
        self.attributes[cmd] = param
        self._verbose(resp)
        logger.info("Parameter has been set: {}={}".format(cmd, resp)) 
        return resp

    def get_resp(self, cmd) -> RTYPE:
        self.ser.write_cmd(cmd)
        resp = self.ser.read_response()
        self._verbose(resp)
        return resp

    def get_help(self) -> RTYPE :
        self.ser.write_cmd("AT+CMD?")
        help_resp = self.ser.read_response()
        self._verbose(help_resp)
        return help_resp


class Peripheral_BLE(BLE_AT):

    def ble_init(self):
        self.ser.write_cmd("AT+BLEINIT=2")
        resp = self.ser.read_response()
        self._verbose(resp)
        logger.info("BLE peripheral device initialized.")

    def set_ble_adv_data(self, dev_name: str, uuid: str, data: str, tx_pwr: int):
        """
        Set BLE advertising data.
        Arguments:
        <dev_name>: device name (ASCII)
        <uuid>: service identifier (HEX)
        <data>: advertising data (HEX)
        <tx_pwr>:
            0: do not include TX power in advertising data
            1: include TX power in advertising data
        """
        self.ser.write_cmd("AT+BLEADVDATAEX=\"{}\",\"{}\",\"{}\",{}".format(dev_name, uuid,
                                                                            data, tx_pwr))
        resp = self.ser.read_response()
        self._verbose(resp)
        adv_dict = {
            "dev_name": dev_name,
            "uuid": uuid,
            "data": data,
            "tx_pwr": tx_pwr
        }
        logger.debug("ADV data set: {}".format(adv_dict))

    def get_ble_adv_data(self) -> dict:
        """Get BLE advertising data."""
        self.ser.write_cmd("AT+BLEADVDATAEX?")
        resp = self.ser.read_response()
        self._verbose(resp)
        resp = resp[1].strip("+BLEADVDATAEX:").split(",")
        adv_dict = {
            "dev_name": resp[0],
            "uuid": resp[1],
            "data": resp[2],
            "tx_pwr": resp[3]
        }
        logger.debug("ADV data query: {}".format(adv_dict))
        return adv_dict

    def set_ble_adv_param(self, int_min: int, int_max: int, adv_type: int, addr_type: int, adv_chnl: int,
                        adv_filter_policy: int=None, peer_addr_type: int=None, peer_addr: str=None) -> None:
        """
        Set parameters for advertising.
        Arguments:
        <adv_init_min>: range 0x0020-0x4000 and <= <adv_int_max>
        <adv_int_max>: range 0x0020-0x4000 and >= <adv_int_min>
        <adv_type>:
            0: ADV_TYPE_IND
            1: ADV_TYPE_DIRECT_IND_HIGH
            2: ADV_TYPE_SCAN_IND
            3: ADV_TYPE_NONCONN_IND
            4: ADV_TYPE_DIRECT_IND_LOW
        <own_addr_type>:
            0: BLE_ADDR_TYPE_PUBLIC
            1: BLE_ADDR_TYPE_RANDOM
        <channel_map>: advertising channel
            1: ADV_CHNL_37
            2: ADV_CHNL_38
            4: ADV_CHNL_39
            7: ADV_CHNL_ALL
        [<adv_filter_policy>]:
            0: ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY
            1: ADV_FILTER_ALLOW_SCAN_WLST_CON_ANY
            2: ADV_FILTER_ALLOW_SCAN_ANY_CON_WLST
            3: ADV_FILTER_ALLOW_SCAN_WLST_CON_WLST
        [<peer_addr_type>]: peer addr type
            0: PUBLIC
            1: RANDOM
        [<peer_addr>]: remote peer bd_addr
        """
        if adv_filter_policy is not None and peer_addr_type is not None and peer_addr is not None:
            self.ser.write_cmd("AT+BLEADVPARAM={},{},{},{},{},{},{},\"{}\"".format(int_min, int_max, adv_type, addr_type, 
                                                                        adv_chnl, adv_filter_policy, peer_addr_type, peer_addr))
        else:
            self.ser.write_cmd("AT+BLEADVPARAM={},{},{},{},{}".format(int_min, int_max, adv_type, addr_type, adv_chnl))
        resp = self.ser.read_response()
        self._verbose(resp)
        logger.debug("Advertising parameters set: {}".format(resp))

    def get_ble_adv_param(self) -> dict:
        """
        Get advertising parameters.
        Response: <adv_int_min>,<adv_int_max>,<adv_type>,<own_addr_type>,<channel_map>,
                  <filter_policy>,<peer_addr_type>,<peer_addr>
        """
        self.ser.write_cmd("AT+BLEADVPARAM?")
        resp = self.ser.read_response()
        self._verbose(resp)
        resp = resp[1].strip("+BLEADVPARAM:").split(",")
        param_dict = {
            "adv_int_min": resp[0],
            "adv_int_max": resp[1],
            "adv_type": resp[2],
            "own_addr_type": resp[3],
            "channel_map": resp[4],
            "filter_policy": resp[5],
            "peer_addr_type": resp[6],
            "peer_addr": resp[7]
        }
        logger.info("Advertising parameters queried: {}".format(param_dict))
        return param_dict

    def start_ble_adv(self):
        """Start advertising on BLE device."""
        self.ser.write_cmd("AT+BLEADVSTART")
        resp = self.ser.read_response()
        self._verbose(resp)
        logger.info("Advertising start: {}".format(resp))

    def stop_ble_adv(self):
        """Stop advertising on BLE device."""
        self.ser.write_cmd("AT+BLEADVSTOP")
        resp = self.ser.read_response()
        self._verbose(resp)
        logger.info("Advertising stop: {}".format(resp))


class Central_BLE(BLE_AT):

    def ble_init(self):
        self.ser.write_cmd("AT+BLEINIT=1")
        resp = self.ser.read_response()
        self._verbose(resp)
        logger.info("BLE central device initialized.")

    def set_ble_scan_param(self, scan_type: int, addr_type: int, filter_policy: int, scan_interval: int, scan_window: int) -> None:
        """
        Set BLE scan parameters.
        Arguments:
        <scan_type>:
            0: Passive
            1: Active
        <addr_type>:
            0: Public
            1: Random
            2: RPA Public
            3: RPA Random
        <filter_policy>:
            0: BLE_SCAN_FILTER_ALLOW_ALL
            1: BLE_SCAN_FILTER_ALLOW_ONLY_WLST
            2: BLE_SCAN_FILTER_ALLOW_UND_RPA_DIR
            3: BLE_SCAN_FILTER_ALLOW_WLIST_RPA_DIR
        <scan_interval>: range 0x0004-0x4000
        <scan_window>: range 0x0004-0x4000 and < <scan_interval>
        """
        self.ser.write_cmd(f"AT+BLESCANPARAM={scan_type},{addr_type},{filter_policy},{scan_interval},{scan_window}")
        resp = self.ser.read_response()
        self._verbose(resp)
        logger.debug("BLE Scan Parameters: scan_type={}, addr_type={}, filter_policy={}"\
                     "scan_interval={}, scan_window={}".format(scan_type, addr_type, filter_policy,
                                                                scan_interval, scan_window))
        self.attributes["BLESCANPARAM"] = [scan_type, addr_type, filter_policy, scan_interval, scan_window]

    def get_ble_scan_params(self) -> dict:
        """
        Get BLE scan parameters currently set.
        Response: <scan_type>,<own_type_addr>,<filter_policy>,<scan_interval>,<scan_window>
        """
        self.ser.write_cmd("AT+BLESCANPARAM?")
        resp = self.ser.read_response()
        self._verbose(resp)
        params = resp[1].strip("+BLESCANPARAM:").split(",")
        self.attributes["BLESCANPARAM"] = params
        logger.debug("BLE scan parameters: scan_type={}, addr_type={}, filter_policy={}, "\
                     "scan_interval={}, scan_window={}".format(*params))
        param_dict = {
            "scan_type": params[0],
            "own_addr_type": params[1],
            "filter_policy": params[2],
            "scan_interval": params[3],
            "scan_window": params[4]
        }
        return param_dict

    def filter_ble_scan(self, interval: int, filter_type: int, filter_param: str=None) -> None:
        """
        Filter BLE scan results.
        Arguments:
        <enable>:
            0: disable scan
            1: enable scan
        [<interval>]:
            scan duration in seconds
        [<filter_type>]:
            1: 'MAC'
            2: 'NAME'
        [<filter_param>]:
            filter parameter of device corressponding to <filter_type>
            filter_param is an exact string value of that returned in Response
        """
        if filter_type not in {1, 2}:
            logger.error("User provided incorrect value: {}".format(filter_type))
            raise ValueError("filter_type must be either 1 or 2.")
        if filter_param is not None:
            self.ser.write_cmd("AT+BLESCAN=1,{},{},\"{}\"".format(interval, filter_type, filter_param))
        else:
            self.ser.write_cmd("AT+BLESCAN=1,{},{}".format(interval, filter_type))
        resp = self.ser.read_response()
        self._verbose(resp)


    def start_ble_scan(self):
        """Starts continuous BLE scan."""
        self.ser.write_cmd("AT+BLESCAN=1")
        resp = self.ser.read_response()
        self._verbose(resp)
        logger.info("Starting BLE scan.")

    def _get_addr_type(self, val: str) -> str:
        addr_types = {
            "0": "Public",
            "1": "Random",
            "2": "RPA Public",
            "3": "RPA Random"
        } 
        try:
            return addr_types[str(val)]
        except IndexError as err:
            logger.error("Unknown address type: {}".format(val))
        return "Unknown"

    def stop_ble_scan(self) -> dict:
        """
        Stops BLE scan.
        Response: <addr>,<rssi>,<adv_data>,<scan_rsp_data>,<addr_type>
        """
        discovered = {}
        self.ser.write_cmd("AT+BLESCAN=0")
        resp = self.ser.read_response()
        self._verbose(resp)
        logger.info("Stopping BLE scan.")
        for res in resp[:-2]:
            vals = res.strip("+BLESCAN:").split(",")
            discovered[vals[0]] = {
                "Address": vals[0],
                "RSSI": vals[1],
                "ADV Data": vals[2],
                "Response Data": vals[3],
                "Address Type": self._get_addr_type(vals[4])
            }
        logger.info("BLE Scan Results: {}".format(discovered))
        return discovered

def mul_625(n):
    int_mul = {}
    for i in range(n):
        m = i * 0.625

c = Central_BLE("/dev/ttyUSB0", verbose=True)
c.ble_init()
c.set_ble_scan_param(0,0,0,320,48)
c.get_ble_scan_params()
c.start_ble_scan()

start = time.perf_counter()
while True:
    end = time.perf_counter() - start
    if end >= 10:
        break
disc = c.stop_ble_scan()
print(disc)