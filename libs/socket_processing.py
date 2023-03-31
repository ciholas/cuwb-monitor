# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import sys
import socket
import struct
import time
import ipaddress
from pyqtgraph import QtCore

# Local libraries
import cdp
from collections import deque
from network_objects import *
from settings import *


class SocketProcessing(QtCore.QThread):
    """Handling of CDP data reception. Uses Qt Thread to work with data plotting."""
    raw_data = deque([])

    def __init__(self, ip, port, interface):
        QtCore.QThread.__init__(self)
        self._stopevent = False

        # Setup UDP socket for listening to CDP packets
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if ipaddress.ip_address(ip).is_multicast:
            try :
                self.sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(ip)+socket.inet_aton(interface))
            except OSError as ose :
                if sys.platform == 'win32' and socket.SOL_IP != 0 :
                    self.sock.setsockopt(0, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(ip)+socket.inet_aton(interface))
                else :
                    print("Socket configuration error when setting up ListenSocket with IP:{} INTERFACE:{} and PORT:{}".format(ip, interface, port) )
                    print(ose)

        if sys.platform == 'win32': self.sock.bind((interface, port))
        else:                       self.sock.bind((ip, port))
        self.sock.settimeout(0.250)

    def run(self):
        """Main thread loop. Listens to sockets and processes data"""
        while UwbNetwork.running and not self._stopevent:
            try:
                data, addr = self.sock.recvfrom(65536) # 2^16 is the max size of a CDP packet
            except socket.timeout:
                print("time out", end='\r', flush=True)
                continue

            self.raw_data.append(data)
        self.sock.close()

    def wait(self):
        self._stopevent = True

    def __del__(self):
        self.wait()


class CdpProcess(SocketProcessing):

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.buffer_empty_count = 0
        self._stopevent = False

    def run(self):
        while UwbNetwork.running and not self._stopevent:
            try:
                packet = cdp.CDP(super(CdpProcess, self).raw_data.popleft())
            except IndexError:
                self.buffer_empty_count += 1
                if self.buffer_empty_count > 20:
                    self.usleep(1)
                    self.buffer_empty_count = 0
                continue
            except ValueError as e:
                if str(e) == 'Incomplete CDP Packet':
                    print(e)
                    pass
                elif 'Unrecognized String' in str(e):
                    print(e)
                    continue
                elif 'Packet Size Error' in str(e):
                    continue
                else:
                    raise

            if not packet.serial_number.as_int in UwbNetwork.nodes:
                Node(packet.serial_number.as_int)

            for data_item in packet.data_items:
                UwbNetwork.nodes[packet.serial_number.as_int].update(data_item, data_item.di_name, time.monotonic())

    def wait(self):
        self._stopevent = True

    def __del__(self):
        self.wait()
