# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

# Local libraries
from cdp import AccelerometerV2
from network_objects import *
from settings import *


class PlotAccelV2(QtWidgets.QMainWindow):
    type = AccelerometerV2.type

    def __init__(self, serial):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()  #This will be our central widget
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Accelerometer V2 Devices ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtWidgets.QGridLayout()
        self.running = True

        self.sub_windows = dict([])

        self.id_total = 0
        self.from_id_id_labels = dict()
        self.from_id_count_labels = dict()
        self.from_id_freq_labels = dict()
        self.from_id_enable_checks = dict()
        self.from_id_count = dict()
        self.from_id_frequency_deques = dict()
        self.from_ids = np.array([])
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[self.type])

        self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtWidgets.QLabel("Packet Count"), 0, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel("Frequency"), 0, 2)
        self.grid_layout.addWidget(QtWidgets.QLabel("Print"), 0, 3)

        self.update_labels()

        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        self.resize(400, 50)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        self.update_labels()

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)
        self.close()

    def update_labels(self):
        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - self.previous_count
        if _current_size > 1000: _current_size = 1000
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
        for idx in range(_current_size):
            _target_id = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].serial_number.as_int
            if not (_target_id in self.from_ids):
                self.from_id_id_labels.update([(self.id_total, QtWidgets.QLabel())])
                self.from_id_count_labels.update([(self.id_total, QtWidgets.QLabel())])
                self.from_id_freq_labels.update([(self.id_total, QtWidgets.QLabel())])
                self.from_id_enable_checks.update([(self.id_total, QtWidgets.QCheckBox())])
                self.from_id_frequency_deques.update([(_target_id, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
                self.from_id_count.update([(_target_id, 0)])
                self.from_ids = np.sort(np.append(self.from_ids, _target_id))

                _row = self.id_total
                _column = 0
                self.grid_layout.addWidget(self.from_id_id_labels[self.id_total], _row+1, _column + 0)
                self.grid_layout.addWidget(self.from_id_count_labels[self.id_total], _row+1, _column + 1)
                self.grid_layout.addWidget(self.from_id_freq_labels[self.id_total], _row+1, _column + 2)
                self.grid_layout.addWidget(self.from_id_enable_checks[self.id_total], _row+1, _column + 3)

                if _column > 0:
                    _row = 2
                    self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), _row, _column + 0)
                    self.grid_layout.addWidget(QtWidgets.QLabel("Packet Count"), _row, _column + 1)
                    self.grid_layout.addWidget(QtWidgets.QLabel("Frequency"), _row, _column + 2)
                    self.grid_layout.addWidget(QtWidgets.QLabel("Enable"), _row, _column + 3)
                self.id_total += 1

            self.from_id_count[_target_id] += 1

            if _target_id in self.from_ids:
                _row = np.where(self.from_ids == _target_id)[0][0]
                if self.from_id_enable_checks[_row].isChecked():
                    print(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size])

            if _target_id in self.sub_windows.keys():
                _scale = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].scale / 2147483647.0
                _x = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].x * _scale
                _y = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].y * _scale
                _z = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].z * _scale
                _time = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].network_time * TICK
                # _time = UwbNetwork.nodes[self.serial].cdp_pkts_time[self.type][idx - _current_size]

                self.sub_windows[_target_id].update_data(_x, _y, _z, _time)

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
        self.sub_windows.update([(serial, PlotAccelV2SubWindow(serial, self))])
        self.sub_windows[serial].show()

    def reset(self):
        for target_id in self.from_ids:
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
        for target_id in self.sub_windows:
            self.sub_windows[target_id].reset()
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]


class PlotAccelV2SubWindow(pg.GraphicsLayoutWidget):
    def __init__(self, serial, parent):

        pg.GraphicsLayoutWidget.__init__(self)
        self.setWindowTitle('CUWB Monitor - Accel V2 Plot ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(1200, 400)
        self.parent = parent

        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)

        self.graph = self.addPlot(title='Accelerometer XYZ', row=0, col=0)
        self.graph.setYRange(-5, 5)
        self.graph.showGrid(x=True, y=True)

        self.legend = self.graph.addLegend()
        self.plot_x = self.graph.plot(name='X', pen=pg.mkPen('r', width=2))
        self.plot_y = self.graph.plot(name='Y', pen=pg.mkPen('g', width=2))
        self.plot_z = self.graph.plot(name='Z', pen=pg.mkPen('b', width=2))

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()
            return

        if len(self.t_data) > 1:
            self.plot_x.setData(self.t_data, self.x_data)
            self.plot_y.setData(self.t_data, self.y_data)
            self.plot_z.setData(self.t_data, self.z_data)

    def update_data(self, x, y, z, t):

        self.x_data.append(x)
        self.y_data.append(y)
        self.z_data.append(z)
        self.t_data.append(t)

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def reset(self):
        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)
