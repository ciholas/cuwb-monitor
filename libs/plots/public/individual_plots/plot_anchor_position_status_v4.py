# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

TIME_RANGE = 5
ANCHOR_STATUS__GOOD_ANCHOR = 0
ANCHOR_STATUS__FILL_ANCHOR = 7

# System libraries
from functools import partial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
import time

# Local libraries
from cdp import AnchorPositionStatusV4
from network_objects import *
from settings import *

class PlotAnchorPositionStatusV4(QtGui.QMainWindow):
    type = AnchorPositionStatusV4.type

    def __init__(self, serial):

        QtGui.QMainWindow.__init__(self)

        self.central = QtGui.QScrollArea()
        self.central_inner_widget = QtGui.QWidget()
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Anchor Position Status V4 Plotter ID: 0x{:08X}'.format(serial))
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
        self.from_id_frequency_deques = dict()
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[AnchorPositionStatusV4.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[AnchorPositionStatusV4.type])

        self.grid_layout.addWidget(QtGui.QLabel("Tag Serial#"), 0, 0)
        self.grid_layout.addWidget(QtGui.QLabel("Packet Count"), 0, 1)
        self.grid_layout.addWidget(QtGui.QLabel("Frequency"), 0, 2)
        self.grid_layout.addWidget(QtGui.QLabel("Print"), 0, 3)

        self.update_labels()

        self.central_inner_widget.setLayout(self.grid_layout)
        self.central.setWidget(self.central_inner_widget)

        self.setCentralWidget(self.central)
        self.resize(400, 400)

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
        current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[AnchorPositionStatusV4.type] - self.previous_count
        if current_size > 1000:
            current_size = 1000
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[AnchorPositionStatusV4.type]
        for idx in range(current_size):
            target_id = UwbNetwork.nodes[self.serial].cdp_pkts[AnchorPositionStatusV4.type][idx - current_size].tag_serial_number.as_int
            if not (target_id in self.from_ids):
                self.from_id_id_labels.update([(self.id_total, QtGui.QLabel())])
                self.from_id_count_labels.update([(self.id_total, QtGui.QLabel())])
                self.from_id_freq_labels.update([(self.id_total, QtGui.QLabel())])
                self.from_id_enable_checks.update([(self.id_total, QtGui.QCheckBox())])
                self.from_id_count.update([(target_id, 0)])
                self.from_id_frequency_deques.update([(target_id, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
                self.from_ids = np.sort(np.append(self.from_ids, target_id))

                row = self.id_total
                column = 0

                row = self.id_total
                column = 0
                self.grid_layout.addWidget(self.from_id_id_labels[self.id_total], row + 1, column + 0)
                self.grid_layout.addWidget(self.from_id_count_labels[self.id_total], row + 1, column + 1)
                self.grid_layout.addWidget(self.from_id_freq_labels[self.id_total], row + 1, column + 2)
                self.grid_layout.addWidget(self.from_id_enable_checks[self.id_total], row + 1, column + 3)

                if column > 0:
                    row = 2
                    self.grid_layout.addWidget(QtGui.QLabel("Serial#"), row, column + 0)
                    self.grid_layout.addWidget(QtGui.QLabel("Packet Count"), row, column + 1)
                    self.grid_layout.addWidget(QtGui.QLabel("Frequency"), row, column + 2)
                    self.grid_layout.addWidget(QtGui.QLabel("Print"), row, column + 3)
                self.id_total += 1

            self.from_id_count[target_id] += 1

            if target_id in self.from_ids:
                row = np.where(self.from_ids==target_id)[0][0]
                if self.from_id_enable_checks[row].isChecked():
                    print(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - current_size])

            if target_id in self.sub_windows:
                packet = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - current_size]
                self.sub_windows[target_id].update_data(packet)

        for target_id in self.from_ids:
            self.from_id_frequency_deques[target_id].append((self.from_id_count[target_id], time.time()))

        for row in range(self.id_total):
            target_id = int(self.from_ids[row])
            if self.from_id_id_labels[row].text() != '0x{:08X}'.format(target_id):
                self.from_id_id_labels[row].setText('0x{:08X}'.format(target_id))
                self.from_id_id_labels[row].setStyleSheet('color:blue')
                self.from_id_id_labels[row].mouseReleaseEvent = partial(self.labelClickEvent, target_id)

            freq = UwbNetwork.nodes[self.serial].calculate_frequency(self.from_id_frequency_deques[target_id])
            self.from_id_count_labels[row].setText('{:5d}'.format(self.from_id_count[target_id]))
            self.from_id_freq_labels[row].setText('{:5.1f}Hz'.format(freq))

    def labelClickEvent(self, serial, e):
        self.sub_windows.update([(serial, PlotAnchorPositionStatusV4SubWindow(serial, self))])

    def reset(self):
        for target_id in self.from_ids:
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
        for target_id in self.sub_windows:
            self.sub_windows[target_id].reset()


class PlotAnchorPositionStatusV4SubWindow(pg.GraphicsWindow):

    def __init__(self, serial, parent):

        pg.GraphicsWindow.__init__(self)
        self.setWindowTitle('CUWB Monitor - Anchor Position Status V4 ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(1200, 400)
        self.parent = parent
        self.running = True
        self.start_time = time.time()
        self.sub_windows = dict([])

        self.graph = self.addPlot(title='')
        self.graph.setLimits(maxXRange=TIME_RANGE)
        self.graph.showGrid(x=True, y=True)
        self.legend = self.graph.addLegend()
        self.num_good_plot = self.graph.plot(pen='g', name='Number of Good Anchors', symbol='o', symbolPen='g', symbolBrush=(0,0,255))
        self.num_good_plot.sigPointsClicked.connect(self.point_clicked)
        self.num_fill_plot = self.graph.plot(pen='b', name='Number of Fill Anchors', symbol='o', symbolPen='b', symbolBrush=(255,0,0))
        self.num_fill_plot.sigPointsClicked.connect(self.point_clicked)
        self.num_bad_plot = self.graph.plot(pen='r', name='Number of Bad Anchors', symbol='o', symbolPen='r', symbolBrush=(0,255,0))
        self.num_bad_plot.sigPointsClicked.connect(self.point_clicked)
        self.packets = dict()

        self.timer = self.startTimer(QPLOT_FREQUENCY)

        self.num_good_anchors = deque([], TRAIL_LENGTH)
        self.num_bad_anchors = deque([], TRAIL_LENGTH)
        self.num_fill_anchors = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()

    def update_data(self, packet):

        num_good_anchors = 0
        num_bad_anchors = 0
        num_fill_anchors = 0

        for anchor in packet.anchor_status_array:
            if anchor.status == ANCHOR_STATUS__GOOD_ANCHOR:
                num_good_anchors += 1
            elif anchor.status == ANCHOR_STATUS__FILL_ANCHOR:
                num_fill_anchors += 1
            else:
                num_bad_anchors += 1

        self.num_good_anchors.append(num_good_anchors)
        self.num_bad_anchors.append(num_bad_anchors)
        self.num_fill_anchors.append(num_fill_anchors)
        self.time.append(time.time() - self.start_time)

        self.num_good_plot.setData(np.array(self.time), np.array(self.num_good_anchors))
        self.num_bad_plot.setData(np.array(self.time), np.array(self.num_bad_anchors))
        self.num_fill_plot.setData(np.array(self.time), np.array(self.num_fill_anchors))
        self.packets[self.time[-1]] = packet

    def point_clicked(self, item, points):
        for point in points:
            time = point._data[0]
            if (time not in self.sub_windows) or (not self.sub_windows[time].running):
                self.sub_windows.update([(time, SpecificPacketSubWindow(self.serial, self, self.packets[time]))])

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)

    def reset(self):
        self.num_good_anchors = deque([], TRAIL_LENGTH)
        self.num_bad_anchors = deque([], TRAIL_LENGTH)
        self.num_fill_anchors = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)
        for sub_window in self.sub_windows:
            self.sub_windows[sub_window].reset()
        self.sub_windows = dict()


