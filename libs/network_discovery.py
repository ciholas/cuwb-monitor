# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import netifaces
import select
import signal
import socket
import sys
import threading
from ipaddress import ip_address, IPv4Interface

# Local libraries
from cdp import CDP, CDPStreamInformation, HostnameAnnounce, InstanceAnnounce


class CuwbNetworkInformation:
    """CUWB Network Information Class Definition"""

    def __init__(self, instance_name='', hostname='', source_ip=0):
        self.instance_name = instance_name
        self.hostname = hostname
        self.source_ip = ip_address(source_ip)
        self.cdp_streams = {}

    def __eq__(self, other):
        if isinstance(other, CuwbNetworkInformation):
            return self.instance_name == other.instance_name \
                   and self.hostname == other.hostname \
                   and self.source_ip == other.source_ip

    def __hash__(self):
        return hash((self.instance_name, self.hostname, self.source_ip))

    def __str__(self):
        return "Network: {}, Hostname: {}, IP: {}, CDP Streams: {}".format(self.instance_name,
                                                                           self.hostname,
                                                                           self.source_ip,
                                                                           ', '.join(str(stream) for stream in self.cdp_streams.values()))


class ListeningAddrInfo:
    """Listening Address Information Class Definition"""

    def __init__(self, ip, port, interface):
        self.ip = ip
        self.port = port
        self.interface = interface

    def __eq__(self, other):
        if isinstance(other, ListeningAddrInfo):
            return self.ip == other.ip and self.port == other.port \
                   and self.interface == other.interface
    def __hash__(self):
        return hash((self.ip, self.port, self.interface))

    def __str__(self):
        return "{}:{} on {}".format(self.ip, self.port, self.interface)


class StreamInformation:
    """CDP Stream Infomation Class Definition"""
    any_interface = ip_address(0)

    def __init__(self, ip, port, ifc=0, netmask='255.255.255.255', alias='N/A'):
        self.ip = ip_address(ip)
        self.port = port
        self.interface = ip_address(ifc)
        self.netmask = ip_address(netmask)
        self.alias = alias
        self.network_address = IPv4Interface(str(self.interface) +'/'+ str(self.netmask)).network

    def is_on_same_subnet(self, ifc):
        return self.network_address == IPv4Interface(ifc+'/'+str(self.netmask)).network

    def __eq__(self, other):
        if isinstance(other, StreamInformation):
            return self.ip == other.ip and self.port == other.port \
                   and self.interface == other.interface

    def __hash__(self):
        return hash((self.ip, self.port, self.interface))

    def __str__(self):
        return "{} - {}/{} -> {}:{}".format(self.alias, self.interface,
                                            self.netmask,
                                            self.ip, self.port)


