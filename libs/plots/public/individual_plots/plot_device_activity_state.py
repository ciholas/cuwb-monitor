# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

# Local libraries
from cdp import DeviceActivityState
from network_objects import *
from settings import *


class PlotDeviceActivityState(QtWidgets.QMainWindow):
    type = DeviceActivityState.type

    def __init__(self, serial):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QScrollArea()
        self.central.setWidgetResizable(True)
        self.central_inner_widget = QtWidgets.QWidget()
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Device Activity State Plotter ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtWidgets.QGridLayout()
        self.running = True

        self.sub_windows = dict([])

        self.id_total = 0
        self.from_id_id_labels = dict()
        self.from_id_count_labels = dict()
        self.from_id_freq_labels = dict()
        self.from_id_enable_checks = dict()
        self.from_id_times = dict()
        self.from_id_count = dict()
        self.from_ids = np.array([])
        self.from_id_frequency_deques = dict()
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[DeviceActivityState.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[DeviceActivityState.type])

        self.grid_layout.addWidget(QtWidgets.QLabel('Serial #'), 0, 0)
        self.grid_layout.addWidget(QtWidgets.QLabel('Packet Count'), 0, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel('Frequency'), 0, 2)
        self.grid_layout.addWidget(QtWidgets.QLabel('Print'), 0, 3)

        self.update_labels()
        #This allows for a dynamic window size where the number of serials already in the window after
        #one pass affects the size of the serial choice window.
        row_height = 20
        self.resize(400, row_height+(row_height * len(self.from_id_id_labels)))

        self.central_inner_widget.setLayout(self.grid_layout)
        self.central.setWidget(self.central_inner_widget)

        self.setCentralWidget(self.central)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        self.update_labels()

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)

    def update_labels(self):
        current_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
        current_size = current_count - self.previous_count
        if current_size > 1000:
            current_size = 1000
        self.previous_count = current_count
        for idx in range(current_size):
            target_id = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - current_size].serial_number.as_int
            if not (target_id in self.from_ids):
                self.from_id_id_labels.update([(self.id_total, QtWidgets.QLabel())])
                self.from_id_count_labels.update([(self.id_total, QtWidgets.QLabel())])
                self.from_id_freq_labels.update([(self.id_total, QtWidgets.QLabel())])
                self.from_id_enable_checks.update([(self.id_total, QtWidgets.QCheckBox())])
                self.from_id_times.update([(target_id, deque([], TRAIL_LENGTH))])
                self.from_id_frequency_deques.update([(target_id, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
                self.from_id_count.update([(target_id, 0)])
                self.from_ids = np.sort(np.append(self.from_ids, target_id))

                row = self.id_total
                column = 0
                self.grid_layout.addWidget(self.from_id_id_labels[self.id_total], row + 1, column + 0)
                self.grid_layout.addWidget(self.from_id_count_labels[self.id_total], row + 1, column + 1)
                self.grid_layout.addWidget(self.from_id_freq_labels[self.id_total], row + 1, column + 2)
                self.grid_layout.addWidget(self.from_id_enable_checks[self.id_total], row + 1, column + 3)

                if column > 0:
                    row = 2
                    self.grid_layout.addWidget(QtWidgets.QLabel("Serial #"), row, column + 0)
                    self.grid_layout.addWidget(QtWidgets.QLabel("Packet Count"), row, column + 1)
                    self.grid_layout.addWidget(QtWidgets.QLabel("Frequency"), row, column + 2)
                    self.grid_layout.addWidget(QtWidgets.QLabel("Print"), row, column + 3)
                self.id_total += 1

            self.from_id_times[target_id].append(UwbNetwork.nodes[self.serial].cdp_pkts_time[self.type][idx - current_size])
            self.from_id_count[target_id] += 1

            if target_id in self.from_ids:
                row = np.where(self.from_ids == target_id)[0][0]
                if self.from_id_enable_checks[row].isChecked():
                    print(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - current_size])

            if target_id in self.sub_windows.keys():
                packet = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - current_size]

                self.sub_windows[target_id].updateData(packet)

        for target_id in self.from_ids:
            self.from_id_frequency_deques[target_id].append((self.from_id_count[target_id], time.monotonic()))

        for row in range(self.id_total):
            target_id = int(self.from_ids[row])
            if self.from_id_id_labels[row].text() != '0x{:08X}'.format(target_id):
                self.from_id_id_labels[row].setText('0x{:08X}'.format(target_id))
                self.from_id_id_labels[row].setStyleSheet(GetClickableColor())
                self.from_id_id_labels[row].mouseReleaseEvent = partial(self.labelClickEvent, target_id)

            if len(self.from_id_times[target_id]) == 0:
                continue

            freq = UwbNetwork.nodes[self.serial].calculate_frequency(self.from_id_frequency_deques[target_id])
            self.from_id_count_labels[row].setText('{:5d}'.format(self.from_id_count[target_id]))
            self.from_id_freq_labels[row].setText('{:5.1f}Hz'.format(freq))

    def labelClickEvent(self, serial, e):
        self.sub_windows.update([(serial, PlotDeviceActivityStateSubWindow(serial, self))])

    def reset(self):
        for target_id in self.from_ids:
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)

class PlotDeviceActivityStateSubWindow(pg.GraphicsLayoutWidget):

    def __init__(self, serial, parent):
        pg.GraphicsLayoutWidget.__init__(self)
        self.show()
        self.setWindowTitle('CUWB Monitor - Device Activity State ID: 0x{:08X}'.format(serial))
        self.parent = parent
        self.serial = serial
        self.resize(600, 100)
        self.timer = self.startTimer(QPLOT_FREQUENCY)

        self.id_dict = {0: 'Unconfigured', 1: 'Low Power', 2: 'Quiet Anchor',
                        3: 'Seeder', 4: 'Default Tag', 5: 'Tag Role 5'}
        self.connectivity_dict = {0: 'No Connection', 1: 'UWB',
                                  2: 'Ethernet', 3: 'UWB and Ethernet'}
        self.sync_dict = {0: 'Not synchronized', 1: 'Transmit Synchronized',
                          2: 'Receive Synchronized',
                          3: 'Transmit and Receive Synchronized'}

        self.role_id_label = self.addLabel(text='', row=0, col=0)
        self.connectivity_state_label = self.addLabel(text='', row=1, col=0)
        self.sync_state_label = self.addLabel(text='', row=2, col=0)
        self.running = True

    def updateData(self, packet):

        id = packet.role_id
        connectivity_state = packet.connectivity_state
        sync_state = packet.synchronization_state

        id_string = 'This device is currently functioning as a: '
        try:
            id_string += self.id_dict[id]
        except KeyError:
            id_string += 'Error'
        connectivity_string = 'This device is currently connected via: '
        try:
            connectivity_string += self.connectivity_dict[connectivity_state]
        except KeyError:
            connectivity_string += 'Error'
        sync_string = 'This device is currently: '
        try:
            sync_string += self.sync_dict[sync_state]
        except KeyError:
            sync_string += 'Error'

        self.role_id_label.setText(id_string)
        self.connectivity_state_label.setText(connectivity_string)
        self.sync_state_label.setText(sync_string)

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False