class SpecificPacketSubWindow(QtGui.QMainWindow):

    def __init__(self, serial, parent, packet):
        QtGui.QMainWindow.__init__(self)
        self.show()
        self.central = QtGui.QScrollArea()
        self.central_inner_widget = QtGui.QWidget()
        self.setWindowTitle('CUWB Monitor - Anchor Position Status V4 ID: 0x{:08X}'.format(serial))
        self.resize(600, 100)
        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.serial = serial
        self.parent = parent
        self.running = True

        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.addWidget(QtGui.QLabel('Anchor Serial #    '), 0, 0)
        self.grid_layout.addWidget(QtGui.QLabel('Interface    '), 0, 1)
        self.grid_layout.addWidget(QtGui.QLabel('Status    '), 0, 2)
        self.grid_layout.addWidget(QtGui.QLabel('Quality'), 0, 3)

        row = 1
        for anchor in packet.anchor_status_array:
            self.grid_layout.addWidget(QtGui.QLabel('0x{:08X}'.format(anchor.anchor_serial_number.as_int)), row, 0)
            self.grid_layout.addWidget(QtGui.QLabel(str(anchor.anchor_interface_identifier)), row, 1)
            self.grid_layout.addWidget(QtGui.QLabel(str(anchor.status)), row, 2)
            self.grid_layout.addWidget(QtGui.QLabel(str(anchor.quality)), row, 3)
            row += 1

        self.central_inner_widget.setLayout(self.grid_layout)
        self.central.setWidget(self.central_inner_widget)

        self.setCentralWidget(self.central)

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)

    def reset(self):
        self.close()
