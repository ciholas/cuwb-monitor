# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import netifaces
from operator import attrgetter
from pyqtgraph import QtCore, QtGui
import time

# Local libraries
from network_objects import UwbNetwork
from network_discovery import CuwbNetworkInformationReceiver, StreamInformation, ListeningAddrInfo
from settings import *
from socket_processing import SocketProcessing, CdpProcess


class NetworkDiscoveryWindow(QtGui.QMainWindow):

    def __init__(self, num_processes, ip, port, ifc):
        super().__init__()
        self.setWindowTitle("CUWB Monitor - Network Discovery")
        self.central = QtGui.QWidget()
        self.central.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.central_layout = QtGui.QVBoxLayout()
        self.central.setLayout(self.central_layout)
        self.setCentralWidget(self.central)

        self.network_discovery = CuwbNetworkInformationReceiver()
        # Save available networks to check if there are changes
        # when trying to refresh the list
        self.previous_cuwb_nets = set(self.network_discovery.available_networks.values())
        self.num_processes = num_processes
        self.stream_idx = 0
        # All CDP StreamInformation objects indexed by self.stream_idx
        self.cdp_streams = dict()
        # All QCheckBoxes for each CDP StreamInformation objects indexed by self.stream_idx
        self.stream_checkboxes = dict()
        # Addresses (ListeningAddrInfo objects) that we are currently listening on
        self.active_addresses = set()
        self.active_any_interface_streams = set()
        # All SocketProcessing and CdpProcess threads indexed by ListeningAddrInfo objects,
        # the values are lists of threads
        self.rx_threads = dict()

        # Add new connection if command line arguments were provided
        if (ip is not None) or (port is not None) or (ifc is not None):
            self.add_manual_connection(ip, port, ifc)

        self.display_cuwb_networks()
        self.timer = self.startTimer(1000)

    def add_manual_connection(self, ip, port, ifc):
        # Replace None values with defaults
        if ip is None: ip = UDP_IP
        if port is None: port = UDP_PORT
        if ifc is None: ifc = IFACE_IP

        stream = StreamInformation(ip, port, ifc)
        if self.network_discovery.is_interface_available(stream):
            stream.equivalent_addresses = self.get_equivalent_addresses(stream)
            self.start_cdp_processing(stream)
        else:
            print('Invalid interface IP')
            exit()

    def display_cuwb_networks(self):
        label = QtGui.QLabel("Select a network:")
        label.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.central_layout.addWidget(label)
        self.scroll_area = QtGui.QScrollArea()
        self.scroll_area.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        self.scroll_area.setFrameStyle(QtGui.QFrame.Panel | QtGui.QFrame.Sunken)
        self.scroll_area.setBackgroundRole(QtGui.QPalette.Light)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.central_layout.addWidget(self.scroll_area)
        self.display_cuwb_networks_widget()
        self.display_active_addresses_widget()

    def display_cuwb_networks_widget(self):
        self.cuwb_nets = QtGui.QWidget()
        self.cuwb_nets.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Maximum)
        nets_layout = QtGui.QVBoxLayout()
        self.cuwb_nets.setLayout(nets_layout)
        self.scroll_area.setWidget(self.cuwb_nets)

        if len(self.network_discovery.available_networks) == 0:
            label = QtGui.QLabel("No CUWB networks are available")
            label.setStyleSheet('color: red')
            nets_layout.addWidget(label, QtCore.Qt.AlignCenter)
        else:
            # Restart CDP streams indexes and empty all containers to avoid duplication
            self.stream_idx = 0
            self.cdp_streams = dict()
            self.stream_checkboxes = dict()
            # All available addresses indexed by ListeningAddrInfo  objects.
            # The values are sets of stream_idx. This information is used to
            # auto check/uncheck checkboxes equivalent addresses.
            # It does not include the indexes of streams with interface '0.0.0.0'
            self.available_addresses = dict()
            # It includes the indexes of streams with interface '0.0.0.0'
            self.any_interface_streams = dict()
            for serial, net_info in sorted(self.network_discovery.available_networks.items(),
                                            key=lambda item: (item[1].instance_name, item[1].hostname, item[1].source_ip)):
                cuwb_net = QtGui.QFrame()
                cuwb_net.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Raised)
                cuwb_net.setLineWidth(1)
                net_layout = QtGui.QGridLayout()
                net_layout.setMargin(0)
                cuwb_net.setLayout(net_layout)

                header = QtGui.QWidget()
                header_layout = QtGui.QGridLayout()
                header.setLayout(header_layout)
                label = QtGui.QLabel('Network: <b>{} ({})</b>'.format(net_info.instance_name, serial))
                header_layout.addWidget(label, 0, 0)
                label = QtGui.QLabel('Host: <b>{}</b>'.format(net_info.hostname))
                header_layout.addWidget(label, 0, 1)
                label = QtGui.QLabel('{}'.format(net_info.source_ip))
                header_layout.addWidget(label, 0, 2, QtCore.Qt.AlignRight)
                net_layout.addWidget(header, 0, 0)

                streams = QtGui.QWidget()
                streams_layout = QtGui.QGridLayout()
                streams.setLayout(streams_layout)
                idx = 0
                stream_order = ['external', 'internal', 'config', 'debug']
                for stream_name in stream_order:
                    # Check if we received information about the CDP stream
                    # before trying to display it
                    if stream_name not in net_info.cdp_streams:
                        continue
                    stream = net_info.cdp_streams[stream_name]
                    label = QtGui.QLabel('{}'.format(stream.alias.capitalize()))
                    streams_layout.addWidget(label, idx, 0)
                    label = QtGui.QLabel('{}/{}'.format(stream.interface, stream.netmask))
                    streams_layout.addWidget(label, idx, 1)
                    label = QtGui.QLabel('->')
                    streams_layout.addWidget(label, idx, 2, QtCore.Qt.AlignCenter)
                    label = QtGui.QLabel('{}:{}'.format(stream.ip, stream.port))
                    streams_layout.addWidget(label, idx, 3)
                    # Add CDP stream checkbox and connect Qt signal to callback function to handle state changes
                    self.stream_checkboxes[self.stream_idx] = QtGui.QCheckBox()
                    self.stream_checkboxes[self.stream_idx].stateChanged.connect(partial(self.stream_click_event, self.stream_idx))
                    streams_layout.addWidget(self.stream_checkboxes[self.stream_idx], idx, 4, QtCore.Qt.AlignRight)

                    if not self.network_discovery.is_interface_available(stream):
                        # Disable checkbox if interface is not on the same subnet
                        self.stream_checkboxes[self.stream_idx].setEnabled(False)
                    else:
                        # Dynamically add attribute to store the equivalent address(es)
                        # using the local interface(s)
                        stream.equivalent_addresses = self.get_equivalent_addresses(stream)

                        if stream.interface != StreamInformation.any_interface:
                            for listen_addr in stream.equivalent_addresses:
                                # Check if there is another CDP stream with the same IP, port and
                                # equivalent local interface and keep track of the indexes of these streams
                                if listen_addr not in self.available_addresses:
                                    self.available_addresses[listen_addr] = set()
                                self.available_addresses[listen_addr].add(self.stream_idx)
                                # Check if we are already listening on this address and autocheck the checkbox
                                if listen_addr in self.active_addresses:
                                    self.stream_checkboxes[self.stream_idx].setChecked(True)
                        else:
                            # Check if there is another CDP stream with the same IP, port and
                            # interface set to '0.0.0.0' and keep track of the indexes of these streams
                            if stream not in self.any_interface_streams:
                                self.any_interface_streams[stream] = set()
                            self.any_interface_streams[stream].add(self.stream_idx)
                            # Check if we are already listening on this address and autocheck the checkbox
                            if stream in self.active_any_interface_streams:
                                self.stream_checkboxes[self.stream_idx].setChecked(True)

                    # Keep track of all the displayed CDP streams and their indexes
                    self.cdp_streams[self.stream_idx] = stream
                    self.stream_idx += 1
                    idx += 1
                net_layout.addWidget(streams, 1, 0)
                nets_layout.addWidget(cuwb_net)

    def display_active_addresses_widget(self):
        self.addr_widget = QtGui.QWidget()
        self.addr_widget.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        addr_layout = QtGui.QVBoxLayout()
        self.addr_widget.setLayout(addr_layout)
        if len(self.active_addresses) > 0:
            label = QtGui.QLabel('Currently listening on:')
            addr_layout.addWidget(label)
        for stream in sorted(self.active_addresses, key=attrgetter('ip', 'port', 'interface')):
            label = QtGui.QLabel('{}:{} - Interface: {}'.format(stream.ip, stream.port, stream.interface))
            addr_layout.addWidget(label)
        self.central_layout.addWidget(self.addr_widget)

    def stream_click_event(self, idx):
        if idx in self.cdp_streams:
            stream = self.cdp_streams[idx]
            if self.stream_checkboxes[idx].isChecked():
                # Check all stream checkboxes with the same IP, port, and equivalent interfaces
                self.set_equivalent_checked(True, stream)
                self.start_cdp_processing(stream)
                self.refresh_active_addresses_widget()
            else:
                # Uncheck all stream checkboxes with the same IP, port, and equivalent interfaces
                self.set_equivalent_checked(False, stream)
                self.stop_cdp_processing(stream)
                self.refresh_active_addresses_widget()

    def refresh_cuwb_networks_widget(self):
        self.scroll_area.hide()
        self.display_cuwb_networks_widget()
        self.scroll_area.show()

    def refresh_active_addresses_widget(self):
        self.addr_widget.hide()
        self.display_active_addresses_widget()
        self.addr_widget.show()

    def get_equivalent_addresses(self, stream):
        """
        Returns a list of ListeningAddrInfo objects with the original ip and
        port specified in the StreamInformation object but with the equivalent
        local interface(s).
        """
        addr_list = []
        ip = str(stream.ip)
        port = stream.port
        interfaces = self.network_discovery.get_equivalent_local_interface(stream)
        for ifc in interfaces:
            listen_addr = ListeningAddrInfo(ip, port, ifc)
            addr_list.append(listen_addr)
        return addr_list

    def start_cdp_processing(self, stream):
        """
        Starts threads to receive CDP data and process it, using the IP, port,
        and equivalent local interface(s) specified in the StreamInformation object
        passed as an argument.
        """
        for listen_addr in stream.equivalent_addresses:
            if listen_addr not in self.rx_threads:
                thread_list = []
                thread_list.append(SocketProcessing(listen_addr.ip, listen_addr.port, listen_addr.interface))
                for n in range(self.num_processes):
                    cdp_process = CdpProcess()
                    cdp_process.start()
                    thread_list.append(cdp_process)
                thread_list[0].start()
                self.set_address_to_active(listen_addr)
                self.rx_threads[listen_addr] = thread_list
        if stream.interface == StreamInformation.any_interface:
            if stream not in self.active_any_interface_streams:
                self.active_any_interface_streams.add(stream)

    def set_address_to_active(self, listen_addr):
        if listen_addr not in self.active_addresses:
            self.active_addresses.add(listen_addr)
            print("Started listening on {}".format(listen_addr))

    def stop_cdp_processing(self, stream):
        """
        Stops all threads that are currently receiving and processing CDP data,
        using the IP, port, and equivalent local interface(s) specified in the
        StreamInformation object passed as an argument.
        """
        for listen_addr in stream.equivalent_addresses:
            if listen_addr in self.rx_threads:
                for thread in self.rx_threads[listen_addr]:
                   thread.wait()
                del self.rx_threads[listen_addr]
                self.set_address_to_inactive(listen_addr)
        if stream.interface == StreamInformation.any_interface:
            if stream in self.active_any_interface_streams:
                self.active_any_interface_streams.discard(stream)

    def set_address_to_inactive(self, listen_addr):
        if listen_addr in self.active_addresses:
            self.active_addresses.discard(listen_addr)
            print("Stopped listening on {}".format(listen_addr))

    def set_equivalent_checked(self, state, stream):
        for listen_addr in stream.equivalent_addresses:
            for stream_idx in self.available_addresses.get(listen_addr, []):
                self.stream_checkboxes[stream_idx].setChecked(state)
        for stream_idx in self.any_interface_streams.get(stream, []):
            self.stream_checkboxes[stream_idx].setChecked(state)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        new_cuwb_nets = set(self.network_discovery.available_networks.values())
        # Only refresh if the list of available networks changed
        if self.previous_cuwb_nets != new_cuwb_nets:
             self.previous_cuwb_nets = set(new_cuwb_nets)
             self.refresh_cuwb_networks_widget()

    def closeEvent(self, e):
        # The window is only closed when the main window is closed.
        # Otherwise, it is just hidden.
        if UwbNetwork.running:
            self.network_discovery.rx_thread.join()
            self.hide()
        else:
            # If network timers are not deleted first, the main window will close when they time out.
            self.network_discovery.rx_thread.join()
            self.network_discovery.network_timers = None
            self.killTimer(self.timer)
            self.close()

    def reopen(self):
        self.network_discovery.reopen()
