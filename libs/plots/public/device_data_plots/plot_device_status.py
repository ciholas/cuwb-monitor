# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

#System Libraries
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtWidgets, QtCore
from functools import partial

#Local Libraries
from device_data_items import DeviceStatus
from network_objects import *
from generic_plots import *
from settings import *

class PlotDeviceStatus(QtWidgets.QMainWindow):
    type = DeviceStatus.type

    def __init__(self, device):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()
        self.setWindowTitle("CUWB Monitor- Device Status Device: 0x{:08X}".format(device.id))
        self.device = device
        self.running = True

        self.grid_main = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_main)
        self.setCentralWidget(self.central)
        
        length =350
        width = 200
        self.resize(length, width)

        self.sub_windows = {}
        self.createLayout()
        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def createLayout(self):
        self.ds_widgets = []
        self.ds_label_array = []
        grid_rows = []
        first_row = 0
        total_rows = 4

        createRows(self.ds_widgets, grid_rows, self.grid_main, first_row, total_rows)

        curr_row = 0
        spacer_size = 20

        #Row Zero
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Free Memory: "), curr_row, 0)
        self.memory_label = self.makeBlankLabel('memory')
        self.ds_label_array.append(self.memory_label)
        grid_rows[curr_row].addWidget(self.memory_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), curr_row, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Flags: "), curr_row, 3)
        self.flags_label = self.makeBlankLabel('flags')
        self.ds_label_array.append(self.flags_label)
        grid_rows[curr_row].addWidget(self.flags_label, curr_row, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), curr_row, 5)
        curr_row += 1

        #Row One
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Minutes Remaining: "), curr_row, 0)
        self.minutes_label = self.makeBlankLabel('minutes_remaining')
        self.ds_label_array.append(self.minutes_label)
        grid_rows[curr_row].addWidget(self.minutes_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), curr_row, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Battery Remaining: "), curr_row, 3)
        self.battery_label = self.makeBlankLabel('battery_percentage')
        self.ds_label_array.append(self.battery_label)
        grid_rows[curr_row].addWidget(self.battery_label, curr_row, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), curr_row, 5)
        curr_row += 1

        #Row Two
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Temperature: "), curr_row, 0)
        self.temperature_label = self.makeBlankLabel('temperature')
        self.ds_label_array.append(self.temperature_label)
        grid_rows[curr_row].addWidget(self.temperature_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), curr_row, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Processor Usage: "), curr_row, 3)
        self.processor_label = self.makeBlankLabel('processor_usage')
        self.ds_label_array.append(self.processor_label)
        grid_rows[curr_row].addWidget(self.processor_label, curr_row, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size,0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), curr_row, 5)
        curr_row +=1

        #Row Three
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Error Patterns: "), curr_row, 0)
        self.error_flags_label = QtWidgets.QLabel("")
        grid_rows[curr_row].addWidget(self.error_flags_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

        self.updateLabels()

    def updateLabels(self):
        if DeviceStatus.type in self.device.names.keys() and self.device.counts[DeviceStatus.type] != 0:
            packet = self.device.packets[DeviceStatus.type][-1]
            
            self.memory_label.setText("{}".format(packet.memory))
            self.flags_label.setText("{}".format(packet.flags))
            self.minutes_label.setText("{}".format(packet.minutes_remaining))
            self.battery_label.setText("{}%".format(packet.battery_percentage))
            self.temperature_label.setText("{} C".format(packet.temperature))
            self.processor_label.setText("{}%".format(packet.processor_usage))
            error_patterns = ""
            for pattern in packet.error_led:
                error_patterns += str(pattern)
                error_patterns += ", "
            self.error_flags_label.setText(error_patterns)
            self.makeLabelsReclickable()
        else:
            self.makeLabelsUnclickable()

    def makeBlankLabel(self, property_name):
        temp_label = QtWidgets.QLabel("")
        temp_label.setStyleSheet(GetClickableColor())
        temp_label.mouseReleaseEvent = partial(self.labelClickEvent, property_name)
        return temp_label

    def labelClickEvent(self, property_name, e):
        self.sub_windows[property_name] = PlotDeviceStatusGraphWindow(self.device, property_name)
        self.sub_windows[property_name].show()

    def makeLabelsReclickable(self):
        for label in self.ds_label_array:
            label.setStyleSheet(GetClickableColor())
            label.setEnabled(True)

    def makeLabelsUnclickable(self):
        for label in self.ds_label_array:
            label.setText("?")
            label.setStyleSheet('color:black')
            label.setEnabled(False)

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
        self.killTimer(self.timer)
        for window in self.sub_windows.values():
            if window.isVisible():
                window.close()
        self.close()

    def reset(self):
        for window in self.sub_windows:
            if self.sub_windows[window].running:
                sub_window_device = self.sub_windows[window].device
                sub_window_item_type = self.sub_windows[window].item_type
                self.sub_windows[window].close()
                self.sub_windows[window] = PlotDeviceStatusGraphWindow(sub_window_device, sub_window_item_type)
                self.sub_windows[window].show()

class PlotDeviceStatusGraphWindow(pg.GraphicsLayoutWidget):

    def __init__(self, device, property_name):
        pg.GraphicsLayoutWidget.__init__(self)
        self.device = device
        self.item_type = property_name

        length = 900
        width = 500
        self.resize(length, width)

        self.setWindowTitle("CUWB Monitor- {} Plot Device Status: 0x{:08X}".format(self.item_type, self.device.id))
        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

        self.graph = self.addPlot(title='')
        self.graph.showGrid(x=True, y=True)
        self.plot= self.graph.plot(pen='b', name=self.item_type)

        self.last_count = self.device.counts[DeviceStatus.type]
        self.data = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)
        _current_size = len(self.device.packets[DeviceStatus.type])
        
        self.updateTime(_current_size)

    def updateTime(self, _current_size):
        if _current_size > TRAIL_LENGTH: _current_size = TRAIL_LENGTH
        for idx in range(_current_size):
            packet = self.device.packets[DeviceStatus.type][idx - _current_size]
            self.data.append(getattr(packet, self.item_type))
            self.time.append(self.device.counts[DeviceStatus.type])

    def timerEvent(self, e):
        if not self.running:
            self.killTimer(self.timer)
            self.close()
            return

        _current_size = self.device.counts[DeviceStatus.type] - self.last_count
        self.last_count = self.device.counts[DeviceStatus.type]
        if _current_size == 0: return

        self.updateTime(_current_size)

        if len(self.time) > 1:
            _data = np.array(self.data)
            _times = np.array(self.time)

            self.plot.setData(_times, _data)

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)
        self.close()
