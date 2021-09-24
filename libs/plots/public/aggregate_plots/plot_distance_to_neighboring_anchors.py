# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

ROLE_QUIET_ANCHOR = 2
ROLE_SEEDER_ANCHOR = 3
TIME_RANGE = 30

# System libraries
import pyqtgraph as pg
from collections import deque
from functools import partial
from pyqtgraph.Qt import QtGui, QtCore
from random import randint

# Local libraries
from cdp import *
from network_objects import *
from settings import *

class PlotDistanceToNeighboringAnchors(QtGui.QMainWindow):
    type = 'DistanceToNeighboringAnchorsPlot'

    def __init__(self):

        QtGui.QMainWindow.__init__(self)

        self.central = QtGui.QScrollArea()
        self.central_inner_widget = QtGui.QWidget()
        self.setWindowTitle('CUWB Monitor - Distance to Neighboring Anchors')
        self.grid_layout = QtGui.QGridLayout()
        self.running = True

        self.sub_windows = dict([])

        self.id_total = 0
        self.from_id_id_labels = dict()
        self.from_id_count_labels = dict()
        self.from_id_freq_labels = dict()
        self.from_id_enable_checks = dict()
        self.from_id_count = dict()
        self.from_ids = np.array([])
        self.from_id_roles = dict()
        self.from_id_frequency_deques = dict()

        self.network_serials = dict()
        self.device_roles_count = dict()
        self.update_labels()

        self.grid_layout.addWidget(QtGui.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtGui.QLabel("Packet Count"), 0, 1)
        self.grid_layout.addWidget(QtGui.QLabel("Frequency"), 0, 2)
        self.grid_layout.addWidget(QtGui.QLabel("Print"), 0, 3)

        self.central_inner_widget.setLayout(self.grid_layout)
        self.central.setWidget(self.central_inner_widget)

        self.setCentralWidget(self.central)
        self.resize(500, 300)

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
        for serial in UwbNetwork.nodes:
            if ((serial not in self.network_serials) and DistanceV2.type in UwbNetwork.nodes[serial].cdp_pkts_count and DeviceActivityState.type in UwbNetwork.nodes[serial].cdp_pkts_count):
                self.network_serials[serial] = (UwbNetwork.nodes[serial].cdp_pkts_count[DistanceV2.type] -
                                                len(UwbNetwork.nodes[serial].cdp_pkts[DistanceV2.type]))
                self.device_roles_count[serial] = (UwbNetwork.nodes[serial].cdp_pkts_count[DeviceActivityState.type] -
                                                   len(UwbNetwork.nodes[serial].cdp_pkts[DeviceActivityState.type]))
        for serial in self.network_serials:
            previous_count = self.network_serials[serial]
            self.network_serials[serial] = UwbNetwork.nodes[serial].cdp_pkts_count[DistanceV2.type]
            current_size = self.network_serials[serial] - previous_count
            if current_size > 1000:
                current_size = 1000
            for idx in range(current_size):
                target_id = UwbNetwork.nodes[serial].cdp_pkts[DistanceV2.type][idx - current_size].serial_number_1.as_int
                if not target_id in self.from_ids:
                    self.from_id_id_labels.update([(self.id_total, QtGui.QLabel())])
                    self.from_id_count_labels.update([(self.id_total, QtGui.QLabel())])
                    self.from_id_freq_labels.update([(self.id_total, QtGui.QLabel())])
                    self.from_id_enable_checks.update([(self.id_total, QtGui.QCheckBox())])
                    self.from_id_count.update([(target_id, 0)])
                    self.from_id_frequency_deques.update([(target_id, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
                    self.from_ids = np.sort(np.append(self.from_ids, target_id))

                    row = self.id_total
                    column = 0
                    self.grid_layout.addWidget(self.from_id_id_labels[self.id_total], row + 1, column + 0)
                    self.grid_layout.addWidget(self.from_id_count_labels[self.id_total], row + 1, column + 1)
                    self.grid_layout.addWidget(self.from_id_freq_labels[self.id_total], row + 1, column + 2)
                    self.grid_layout.addWidget(self.from_id_enable_checks[self.id_total], row + 1, column + 3)

                    self.id_total += 1

                self.from_id_count[target_id] += 1

                if target_id in self.from_ids:
                    row = np.where(self.from_ids==target_id)[0][0]
                    if self.from_id_enable_checks[row].isChecked():
                        print(UwbNetwork.nodes[serial].cdp_pkts[DistanceV2.type][idx - current_size])

                if target_id in self.sub_windows:
                    packet = UwbNetwork.nodes[serial].cdp_pkts[DistanceV2.type][idx - current_size]
                    timestamp = UwbNetwork.nodes[serial].cdp_pkts_time[DistanceV2.type][idx - current_size]
                    self.sub_windows[target_id].update_data(packet, timestamp)

            previous_count = self.device_roles_count[serial]
            self.device_roles_count[serial] = UwbNetwork.nodes[serial].cdp_pkts_count[DeviceActivityState.type]
            current_size = self.device_roles_count[serial]
            for idx in range(current_size):
                target_id = UwbNetwork.nodes[serial].cdp_pkts[DeviceActivityState.type][idx - current_size].serial_number
                role = UwbNetwork.nodes[serial].cdp_pkts[DeviceActivityState.type][idx - current_size].role_id
                if role == ROLE_QUIET_ANCHOR or role == ROLE_SEEDER_ANCHOR:
                    self.from_id_roles[target_id] = True
                else:
                    self.from_id_roles[target_id] = False

        for target_id in self.from_ids:
            self.from_id_frequency_deques[target_id].append((self.from_id_count[target_id], time.time()))

        networks = list(self.network_serials.keys())
        for row in range(self.id_total):
            target_id = int(self.from_ids[row])
            if self.from_id_id_labels[row].text() != '0x{:08X}'.format(target_id):
                self.from_id_id_labels[row].setText('0x{:08X}'.format(target_id))
                self.from_id_id_labels[row].setStyleSheet('color:blue')
                self.from_id_id_labels[row].mouseReleaseEvent = partial(self.labelClickEvent, target_id)

            freq = UwbNetwork.nodes[networks[0]].calculate_frequency(self.from_id_frequency_deques[target_id])
            self.from_id_count_labels[row].setText('{:5d}'.format(self.from_id_count[target_id]))
            self.from_id_freq_labels[row].setText('{:5.1f}Hz'.format(freq))

    def labelClickEvent(self, serial, e):
        self.sub_windows.update([(serial, PlotDistanceToNeighboringAnchorsSubWindow(serial, self))])

    def reset(self):
        for target_id in self.from_ids:
            self.network_serials = dict()
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
        for target_id in self.sub_windows:
            self.sub_windows[target_id].reset()

class PlotDistanceToNeighboringAnchorsSubWindow(pg.LayoutWidget):

    def __init__(self, serial, parent):

        pg.LayoutWidget.__init__(self)
        self.show()
        self.setWindowTitle('CUWB Monitor - Distance to Anchors: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(800, 800)
        self.parent = parent
        self.recent_timestamp = 0

        self.devices = np.array([])
        self.device_anchor = dict()
        self.device_distances = dict()
        self.device_qualities = dict()
        self.device_timestamps = dict()
        self.device_distance_plots = dict()
        self.device_quality_plots = dict()
        self.device_colors = dict()

        self.colors = ['r', 'g', 'b', 'c', 'm', 'y', 's', (0, 51, 0), (127, 0, 255), (255, 127, 0), (0, 255, 127), (102, 0, 0), 'w', 'l']
        self.colors_used = []
        self.color_offset = 0

        self.graph_distance = pg.PlotWidget(name='Distance', title='Distance (m) vs Time (s)')
        self.graph_distance.showGrid(x=True, y=True)
        self.graph_distance.setLimits(maxXRange=TIME_RANGE)
        self.distance_legend = self.graph_distance.addLegend()
        self.addWidget(self.graph_distance, row=1, col=0, colspan=3)

        self.graph_quality = pg.PlotWidget(name='Quality', title='Quality vs Time (s)')
        self.graph_quality.showGrid(x=True, y=True)
        self.graph_quality.setLimits(maxXRange=TIME_RANGE)
        self.addWidget(self.graph_quality, row=2, col=0, colspan=3)

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

    def update_data(self, packet, timestamp):

        if packet.serial_number_1 == self.serial:
            serial = packet.serial_number_2
        else:
            serial = packet.serial_number_1
        if self.parent.from_id_roles[serial]:
            if serial not in self.devices:
                self.devices = np.append(self.devices, serial)
                self.device_distances.update([(serial, deque([], TRAIL_LENGTH))])
                self.device_qualities.update([(serial, deque([], TRAIL_LENGTH))])
                self.device_timestamps.update([(serial, deque([], TRAIL_LENGTH))])
                color = self.colors[self.color_offset % len(self.colors)]
                original_color_offset = self.color_offset
                while color in self.colors_used:
                    self.color_offset += 1
                    if self.color_offset > len(self.colors):
                        self.color_offset = 0
                    if self.color_offset == original_color_offset:
                        color = (randint(0, 255), randint(0, 255), randint(0, 255))
                        break
                    color = self.colors[self.color_offset % len(self.colors)]
                self.colors_used.append(color)
                self.device_colors.update([(serial, color)])
                self.device_distance_plots.update([(serial, self.graph_distance.plot(pen=pg.mkPen(color, width=2)))])
                self.device_quality_plots.update([(serial, self.graph_quality.plot(pen=pg.mkPen(color, width=2)))])
                if self.color_offset < len(self.colors):
                    self.color_offset += 1
                self.distance_legend.addItem(self.device_distance_plots[serial], '0x{:08X}'.format(serial.as_int))
            self.device_distances[serial].append(packet.distance / 1000.0)
            self.device_qualities[serial].append(packet.quality)
            self.device_timestamps[serial].append(timestamp)

            self.device_distance_plots[serial].setData(self.device_timestamps[serial], self.device_distances[serial])
            self.device_quality_plots[serial].setData(self.device_timestamps[serial], self.device_qualities[serial])

            if timestamp > self.recent_timestamp:
                self.recent_timestamp = timestamp

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()
            return

        for device in self.devices:
            if self.device_timestamps[device][-1] < (self.recent_timestamp - TIME_RANGE):
                self.device_distance_plots[device].clear()
                self.device_quality_plots[device].clear()
                del self.device_distances[device]
                del self.device_qualities[device]
                del self.device_timestamps[device]
                self.distance_legend.removeItem('0x{:08X}'.format(device.as_int))
                del self.device_distance_plots[device]
                del self.device_quality_plots[device]
                self.colors_used.remove(self.device_colors[device])
                del self.device_colors[device]
                self.devices = np.delete(self.devices, np.argwhere(self.devices==device))

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def reset(self):
        for device in self.devices:
            self.device_distance_plots[device].clear()
            self.device_quality_plots[device].clear()
        self.devices = np.array([])
        self.device_distances = dict()
        self.device_qualities = dict()
        self.device_timestamps = dict()
        self.device_distance_plots = dict()
        self.device_quality_plots = dict()