class CuwbNetworkInformationReceiver:

    def __init__(self):
        config_sock = ListenSocket('239.255.76.67', 7671)
        self.rx_thread = RxThread(config_sock, self.handle_cdp_data)
        self.rx_thread.start()
        self.available_networks = {}
        self.network_timers = {}
        self.local_interfaces = self.get_local_interfaces()

    def get_local_interfaces(self):
        local_interfaces = []
        for ifc in netifaces.interfaces():
            for ifc_info in netifaces.ifaddresses(ifc).get(netifaces.AF_INET, []):
                if 'addr' in ifc_info:
                    local_interfaces.append(ifc_info['addr'])
        return local_interfaces

    def get_equivalent_local_interface(self, cuwb_net):
        if cuwb_net.interface == StreamInformation.any_interface:
            print('Using the interface 0.0.0.0 may result in receiving packets duplicated {} times.'.format(len(self.local_interfaces)))
            return self.local_interfaces

        for local_ifc in self.local_interfaces:
            if cuwb_net.is_on_same_subnet(local_ifc):
                return [local_ifc]
        return ['127.0.0.1']

    def is_interface_available(self, cuwb_net):
        if cuwb_net.interface == StreamInformation.any_interface:
            return True

        for local_ifc in self.local_interfaces:
            if cuwb_net.is_on_same_subnet(local_ifc):
                return True
        return False

    def remove_cuwb_network(self, serial_number):
        print("Removing CUWB Server {} from the list".format(serial_number))
        # If no data is received in 30 seconds from a Cuwb Server,
        # remove it from the list of available networks.
        if serial_number in self.available_networks:
            del self.available_networks[serial_number]
        if serial_number in self.network_timers:
            del self.network_timers[serial_number]

    def reopen(self):
        config_sock = ListenSocket('239.255.76.67', 7671)
        if not self.rx_thread.isAlive():
            self.rx_thread = RxThread(config_sock, self.handle_cdp_data)
            self.rx_thread.start()

    def add_timer(self, serial_number):
        # 30-second timeout before attempting to remove any CUWB Network.
        self.network_timers[serial_number] = CdpTimeout(30, serial_number, self.remove_cuwb_network)

    def handle_cdp_data(self, cdp_packet, server_ip):
        for cdp_stream in cdp_packet.data_items_by_type.get(CDPStreamInformation.type, []):
            # Get network information in the CDP Stream Information data item
            ip = cdp_stream.destination_ip
            port = cdp_stream.destination_port
            ifc = cdp_stream.interface_ip
            netmask = cdp_stream.interface_netmask
            alias = cdp_stream.name
            stream = StreamInformation(ip, port, ifc, netmask, alias)

            # Avoids duplicating of packets caused by listening to the same data on multiple interfaces
            if stream.interface == ip_address(0):
                stream.interface = server_ip
                stream.network_address = IPv4Interface(str(stream.interface) +'/'+ str(stream.netmask)).network

            # Check if there is already information about this CUWB network and update the CDP streams
            if cdp_packet.serial_number in self.available_networks:
                self.available_networks[cdp_packet.serial_number].cdp_streams[stream.alias] = stream
                # Reset timer since we are still getting data from this CUWB server
                self.network_timers[cdp_packet.serial_number].reset()
            else:
                net_info = CuwbNetworkInformation(source_ip=server_ip)
                net_info.cdp_streams[stream.alias] = stream
                self.available_networks[cdp_packet.serial_number] = net_info
                # Start timer since this is the first time we hear from this CUWB server
                self.add_timer(cdp_packet.serial_number)

        for instance_info in cdp_packet.data_items_by_type.get(InstanceAnnounce.type, []):
            # Check if there is already information about this CUWB network and update the instance name
            if cdp_packet.serial_number in self.available_networks:
                self.available_networks[cdp_packet.serial_number].instance_name = instance_info.instance_name
                # Reset timer since we are still getting data from this CUWB server
                self.network_timers[cdp_packet.serial_number].reset()
            else:
                net_info = CuwbNetworkInformation(source_ip=server_ip)
                net_info.instance_name = instance_info.instance_name
                self.available_networks[cdp_packet.serial_number] = net_info
                # Start timer since this is the first time we hear from this CUWB server
                self.add_timer(cdp_packet.serial_number)

        for hostname_info in cdp_packet.data_items_by_type.get(HostnameAnnounce.type, []):
            # Check if there is already information about this host and update the hostname
            if cdp_packet.serial_number in self.available_networks:
                self.available_networks[cdp_packet.serial_number].hostname = hostname_info.hostname
                # Reset timer since we are still getting data from this CUWB server
                self.network_timers[cdp_packet.serial_number].reset()
            else:
                net_info = CuwbNetworkInformation(source_ip=server_ip)
                net_info.hostname = hostname_info.hostname
                self.available_networks[cdp_packet.serial_number] = net_info
                # Start timer since this is the first time we hear from this CUWB server
                self.add_timer(cdp_packet.serial_number)

    def __del__(self):
        self.rx_thread.join()
        self.network_timers = None


class ListenSocket():

    def __init__(self, group, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if sys.platform != 'win32':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.bind(('', port))
        for ifc in netifaces.interfaces():
            for ifc_info in netifaces.ifaddresses(ifc).get(netifaces.AF_INET, []):
                if 'addr' in ifc_info:
                    self.socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(group) + socket.inet_aton(ifc_info['addr']))

    def __del__(self):
        self.socket.close()


class RxThread(threading.Thread):
    """ Handling of CDP data reception """

    def __init__(self, socket, add_packet_cb):
        self._stopevent = threading.Event()
        self.sock = socket
        self.add_packet = add_packet_cb
        threading.Thread.__init__(self, name="RxThread")

    def run(self):
        while not self._stopevent.isSet():
            # Check if data are available for non-blocking reading
            ready = select.select([self.sock.socket], [], [], 0)
            if ready[0]:
                data, addr = self.sock.socket.recvfrom(65535)
                rx_packet = CDP(data)
                self.add_packet(rx_packet, addr[0])  # IP address of the server
        self.sock.socket.close()

    def join(self, timeout=None):
        self._stopevent.set()
        threading.Thread.join(self, timeout)

    def __del__(self):
        self.join()


class CdpTimeout():

    def __init__(self, sec, serial_number, remove_cuwb_net_cb):
        self.sec = sec
        self.serial_number = serial_number
        self.remove_cuwb_net = remove_cuwb_net_cb
        self.start()

    def start(self):
        self.timer = threading.Timer(self.sec, self.remove_cuwb_net, (self.serial_number,))
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start()

    def __del__(self):
        if self.timer.is_alive():
            self.timer.cancel()
