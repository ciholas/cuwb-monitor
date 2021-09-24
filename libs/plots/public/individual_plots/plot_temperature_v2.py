# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from cdp import TemperatureV2
from network_objects import *
from settings import *


class PlotTemperatureV2(QtGui.QMainWindow):
    type = TemperatureV2.type

    def __init__(self, serial):

        QtGui.QMainWindow.__init__(self)

        self.central = QtGui.QWidget()  #This will be our central widget
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Temperature V2 Devices ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtGui.QGridLayout()
        self.running = True

        self.sub_window = PlotTemperatureV2SubWindow(self.serial, self)

        self.id_total = 0
        self.from_id_id_labels = dict()
        self.from_id_count_labels = dict()
        self.from_id_freq_labels = dict()
        self.from_id_enable_checks = dict()
        self.from_id_frequency_deques = dict()
        self.from_id_times = dict()
        self.from_id_count = dict()
        self.from_id_temp_data = dict()
        self.from_ids = np.array([])
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[self.type])

        self.grid_layout.addWidget(QtGui.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtGui.QLabel("Packet Count"), 0, 1)
        self.grid_layout.addWidget(QtGui.QLabel("Frequency"), 0, 2)
        self.grid_layout.addWidget(QtGui.QLabel("Enable"), 0, 3)

        self.update_labels()

        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        self.resize(400, 50)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()

        self.update_labels()

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def update_labels(self):
        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - self.previous_count
        if _current_size > 1000: _current_size = 1000
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
        for idx in range(_current_size):
            _target_id = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].serial_number.as_int
            if not (_target_id in self.from_ids):
                self.from_id_id_labels.update([(self.id_total, QtGui.QLabel())])
                self.from_id_count_labels.update([(self.id_total, QtGui.QLabel())])
                self.from_id_freq_labels.update([(self.id_total, QtGui.QLabel())])
                self.from_id_enable_checks.update([(self.id_total, QtGui.QCheckBox())])
                self.from_id_times.update([(_target_id, deque([], TRAIL_LENGTH))])
                self.from_id_frequency_deques.update([(_target_id, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
                self.from_id_count.update([(_target_id, 0)])
                self.from_id_temp_data.update([(_target_id, deque([], TRAIL_LENGTH))])
                self.from_ids = np.sort(np.append(self.from_ids, _target_id))

                _row = self.id_total
                _column = 0
                self.grid_layout.addWidget(self.from_id_id_labels[self.id_total], _row + 1, _column + 0)
                self.grid_layout.addWidget(self.from_id_count_labels[self.id_total], _row + 1, _column + 1)
                self.grid_layout.addWidget(self.from_id_freq_labels[self.id_total], _row + 1, _column + 2)
                self.grid_layout.addWidget(self.from_id_enable_checks[self.id_total], _row + 1, _column + 3)

                if _column > 0:
                    _row = 2
                    self.grid_layout.addWidget(QtGui.QLabel("Serial#"), _row, _column + 0)
                    self.grid_layout.addWidget(QtGui.QLabel("Packet Count"), _row, _column + 1)
                    self.grid_layout.addWidget(QtGui.QLabel("Frequency"), _row, _column + 2)
                    self.grid_layout.addWidget(QtGui.QLabel("Enable"), _row, _column + 3)
                self.id_total += 1

            self.from_id_times[_target_id].append(UwbNetwork.nodes[self.serial].cdp_pkts_time[self.type][idx - _current_size])
            self.from_id_count[_target_id] += 1

            _scale = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].scale / 32767.0
            self.from_id_temp_data[_target_id].append(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].temperature * _scale)

        for _target_id in self.from_ids:
            self.from_id_frequency_deques[_target_id].append((self.from_id_count[_target_id], time.time()))

        for _row in range(self.id_total):
            _target_id = int(self.from_ids[_row])
            if self.from_id_id_labels[_row].text() != '0x{:08X}'.format(_target_id):
                self.from_id_id_labels[_row].setText('0x{:08X}'.format(_target_id))

            if len(self.from_id_times[_target_id]) == 0: continue

            _freq = UwbNetwork.nodes[self.serial].calculate_frequency(self.from_id_frequency_deques[_target_id])
            self.from_id_count_labels[_row].setText('{:5d}'.format(self.from_id_count[_target_id]))
            self.from_id_freq_labels[_row].setText('{:5.1f}Hz'.format(_freq))

            if self.from_id_enable_checks[_row].isChecked():
                self.sub_window.update_data('temperature', '0x{:08X}'.format(_target_id),
                                            np.array(self.from_id_temp_data[_target_id]),
                                            np.array(self.from_id_times[_target_id]))
            else:
                self.sub_window.update_data('temperature', '0x{:08X}'.format(_target_id),
                                            np.array([]),
                                            np.array([]))

    def reset(self):
        for target_id in self.from_ids:
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
            self.from_id_temp_data[target_id] = deque([], TRAIL_LENGTH)
            self.from_id_times[target_id] = deque([], TRAIL_LENGTH)
        self.sub_window.color_offset = 0
        for row in range(self.id_total):
            target_id = int(self.from_ids[row])
            self.sub_window.update_data('temperature', '0x{:08X}'.format(target_id),
                                        np.array([]),
                                        np.array([]))
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]


class PlotTemperatureV2SubWindow(pg.GraphicsWindow):
    def __init__(self, serial, parent):

        pg.GraphicsWindow.__init__(self)
        self.setWindowTitle('CUWB Monitor - Temperature V2 Plot ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(1200, 1200)
        self.parent = parent

        self.colors = ['r', 'g', 'b', 'c', 'm', 'y', 'w']
        self.color_offset = 0

        self.temp_graph = self.addPlot(title='Temperature', row=0, col=0)
        self.legend_graph = self.addPlot(title='Legend', row=1, col=0)
        #self.temp_graph.setYRange(-5, 5)
        self.temp_graph.showGrid(x=True, y=True)
        self.legend = self.legend_graph.addLegend()

        self.temp_data = dict()
        self.legend_data = dict()

        self.timer = self.startTimer(300)
        self.running = True

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()
            return

    def update_data(self, plot_type, serial, data, time):

        if data.size == 0:
            if serial in self.temp_data:
                self.temp_data[serial].clear()
                self.legend_data[serial].clear()
                del self.temp_data[serial]
                del self.legend_data[serial]
            return

        if not (serial in self.temp_data):
            try:
                self.legend_graph.legend.scene().removeItem(self.legend_graph.legend)
            except Exception as e: print(e)

            self.temp_data.update([(serial, self.temp_graph.plot(name=serial, pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.legend_data.update([(serial, self.temp_graph.plot(name=serial, pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.color_offset += 1

            self.legend = self.legend_graph.addLegend()
            for _curve_serials in self.temp_data.keys():
                self.legend.addItem(self.legend_data[_curve_serials], _curve_serials)

        if   plot_type == 'temperature': self.temp_data[serial].setData(time, data)

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False
