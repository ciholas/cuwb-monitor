# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import struct
import time

#Local Libraries
import device_data_items
from cdp import *
from network_objects import *
from settings import *
from plots import *

class PlotDeviceData(QtWidgets.QMainWindow):
    type = DeviceData.type
    
    def __init__(self, serial):
        
        QtWidgets.QMainWindow.__init__(self)
        
        self.central = QtWidgets.QWidget()
        self.setWindowTitle('CUWB Monitor - DeviceData ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        
        self.window_length = 200
        self.window_width = 30
        self.resize(self.window_length, self.window_width)
        self.grid_layout.addWidget(QtWidgets.QLabel("Devices:"), 0, 0)
        count_label = QtWidgets.QLabel("Counts:")
        count_label.setAlignment(QtCore.Qt.AlignCenter)
        self.grid_layout.addWidget(count_label, 0, 1)
        
        self.serial = serial
        self.running = True
        self.device_network = DeviceNetwork(self.serial)
        self.device_labels = []
        self.device_counts = {}
        self.sub_windows = {}
        self.curr_row = 1
        self.prev_node_count = 0
        
        self.updateDevices()
        self.timer = self.startTimer(250)

    def updateDevices(self):
        if DeviceData.type in UwbNetwork.nodes[self.serial].cdp_pkts_count and UwbNetwork.nodes[self.serial].cdp_pkts_count[DeviceData.type] != 0:
            while self.prev_node_count != UwbNetwork.nodes[self.serial].cdp_pkts_count[DeviceData.type]:
                packet = UwbNetwork.nodes[self.serial].cdp_pkts[DeviceData.type][self.prev_node_count]
                typing, device_id, sequence_num, tlv_header = struct.unpack("<BIBH", packet.device_data[:8])
                packet_type_length = format(tlv_header, "#018b")
                packet_type = int(packet_type_length[2:12], 2)
                packet_length = int(packet_type_length[12:], 2)
                packet_data = packet.device_data[8:]
                if not CiholasSerialNumber(device_id).as_int in self.device_network.devices.keys():
                    self.device_network.devices[device_id] = Device(device_id, self.prev_node_count)
                    device_text = str(hex(device_id)).upper()
                    device_text = device_text[2:]
                    device_label = QtWidgets.QLabel('0x' + device_text)
                    device_label.setStyleSheet(GetClickableColor())
                    device_label.mouseReleaseEvent = partial(self.labelClickEvent, self.device_network, device_id)
                    self.device_labels.append(device_label)
                    self.grid_layout.addWidget(device_label, self.curr_row, 0)
                    device_count = QtWidgets.QLabel()
                    device_count.setAlignment(QtCore.Qt.AlignCenter)
                    self.device_counts[device_id] = device_count
                    self.grid_layout.addWidget(self.device_counts[device_id], self.curr_row, 1)
                    self.curr_row += 1
                    self.resize(self.window_length, self.window_width + 20*len(self.device_network.devices))

                if packet_type not in self.device_network.devices[device_id].names:
                    self.device_network.devices[device_id].addType(packet_type)
                self.device_network.devices[device_id].updateData(packet_type, packet_data, packet_length)
                self.device_counts[device_id].setText(str(self.device_network.devices[device_id].total_count))
                self.prev_node_count += 1

    def labelClickEvent(self, network, device_id, e):
        if device_id in self.sub_windows.keys():
            if self.sub_windows[device_id].isVisible():
                self.sub_windows[device_id].close()
            del self.sub_windows[device_id]

        self.sub_windows[device_id] = PlotDeviceDataSubwindow(network, device_id)
        self.sub_windows[device_id].show()

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        if self.running:
            self.updateDevices()
        else:
            self.killTimer(self.timer)
            self.close()

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)
        for window in self.sub_windows.values():
            if window.isVisible():
                window.close()
        self.close()

    def reset(self):
        self.prev_node_count = 0
        self.device_network.clear()
        for device_id, label in self.device_counts.items():
            label.setText("0")
        for window in self.sub_windows.values():
            window.reset()

