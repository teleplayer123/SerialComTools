import struct 
import sys
import usb.core
import usb.util
from time import sleep

from hex_dump import xdump

if len(sys.argv) > 0:
    CHANNEL = int(sys.argv[1])
else:
    CHANNEL = 25

#cc2531 Requests
GET_IDENTITY = 0xc0
SET_POWER = 0xc5
GET_POWER = 0xc6
SET_START = 0xd0
SET_END = 0xd1
SET_CHANNEL = 0xd2


class CC2531_Packet:
    
    def __init__(self, raw_data):
        pdata = struct.unpack("<I2BHB3H", raw_data[0:15])
        self.preamble = pdata[0]
        self.sfd = pdata[1]
        self.length = pdata[2]
        self.frame_control = pdata[3]
        self.seq_num = pdata[4]
        self.dest_pan = pdata[5]
        self.dest_add = pdata[6]
        self.src_add = pdata[7]
        self.data = raw_data

    def __str__(self):
        return f"""
        Preamble: {hex(self.preamble)}
        SFD: {hex(self.sfd)}
        Length: {int(self.length)}
        Frame Control: {hex(self.frame_control)}
        Sequence Number: {int(self.seq_num)}
        Destination PAN: {hex(self.dest_pan)}
        Destination Address: {hex(self.dest_add)}
        Source Address: {hex(self.src_add)}
        DATA DUMP:
        {xdump(self.data)}
        """

cc2531_vendor = 0x0451
cc2531_product = 0x16ae
cc2531_ep = 0x83


dev = usb.core.find(idVendor=cc2531_vendor, idProduct=cc2531_product)
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
        data = dev.read(cc2531_ep, 4096, 1500)
        try:
            pkt = CC2531_Packet(data)
            print(str(pkt))
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
