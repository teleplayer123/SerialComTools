#!/usr/bin/python3

import os
import struct 
import sys
import usb.core
import usb.util
from time import asctime, sleep, time

from hex_dump import xdump


DIRNAME = "cc2540_logs"
if not os.path.exists(DIRNAME):
    os.mkdir(DIRNAME)
SUBDIR = os.path.join(DIRNAME, "{}".format(asctime()))
if not os.path.exists(SUBDIR):
    os.mkdir(SUBDIR)

FILENAME = SUBDIR + "/ble_sniff_{}.txt"

if len(sys.argv) > 1:
    CHANNEL = int(sys.argv[1])
else:
    CHANNEL = 37

#cc2540 Requests
GET_IDENTITY = 0xc0
SET_POWER = 0xc5
GET_POWER = 0xc6
SET_START = 0xd0
SET_END = 0xd1
SET_CHANNEL = 0xd2

class LL_Header:

    def __init__(self, raw_data):
        phy_hdr = struct.unpack("<4sBB", raw_data[:6])
        self.access_addr = self.fmt_addr(phy_hdr[0])
        self.pdu = self.get_pdu_hdr(phy_hdr[1])
        self.data_len = int(phy_hdr[2]) #length 8 bits
        self.pdata = raw_data[-self.data_len:]
        self.data = raw_data

    def fmt_addr(self, data):
        bs = reversed(["%02x" % data[i] for i in range(len(data))])
        return ":".join(bs)

    def get_pdu_hdr(self, data):
        """
        pdu type: 4 bits
        rfu: 1 bit
        ChSel: 1 bit
        TxAdd: 1 bit
        RxAdd: 1 bit
        """
        res = {}
        pdu_type = data >> 4 & 0b1111
        rfu = int((data & 0b0001) == 1)
        chsel = int((data & 0b0010) == 2)
        txadd = int((data & 0b0100) == 4)
        rxadd = int((data & 0b1000) == 8) 
        return {
            "pdu_type": (self.get_pdu_type(pdu_type)),
            "rfu": rfu,
            "chsel": chsel,
            "txadd": txadd,
            "rxadd": rxadd
        }

    def get_pdu_type(self, bits):
        name = None
        val = None
        pdu_types = {
            "ADV_IND": 0b0000,
            "ADV_DIRECT_IND": 0b0001,
            "ADV_NONCONN_IND": 0b0010,
            "SCAN_REQ": 0b0011,
            "SCAN_RSP": 0b0100,
            "CONNECT_IND": 0b0101,
            "ADV_SCAN_IND": 0b0110
        }
        for k, v in pdu_types.items():
            if bits & v:
                name = k
                val = v
                break
        return name, val

    def __str__(self):
        return f"""
        Channel: {CHANNEL}
        Access Address: {self.access_addr}
        PDU: {self.pdu}
        Data Length: {self.data_len}
        Payload: 
        {xdump(self.pdata)}
        Data Dump:
        {xdump(self.data)}
        """


class CC2540_Packet:
    
    def __init__(self, raw_data):
        pdata = struct.unpack("<BIQB", raw_data[0:14])
        self.p_info = pdata[0]
        self.p_num = pdata[1]
        self.p_time = self.calc_time(pdata[2])
        self.p_len = pdata[3]
        self.data = raw_data
        
    def fmt_addr(self, data):
        bs = ["%02x" % data[i] for i in range(len(data))]
        return ":".join(bs)

    def calc_time(self, tm):
        tm_hi = tm & 0xFFFF
        tm_lo = tm >> 16
        tms = (tm_hi*5000 + tm_lo) >> 5
        return float(tms)
    
    def __str__(self):
        return f"""
        Channel: {CHANNEL}
        Info: {self.p_info}
        Packet Number: {hex(self.p_num)}
        Timestamp: {self.p_time}
        Length: {self.p_len}
        DATA:
        {xdump(self.data)}
        """

def write_to_file(*args, arg_has_header=False, filename=None):
    if filename is not None:
        filename = filename + "_{}".format(int(time()))
    else:
        filename = FILENAME.format(int(time()))
    with open(filename, "w", encoding="utf-8") as fh:
        if arg_has_header == True:
            for i in range(0, len(args), 2):
                fh.write(args[i])
                fh.write(args[i+1])
        else:
            for arg in args:
                fh.write(arg)
    

#adv access address: 0x8e89bed6

#you can get id's from lsusb
cc2540_vendor = 0x0451
cc2540_product = 0x16b3
cc2540_ep = 0x83


dev = usb.core.find(idVendor=cc2540_vendor, idProduct=cc2540_product)
"""
dev.set_configuration()
config = dev.get_active_configuration()
iface = config[(0,0)]
"""
"""
##bConfigurationValue is needed to set_configuration to work with device
bconfig = iface.bConfigurationValue
config = usb.util.find_descriptor(dev)
config.set()
print(config)
"""

#write(endpoint_addr, msg, timeout)
#read(endpoint_addr, read_size, timeout)
#ctrl_transfer(bmRequestType, bmRequest, wValue, wIndex, payload/length)
# -bmRequestType controls data transfer direction (OUT and IN) OUT=0x40, IN=0xC0
# -bmRequest is the action command:  
ret = dev.ctrl_transfer(0xc0, GET_IDENTITY, 0, 0, 256)
print(f"ID: {ret}")
dev.ctrl_transfer(0x40, SET_POWER, wIndex=4)
while True:
    power = dev.ctrl_transfer(0xc0, GET_POWER, 0, 0, 1)
    print(power)
    if power[0] == 4:
        break
    else:
        sleep(1)
dev.ctrl_transfer(0x40, SET_CHANNEL, 0, 0, [CHANNEL])
dev.ctrl_transfer(0x40, SET_CHANNEL, 0, 1, [0x00])

dev.ctrl_transfer(0x40, SET_START)
while True:
    try:
        data = dev.read(cc2540_ep, 4096, 1500)
        try:
            pkt = CC2540_Packet(data)
            print(str(pkt))
            ll = LL_Header(data[8:])
            print(str(ll))
            print(f"RAW DATA: \n{xdump(data)}")
            write_to_file("CC2540 PACKET:\n", str(pkt), "\nBLE PACKET: \n", str(ll), arg_has_header=True)
        except struct.error:
            continue
    except usb.core.USBError as err:
        print(f"Error: {err}")
        continue
    except KeyboardInterrupt:
        dev.ctrl_transfer(0x40, SET_POWER, wIndex=0)
        power = dev.ctrl_transfer(0xc0, GET_POWER, 0, 0, 1)
        print(f"Shutting down power: {power}")
        dev.ctrl_transfer(0x40, SET_END)
        break