class PlotDeviceDataSubwindow(QtWidgets.QMainWindow):
    
    def __init__(self, network, device_id):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()
        self.setWindowTitle('CUWB Monitor - DeviceData ID: 0x{:08X}'.format(device_id))
        self.grid_layout = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)

        self.window_length = 400
        self.window_width = 30
        self.resize(self.window_length, self.window_width)
        
        type_title = QtWidgets.QLabel('Type')
        type_title.setMargin(5)
        type_title.setAlignment(QtCore.Qt.AlignRight)
        count_title = QtWidgets.QLabel('Count')
        count_title.setMargin(5)
        frequency_title = QtWidgets.QLabel('Frequency')
        frequency_title.setMargin(5)
        print_title = QtWidgets.QLabel('Print')
        print_title.setMargin(5)
        self.grid_layout.addWidget(type_title, 0, 0)
        self.grid_layout.addWidget(count_title, 0, 1)
        self.grid_layout.addWidget(frequency_title, 0, 2)
        self.grid_layout.addWidget(print_title, 0, 3)

        self.device_network = network
        self.device = self.device_network.devices[device_id]
        self.sub_windows = {}
        self.row_count = 1
        self.type_labels = {}
        self.count_labels = {}
        self.freq_labels = {}
        self.print_boxes = {}
        self.prev_count = {}

        self.running = True
        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.updateLabels()

    def updateLabels(self):
        for dd_type in self.device.names.keys():
            self.device.updateFrequencies(dd_type, self.device_network.isPaused())
            if not dd_type in self.type_labels.keys():
                self.type_labels[dd_type] = QtWidgets.QLabel(self.device.names[dd_type])
                self.count_labels[dd_type] = QtWidgets.QLabel(str(self.device.counts[dd_type]))
                self.count_labels[dd_type].setAlignment(QtCore.Qt.AlignCenter)
                self.freq_labels[dd_type] = QtWidgets.QLabel("{:0.3f} Hz".format(self.device.frequencies[dd_type]))
                self.freq_labels[dd_type].setAlignment(QtCore.Qt.AlignCenter)
                self.print_boxes[dd_type] = QtWidgets.QCheckBox()

                self.grid_layout.addWidget(self.type_labels[dd_type], self.row_count, 0)
                self.grid_layout.addWidget(self.count_labels[dd_type], self.row_count, 1)
                self.grid_layout.addWidget(self.freq_labels[dd_type], self.row_count, 2)
                self.grid_layout.addWidget(self.print_boxes[dd_type], self.row_count, 3)

                self.count_labels[dd_type].setStyleSheet(GetClickableColor())
                self.count_labels[dd_type].mouseReleaseEvent = partial(self.countClickEvent, dd_type)
                self.prev_count[dd_type] = self.device.counts[dd_type]
                self.row_count += 1
            else:
                self.count_labels[dd_type].setText(str(self.device.counts[dd_type]))
                self.freq_labels[dd_type].setText("{:0.3f} Hz".format(self.device.frequencies[dd_type]))

            if self.print_boxes[dd_type].isChecked():
                while self.prev_count[dd_type] < self.device.counts[dd_type]:
                    index = self.prev_count[dd_type] - self.device.counts[dd_type]
                    print(self.device.packets[dd_type][index])
                    self.prev_count[dd_type] += 1

            if dd_type in dd_type_to_plot.keys():
                self.type_labels[dd_type].setStyleSheet(GetClickableColor())
                self.type_labels[dd_type].mouseReleaseEvent = partial(self.typeClickEvent, dd_type)

    def typeClickEvent(self, dd_type, e):
        temp_plot = partial(dd_type_to_plot[dd_type], self.device)
        if dd_type in self.sub_windows.keys():
            if self.sub_windows[dd_type].isVisible():
                self.sub_windows[dd_type].close()
            del self.sub_windows[dd_type]
        self.sub_windows[dd_type] = temp_plot()
        self.sub_windows[dd_type].show()
        

    def countClickEvent(self, dd_type, e):
        count = self.device.counts[dd_type]
        if count > 1000: count = 1000
        for index in range(-count, 0):
            print("RX Time: {:f}".format(self.device.times[dd_type][index]))
            print(self.device.packets[dd_type][index])
        

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        if self.running:
            self.updateLabels()
        else:
            self.killTimer(self.timer)
            self.close()

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)
        for window in self.sub_windows.values():
            if window.isVisible():
                window.close()
        self.close()

    def reset(self):
        self.prev_node_count = 0

        for window in self.sub_windows.values():
            window.reset()

