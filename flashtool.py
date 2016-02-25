#!/usr/bin/env python
import usb.core
from usb.core import USBError
import usb.util
import sys
from time import sleep

#Pause between request and receive duration
PAUSE=0.01

#Directions
HOST_TO_DEVICE = 0x00
DEVICE_TO_HOST = 0x80

#Types
CLASS = 0x20

#Recipients
INTERFACE = 0x01
OTHER = 0x11

#Requests
SET_REPORT = 0x09
GET_REPORT = 0x01
GET_STATUS = 0x00


URB_FUNCTION_CLASS_INTERFACE = 0x001b


class Keyboard(object):
    def __init__(self):
        self.device = usb.core.find(idVendor=0x04d9, idProduct=0x0141)

        if self.device is None:
            raise ValueError('Device not found')
        if self.device.is_kernel_driver_active(0):
            try:
                self.device.detach_kernel_driver(0)
                print ("kernel driver detached for interface 0")
            except usb.core.USBError as e:
                sys.exit("Could not detach kernel driver for interface 0: ")
        else:
            print ("no kernel driver attached for interface 0")

        if self.device.is_kernel_driver_active(1):
            try:
                self.device.detach_kernel_driver(1)
                print ("kernel driver detached for interface 1")
            except usb.core.USBError as e:
                sys.exit("Could not detach kernel driver for interface 1: ")
        else:
            print ("no kernel driver attached for interface 1")

        if self.device.is_kernel_driver_active(2):
            try:
                self.device.detach_kernel_driver(2)
                print ("kernel driver detached for interface 2")
            except usb.core.USBError as e:
                sys.exit("Could not detach kernel driver for interface 2: ")
        else:
            print ("no kernel driver attached for interface 2")


        try:
            self.device.set_configuration()
        except:
            sys.exit("Could not set configuration")

        # try:
        #     usb.util.claim_interface(self.device, 0)
        #     print ("claimed device for interface 0")
        # except:
        #     sys.exit("Could not claim device for interface 0: ")
        #
        # try:
        #     usb.util.claim_interface(self.device, 1)
        #     print ("claimed device for interface 1")
        # except:
        #     sys.exit("Could not claim device for interface 1: ")
        #
        # try:
        #     usb.util.claim_interface(self.device, 2)
        #     print ("claimed device for interface 2")
        # except:
        #     sys.exit("Could not claim device for interface 2: ")

        # try:
        #     self.device.set_interface_altsetting(interface = 0, alternate_setting = 0)
        # except USBError:
        #     print ("could not set alternate setting for interface 0")
        # try:
        #     self.device.set_interface_altsetting(interface = 1, alternate_setting = 0)
        # except USBError:
        #     print ("could not set alternate setting for interface 1")
        # try:
        #     self.device.set_interface_altsetting(interface = 2, alternate_setting = 0)
        # except USBError:
        #     print ("could not set alternate setting for interface 2")
        self.sendEp = 0x04
        self.recvEp = 0x83

    def _send(self, msg):
        data = bytes(self._fix(msg))
        assert self.device.write(self.sendEp, data) == len(data)

    def _recv(self, numBytes, timeout=1000):
        sleep(PAUSE)
        return self.device.read(self.recvEp, numBytes, timeout)

    def _send_ctrl(self, request_type, request, value, index, msg):
        self.device.ctrl_transfer(request_type, request, value, index, None)

    def _recv_ctrl(self, request_type, request, value, index, numBytes, timeout=5000):
        return self.device.ctrl_transfer(request_type, request, value, index, numBytes, timeout)

    def _new_msg(self):
        return [0]*64

    def _set_command(self, msg, cmd, subcmd):
        msg[0] = cmd
        msg[1] = subcmd

    def _define_area(self, msg, start, end):
        msg[4] = start[3]
        msg[5] = start[2]
        msg[6] = start[1]
        msg[7] = start[0]
        msg[8] = end[3]
        msg[9] = end[2]
        msg[10] = end[1]
        msg[11] = end[0]

    def _set_data(self, msg, data):
        msg[12:64] = data

    def _fix(self, data):
        data[2:4] = self._crc16(data)
        return data

    def _crc16(self, data, bits=8):
        crc = 0x0000
        for code in data:
            crc = crc ^ (code << 8)
            for bit in range(0, bits):
                crc = crc << 1
                if (crc&0x10000):
                    crc = ((crc ^ 0x1021) & 0xFFFF)
        return [crc & 0x00FF, crc >> 8]

    def int2address(self, data):
        return [data>>24, data>>16 & 0x00FF, data>>8 & 0x0000FF, data & 0x000000FF]

    def bytes2str(self, data):
        return ''.join('{:02x}'.format(x) for x in data)

    def _set_report(self):
        self._send_ctrl(HOST_TO_DEVICE|CLASS|INTERFACE, SET_REPORT, 0x0200, 0, "1")

    def _get_report(self):
        return self._recv_ctrl(DEVICE_TO_HOST|CLASS|INTERFACE, GET_REPORT, 0x0100, 1, 64)

    def send_bump(self):
        msg = self._new_msg()
        self._set_command(msg, 3, 0)
        self._send(msg)
        return self._recv(64)

    def enter_flash_mode(self):
        msg = self._new_msg()
        self._set_command(msg, 4, 1)
        self._send(msg)

    def leave_flash_mode(self):
        msg = self._new_msg()
        self._set_command(msg, 4, 0)
        self._send(msg)

    def read_flash(self, pos):
        msg = self._new_msg()
        self._set_command(msg, 1, 2)
        self._define_area(msg, self.int2address(pos), self.int2address(pos+64))
        self._send(msg)
        return self._recv(64)

    def write_flash(self, pos, data):
        msg = self._new_msg()
        self._set_command(msg, 1, 1)

        self._define_area(msg, self.int2address(pos), self.int2address(pos+64))
        self._set_data(msg, data)
        self._send(msg)

    def check_flash(self, pos, data):
        msg = self._new_msg()
        self._set_command(msg, 1, 0)
        self._define_area(msg, self.int2address(pos), self.int2address(pos+64))
        self._set_data(msg, data)
        self._send(msg)

    def read_version(self):
        return self.read_flash(0x00002800)

    def read_firmware(self):
        out = bytearray(0x20000)
        newFile=open('flash.img','wb')
        for pos in range(0, 0x20000, 0x40):
            out[pos:pos+64] = self.read_flash(pos)
        newFile.write(out)
        newFile.close()




kbd = Keyboard()
out = kbd.send_bump()
print(kbd.bytes2str(out))
print("Version is:")
out = kbd.read_version()
print(kbd.bytes2str(out))
#input("Press Enter to continue...")
print("flash is:")

kbd.read_firmware()
#print(kbd.bytes2str(kbd.read_firmware(start, end)))
