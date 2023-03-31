# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

# Local libraries
from cdp import PressureV2
from network_objects import *
from settings import *


class PlotPressureV2(QtWidgets.QMainWindow):
    type = PressureV2.type

    def __init__(self, serial):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QScrollArea()
        self.central.setWidgetResizable(True)
        self.central_inner_widget = QtWidgets.QWidget()
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Pressure V2 Devices ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtWidgets.QGridLayout()
        self.running = True

        self.sub_window = PlotPressureV2SubWindow(self.serial, self)
        self.sub_window.show()

        self.id_total = 0
        self.from_id_id_labels = dict()
        self.from_id_count_labels = dict()
        self.from_id_freq_labels = dict()
        self.from_id_enable_checks = dict()
        self.from_id_frequency_deques = dict()
        self.from_id_times = dict()
        self.from_id_count = dict()
        self.from_id_p_data = dict()
        self.from_ids = np.array([])
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[self.type])

        self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtWidgets.QLabel("Packet Count"), 0, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel("Frequency"), 0, 2)
        self.grid_layout.addWidget(QtWidgets.QLabel("Enable"), 0, 3)

        self.update_labels()
        #This allows for a dynamic window size where the number of serials already in the window after
        #one pass affects the size of the serial choice window.
        row_height = 20
        self.resize(400, row_height+(row_height * len(self.from_id_id_labels)))

        self.central_inner_widget.setLayout(self.grid_layout)
        self.central.setWidget(self.central_inner_widget)
        
        self.setCentralWidget(self.central)
        self.resize(400, 50)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        self.update_labels()

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False
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
                self.from_id_times.update([(_target_id, deque([], TRAIL_LENGTH))])
                self.from_id_count.update([(_target_id, 0)])
                self.from_id_p_data.update([(_target_id, deque([], TRAIL_LENGTH))])
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
                    self.grid_layout.addWidget(QtWidgets.QLabel("Enable"), _row, _column + 3)
                self.id_total += 1

            self.from_id_times[_target_id].append(UwbNetwork.nodes[self.serial].cdp_pkts_time[self.type][idx - _current_size])

            self.from_id_count[_target_id] += 1

            _scale = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].scale / 2147483647.0
            self.from_id_p_data[_target_id].append(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].pressure * _scale)

        for _target_id in self.from_ids:
            self.from_id_frequency_deques[_target_id].append((self.from_id_count[_target_id], time.monotonic()))

        for _row in range(self.id_total):
            _target_id = int(self.from_ids[_row])
            if self.from_id_id_labels[_row].text() != '0x{:08X}'.format(_target_id):
                self.from_id_id_labels[_row].setText('0x{:08X}'.format(_target_id))

            if len(self.from_id_times[_target_id]) == 0: continue

            _freq = UwbNetwork.nodes[self.serial].calculate_frequency(self.from_id_frequency_deques[_target_id])
            self.from_id_count_labels[_row].setText('{:5d}'.format(self.from_id_count[_target_id]))
            self.from_id_freq_labels[_row].setText('{:5.1f}Hz'.format(_freq))

            if self.from_id_enable_checks[_row].isChecked():
                self.sub_window.update_data('pressure', '0x{:08X}'.format(_target_id),
                                            np.array(self.from_id_p_data[_target_id]),
                                            np.array(self.from_id_times[_target_id]))
            else:
                self.sub_window.update_data('pressure', '0x{:08X}'.format(_target_id),
                                            np.array([]),
                                            np.array([]))

    def reset(self):
        if self.sub_window.isVisible():
            for target_id in self.from_ids:
                self.from_id_count[target_id] = 0
                self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
                self.from_id_p_data[target_id] = deque([], TRAIL_LENGTH)
                self.from_id_times[target_id] = deque([], TRAIL_LENGTH)
            self.sub_window.color_offset = 0
            for row in range(self.id_total):
                target_id = int(self.from_ids[row])
                self.sub_window.update_data('pressure', '0x{:08X}'.format(target_id),
                                            np.array([]),
                                            np.array([]))
            self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]


class PlotPressureV2SubWindow(pg.GraphicsLayoutWidget):

    def __init__(self, serial, parent):

        pg.GraphicsLayoutWidget.__init__(self)
        self.setWindowTitle('CUWB Monitor - Pressure V2 Plot ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(1200, 1200)
        self.parent = parent

        self.colors = ['r', 'g', 'b', 'c', 'm', 'y', 'w']
        self.color_offset = 0

        self.p_graph = self.addPlot(title='Pressure', row=0, col=0)
        self.legend_graph = self.addPlot(title='Legend', row=1, col=0)
        #self.p_graph.setYRange(-5, 5)
        self.p_graph.showGrid(x=True, y=True)
        self.legend = self.legend_graph.addLegend()

        self.p_data = dict()
        self.legend_data = dict()

        self.timer = self.startTimer(300)
        self.running = True

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()

    def update_data(self, plot_type, serial, data, time):

        if data.size == 0:
            if serial in self.p_data:
                self.p_data[serial].clear()
                self.legend_data[serial].clear()
                del self.p_data[serial]
                del self.legend_data[serial]
            return

        if not (serial in self.p_data):
            try:
                self.legend_graph.removeItem(self.legend)
            except Exception as e: print(e)

            self.p_data.update([(serial, self.p_graph.plot(name=serial, pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.legend_data.update([(serial, self.p_graph.plot(name=serial, pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.color_offset += 1

            self.legend = self.legend_graph.addLegend()
            self.legend.clear()
            for _curve_serials in self.p_data.keys():
                self.legend.addItem(self.legend_data[_curve_serials], _curve_serials)

        if plot_type == 'pressure' and len(time) > 1: self.p_data[serial].setData(time, data)

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False