class DeviceNetwork():

    def __init__(self, anchor):
        self.devices = {}
        self.init_time = time.monotonic()
        self.pinging_anchor = anchor

    def isPaused(self):
        return UwbNetwork.nodes[self.pinging_anchor].paused

    def clear(self):
        for device_id, device in self.devices.items():
            device.clear()

class Device():

    def __init__(self, device_id, init_count):
        self.id = device_id
        self.total_count = 0
        self.start_count = 0
        self.names = {}
        self.packets = {}
        self.times = {}
        self.counts = {}
        self.frequencies = {}
        self.frequency_deques = {}
        self.packet_lengths = {}

    def addType(self, ddi_type):
        device_data_types_names = {1: "VersionStringResponse",
                                   3: "MagnetometerCalibrationResponse",
                                   4: "DeviceStatus",
                                   6: "GyroscopeCalibrationResponse",
                                   7: "PersistentPropertyGetTypesResponse",
                                   8: "PersistentPropertyGetPropertyResponse",
                                   9: "BootloaderStatus"}
        if ddi_type in device_data_types_names.keys():
            self.names[ddi_type] = device_data_types_names[ddi_type]
        else:
            self.names[ddi_type] = "Unknown Type"
        self.packets[ddi_type] = deque([], TRAIL_LENGTH)
        self.packet_lengths[ddi_type] = deque([], TRAIL_LENGTH)
        self.times[ddi_type] = deque([], TRAIL_LENGTH)
        self.counts[ddi_type] = 0
        self.frequencies[ddi_type] = 0
        self.frequency_deques[ddi_type] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
    
    def updateData(self, ddi_type, data, data_length):
        device_data_types = {1: device_data_items.VersionStringResponse,
                             3: device_data_items.MagnetometerCalibrationResponse,
                             4: device_data_items.DeviceStatus,
                             6: device_data_items.GyroscopeCalibrationResponse,
                             7: device_data_items.PersistentPropertyGetTypesResponse,
                             8: device_data_items.PersistentPropertyGetPropertyResponse,
                             9: device_data_items.BootloaderStatus}
        device_ddi = device_data_types[ddi_type](self.id, data)
        self.packets[ddi_type].append(device_ddi)
        self.packet_lengths[ddi_type].append(data_length)
        self.times[ddi_type].append(time.monotonic()-UwbNetwork.time_initial)
        self.counts[ddi_type] += 1
        self.total_count += 1

    def updateFrequencies(self, ddi_type, paused):
        self.frequency_deques[ddi_type].append([self.counts[ddi_type], time.monotonic()])
        if paused or len(self.frequency_deques[ddi_type]) < 2:
            self.frequencies[ddi_type] = 0
        else:
            self.frequencies[ddi_type] = (self.frequency_deques[ddi_type][-1][0] - self.frequency_deques[ddi_type][0][0]) / (self.frequency_deques[ddi_type][-1][1] - self.frequency_deques[ddi_type][0][1])

    def clear(self):
        for ddi_type in self.names.keys():
            self.packets[ddi_type] = deque([], TRAIL_LENGTH)
            self.packet_lengths[ddi_type] = deque([], TRAIL_LENGTH)
            self.times[ddi_type] = deque([], TRAIL_LENGTH)
            self.counts[ddi_type] = 0
            self.frequencies[ddi_type] = 0
            self.frequency_deques[ddi_type] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
            self.total_count = 0
