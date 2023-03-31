# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from PyQt5.QtWidgets import QCheckBox
from collections import deque
import time

# Local libraries
from cdp import PositionV3
from network_objects import *
from settings import *


class PlotPositionReportV3(QtWidgets.QMainWindow):
    type = PositionV3.type

    def __init__(self, serial):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QScrollArea()
        self.central.setWidgetResizable(True)
        self.central_inner_widget = QtWidgets.QWidget()
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Position V3 Plotter ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtWidgets.QGridLayout()
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
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[PositionV3.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[PositionV3.type])

        self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtWidgets.QLabel("Packet Count"), 0, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel("Frequency"), 0, 2)
        self.grid_layout.addWidget(QtWidgets.QLabel("Print"), 0, 3)

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
        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[PositionV3.type] - self.previous_count
        if _current_size > 1000: _current_size = 1000
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[PositionV3.type]
        for idx in range(_current_size):
            _target_id = UwbNetwork.nodes[self.serial].cdp_pkts[PositionV3.type][idx - _current_size].serial_number.as_int
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
                    print(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size])

            if _target_id in self.sub_windows.keys():
                _packet = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size]
                self.sub_windows[_target_id].update_data(_packet)

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

    def labelClickEvent(self, serial, e):
        self.sub_windows.update([(serial, PlotPositionV3SubWindow(serial, self))])

    def reset(self):
        for target_id in self.from_ids:
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
        for target_id in self.sub_windows:
            self.sub_windows[target_id].reset()


class PlotPositionV3SubWindow(pg.LayoutWidget):

    def __init__(self, serial, parent):

        pg.LayoutWidget.__init__(self)
        self.show()
        self.setWindowTitle('CUWB Monitor - Position V3 ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(800, 800)
        self.parent = parent

        self.data_x = deque([], TRAIL_LENGTH)
        self.data_y = deque([], TRAIL_LENGTH)
        self.data_z = deque([], TRAIL_LENGTH)

        self.graph_xy = pg.PlotWidget(name='XY', title='XY')
        self.graph_xy.showGrid(x=True, y=True)
        self.plot_xy = self.graph_xy.plot(pen=pg.mkPen('b', width=2))
        self.plot_xy_pt = self.graph_xy.plot(pen=pg.mkPen('c', width=1), symbol='o', symbolPen='c', symbolSize=8, symbolBrush='c')

        self.graph_xz = pg.PlotWidget(name='XZ', title='XZ')
        self.graph_xz.showGrid(x=True, y=True)
        self.graph_xz.setXLink('XY')
        self.plot_xz = self.graph_xz.plot(pen=pg.mkPen('b', width=2))
        self.plot_xz_pt = self.graph_xz.plot(pen=pg.mkPen('c', width=1), symbol='o', symbolPen='c', symbolSize=8, symbolBrush='c')

        self.stats_xyz_avg = QtWidgets.QLabel("")
        self.stats_xyz_std = QtWidgets.QLabel("")
        self.stats_quality = QtWidgets.QLabel("")

        self.scatter_checkbox = QCheckBox("Scatterplot")
        self.scatter_checkbox.stateChanged.connect(self.changeGraph)

        self.addWidget(self.graph_xy, row=0, col=0, colspan=3)
        self.addWidget(self.graph_xz, row=1, col=0, colspan=3)
        self.addWidget(self.stats_xyz_avg, row=2, col=0)
        self.addWidget(self.stats_xyz_std, row=2, col=1)
        self.addWidget(self.stats_quality, row=2, col=2)
        self.addWidget(self.scatter_checkbox, row=3, col=0)

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

    def update_data(self, packet):

        self.data_x.append(packet.x / 1000.0)
        self.data_y.append(packet.y / 1000.0)
        self.data_z.append(packet.z / 1000.0)
        if len(self.data_x) > 1:
            self.stats_quality.setText("Quality: {:5d}".format(packet.quality))

            self.plot_xy.setData(self.data_x    , self.data_y)
            self.plot_xy_pt.setData([self.data_x[-1]], [self.data_y[-1]])

            self.plot_xz.setData(self.data_x    , self.data_z)
            self.plot_xz_pt.setData([self.data_x[-1]], [self.data_z[-1]])

            self.stats_xyz_avg.setText("xyz_avg: ({:0.3f}, {:0.3f}, {:0.3f})".format(np.mean(np.array(self.data_x)[-100:]), np.mean(np.array(self.data_y)[-100:]), np.mean(np.array(self.data_z)[-100:])))
            self.stats_xyz_std.setText("xyz_std: ({:0.3f}, {:0.3f}, {:0.3f})".format(np.std(np.array(self.data_x)[-100:]), np.std(np.array(self.data_y)[-100:]), np.std(np.array(self.data_z)[-100:])))

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()
            return

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def reset(self):
        self.data_x = deque([], TRAIL_LENGTH)
        self.data_y = deque([], TRAIL_LENGTH)
        self.data_z = deque([], TRAIL_LENGTH)

    def changeGraph(self, state):
        self.graph_xy.clear()
        self.graph_xz.clear()
        if state == QtCore.Qt.Checked:
            self.plot_xy = self.graph_xy.plot(pen=None, symbol='o')
            self.plot_xy_pt = self.graph_xy.plot(pen=None, symbol='o')
            self.plot_xz = self.graph_xz.plot(pen=None, symbol='o')
            self.plot_xz_pt = self.graph_xz.plot(pen=None, symbol='o')
        else:
            self.plot_xy = self.graph_xy.plot(pen=pg.mkPen('b', width=2))
            self.plot_xy_pt = self.graph_xy.plot(pen=pg.mkPen('c', width=1), symbol='o', symbolPen='c', symbolSize=8, symbolBrush='c')
            self.plot_xz = self.graph_xz.plot(pen=pg.mkPen('b', width=2))
            self.plot_xz_pt = self.graph_xz.plot(pen=pg.mkPen('c', width=1), symbol='o', symbolPen='c', symbolSize=8, symbolBrush='c')
