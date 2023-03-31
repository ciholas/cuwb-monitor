# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from functools import partial

# Local libraries
from cdp import DeviceHardwareStatusV2
from network_objects import *
from settings import *
from generic_plots import *

class PlotDeviceHardwareStatusV2(QtWidgets.QMainWindow):
    type = DeviceHardwareStatusV2.type
    
    def __init__(self, serial):
        
        QtWidgets.QMainWindow.__init__(self)
        self.serial = serial

        self.central = QtWidgets.QScrollArea()
        self.central.setWidgetResizable(True)
        self.central_inner_widget = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        self.setWindowTitle("CUWB Monitor- Device Hardware Status V2")

        self.sub_windows ={}
        self.from_ids = np.array([])
        self.prev_count = 0
        self.id_total = 0
        self.from_id_id_labels = {}
        self.from_id_count_labels = {}
        self.from_id_freq_labels = {}
        self.from_id_enable_checks = {}
        self.from_id_count = {}
        self.from_id_frequency_deques = {}

        self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtWidgets.QLabel("Packet Count"), 0, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel("Frequency"), 0, 2)
        self.grid_layout.addWidget(QtWidgets.QLabel("Print"), 0, 3)

        self.running = True
        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.updateLabels()
        #This allows for a dynamic window size where the number of serials already in the window after
        #one pass affects the size of the serial choice window.
        row_height = 20
        self.resize(400, row_height+(row_height * len(self.from_id_id_labels)))

        self.central_inner_widget.setLayout(self.grid_layout)
        self.central.setWidget(self.central_inner_widget)
        self.setCentralWidget(self.central)

    def updateLabels(self):
        if self.type in UwbNetwork.nodes[self.serial].cdp_pkts_count:
            _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
            if _current_size - self.prev_count > 1000: self.prev_count = _current_size - 1000
            while self.prev_count < _current_size:
                idx = self.prev_count - _current_size
                _target_id = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx].serial_number.as_int
                if not (_target_id in self.from_ids):
                    self.from_id_id_labels.update([(self.id_total, QtWidgets.QLabel())])
                    self.from_id_count_labels.update([(self.id_total, QtWidgets.QLabel())])
                    self.from_id_freq_labels.update([(self.id_total, QtWidgets.QLabel())])
                    self.from_id_enable_checks.update([(self.id_total, QtWidgets.QCheckBox())])
                    self.from_id_count.update([(_target_id, 0)])
                    self.from_id_frequency_deques.update([(_target_id, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
                    self.from_ids = np.sort(np.append(self.from_ids, _target_id))

                    _row = self.id_total
                    _column = 0
                    self.grid_layout.addWidget(self.from_id_id_labels[self.id_total], _row + 1, _column + 0)
                    self.grid_layout.addWidget(self.from_id_count_labels[self.id_total], _row + 1, _column + 1)
                    self.grid_layout.addWidget(self.from_id_freq_labels[self.id_total], _row + 1, _column + 2)
                    self.grid_layout.addWidget(self.from_id_enable_checks[self.id_total], _row + 1, _column + 3)

                    if _column > 0:
                        _row = 2
                        self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), _row, _column + 0)
                        self.grid_layout.addWidget(QtWidgets.QLabel("Packet Count"), _row, _column + 1)
                        self.grid_layout.addWidget(QtWidgets.QLabel("Frequency"), _row, _column + 2)
                        self.grid_layout.addWidget(QtWidgets.QLabel("Print"), _row, _column + 3)
                    self.id_total += 1

                self.from_id_count[_target_id] += 1

                if _target_id in self.from_ids:
                    _row = np.where(self.from_ids==_target_id)[0][0]
                    if self.from_id_enable_checks[_row].isChecked():
                        print(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx])

                if _target_id in self.sub_windows.keys():
                    _packet = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx]
                    _time = UwbNetwork.nodes[self.serial].cdp_pkts_time[self.type][idx]
                    self.sub_windows[_target_id].updateLabels(_packet, _time)

                self.prev_count += 1

            for _target_id in self.from_ids:
                self.from_id_frequency_deques[_target_id].append((self.from_id_count[_target_id], time.monotonic()))

            for _row in range(self.id_total):
                _target_id = int(self.from_ids[_row])
                if self.from_id_id_labels[_row].text() != '0x{:08X}'.format(_target_id):
                    self.from_id_id_labels[_row].setText('0x{:08X}'.format(_target_id))
                    self.from_id_id_labels[_row].setStyleSheet(GetClickableColor())
                    self.from_id_id_labels[_row].mouseReleaseEvent = partial(self.labelClickEvent, _target_id)

                _freq = UwbNetwork.nodes[self.serial].calculate_frequency(self.from_id_frequency_deques[_target_id])
                self.from_id_count_labels[_row].setText('{:5d}'.format(self.from_id_count[_target_id]))
                self.from_id_freq_labels[_row].setText('{:5.1f}Hz'.format(_freq))

    def labelClickEvent(self, item_serial, e):
        self.sub_windows[item_serial] = PlotDeviceHardwareStatusV2SubWindow(item_serial, self)
        if UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] != 0:
            index = -1
            while -index < UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]:
                packet = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][index]
                if packet.serial_number.as_int == item_serial:
                    time = UwbNetwork.nodes[self.serial].cdp_pkts_time[self.type]
                    self.sub_windows[item_serial].updateLabels(packet, time)
                index -= 1
        self.sub_windows[item_serial].show()

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.running = False
            self.close()
            return
        if self.running:
            self.updateLabels()
        else:
            self.killTimer(self.timer)
            self.close()

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False
        for window in self.sub_windows.values():
            if window.isVisible():
                window.close()
        self.close()

    def reset(self):
        for window in self.sub_windows.values():
            window.reset()

class PlotDeviceHardwareStatusV2SubWindow(QtWidgets.QMainWindow):

    def __init__(self, device_serial, parent):
        
        QtWidgets.QMainWindow.__init__(self)
        self.device_serial = device_serial
        self.parent = parent

        self.central = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        
        self.setWindowTitle("CUWB Monitor- Device Hardware Status V2 ID: 0x{:08X}".format(self.device_serial))
        length = 350
        width = 200
        self.resize(length, width)
        self.sub_windows = {}
        
        self.createLayout()
        
        self.running = True
        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def createLayout(self):
        self.dhs_widgets = []
        self.dhs_label_array = []
        grid_rows = []
        first_row = 0
        total_rows = 4

        createRows(self.dhs_widgets, grid_rows, self.grid_layout, first_row, total_rows)

        curr_row = 0
        spacer_size = 20

        #Row Zero
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Free Memory: "), curr_row, 0)
        self.memory_label = self.makeBlankLabel('memory')
        self.dhs_label_array.append(self.memory_label)
        grid_rows[curr_row].addWidget(self.memory_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), curr_row, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Flags: "), curr_row, 3)
        self.flags_label = self.makeBlankLabel('flags')
        self.dhs_label_array.append(self.flags_label)
        grid_rows[curr_row].addWidget(self.flags_label, curr_row, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), curr_row, 5)
        curr_row += 1

        #Row One
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Minutes Remaining: "), curr_row, 0)
        self.minutes_label = self.makeBlankLabel('minutes_remaining')
        self.dhs_label_array.append(self.minutes_label)
        grid_rows[curr_row].addWidget(self.minutes_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), curr_row, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Battery Remaining: "), curr_row, 3)
        self.battery_label = self.makeBlankLabel('battery_percentage')
        self.dhs_label_array.append(self.battery_label)
        grid_rows[curr_row].addWidget(self.battery_label, curr_row, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), curr_row, 5)
        curr_row += 1

        #Row Two
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Temperature: "), curr_row, 0)
        self.temperature_label = self.makeBlankLabel('temperature')
        self.dhs_label_array.append(self.temperature_label)
        grid_rows[curr_row].addWidget(self.temperature_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), curr_row, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Processor Usage: "), curr_row, 3)
        self.processor_label = self.makeBlankLabel('processor_usage')
        self.dhs_label_array.append(self.processor_label)
        grid_rows[curr_row].addWidget(self.processor_label, curr_row, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size,0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), curr_row, 5)
        curr_row +=1

        #Row Three
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Error Patterns: "), curr_row, 0)
        self.error_flags_label = QtWidgets.QLabel("")
        grid_rows[curr_row].addWidget(self.error_flags_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

    def updateLabels(self, packet, time):
        self.memory_label.setText("{}".format(packet.memory))
        self.flags_label.setText("{}".format(packet.flags))
        self.minutes_label.setText("{}".format(packet.minutes_remaining))
        self.battery_label.setText("{}%".format(packet.battery_percentage))
        self.temperature_label.setText("{} C".format(packet.temperature))
        self.processor_label.setText("{}%".format(packet.processor_usage))
        error_patterns = ""
        for pattern in packet.error_patterns:
            error_patterns += str(pattern)
            error_patterns += ", "
        self.error_flags_label.setText(error_patterns)
        self.makeLabelsReclickable()

        for property_name in self.sub_windows.keys():
            if self.sub_windows[property_name].running:
                self.sub_windows[property_name].updateTime(packet, property_name, time)

    def makeBlankLabel(self, property_name):
        temp_label = QtWidgets.QLabel("")
        temp_label.setStyleSheet(GetClickableColor())
        temp_label.mouseReleaseEvent = partial(self.labelClickEvent, property_name)
        return temp_label

    def labelClickEvent(self, property_name, e):
        self.sub_windows[property_name] = PlotDeviceHardwareStatusV2GraphWindow(self.device_serial, self, property_name)
        self.sub_windows[property_name].show()

    def makeLabelsReclickable(self):
        for label in self.dhs_label_array:
            label.setStyleSheet(GetClickableColor())
            label.setEnabled(True)

    def makeLabelsUnclickable(self):
        for label in self.dhs_label_array:
            label.setText("?")
            label.setStyleSheet('color:black')
            label.setEnabled(False)

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.killTimer(self.timer)
            self.close()
            return

    def closeEvent(self, e):
        self.killTimer(self.timer)
        for window in self.sub_windows.values():
            if window.isVisible():
                window.close()
        self.close()

    def reset(self):
        self.makeLabelsUnclickable()
        for window in self.sub_windows:
            if self.sub_windows[window].running:
                sub_window_device_serial = self.sub_windows[window].device_serial
                sub_window_item_type = self.sub_windows[window].item_type
                self.sub_windows[window].close()
                self.sub_windows[window] = PlotDeviceHardwareStatusV2GraphWindow(sub_window_device_serial, self, sub_window_item_type)
                self.sub_windows[window].show()

class PlotDeviceHardwareStatusV2GraphWindow(pg.GraphicsLayoutWidget):
#This class should be generic enough to where it can be reused as a plotter for any data type that comes in through the netapp
#serial number.  See the updateLabel methods for how data is sent to it.
    def __init__(self, device_serial, parent, item_type):
        self.device_serial = device_serial
        self.parent = parent
        self.item_type = item_type

        pg.GraphicsLayoutWidget.__init__(self)
        length = 900
        width = 500
        self.resize(length, width)

        self.setWindowTitle("CUWB Monitor- {} Plot ID: 0x{:08X}".format(self.item_type, self.device_serial))
        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

        self.graph = self.addPlot(title='')
        self.graph.showGrid(x=True, y=True)
        self.plot= self.graph.plot(pen='b', name=self.item_type)

        self.data = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)

    def updateTime(self, packet, item_type, time):
        self.data.append(getattr(packet, item_type))
        self.time.append(time)

        if len(self.time) > 1:
            _data = np.array(self.data)
            _times = np.array(self.time)

            self.plot.setData(_times, _data)

    def timerEvent(self, e):
        if not self.running or not self.parent.running:
            self.killTimer(self.timer)
            self.close()
            return

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)
        self.close()
