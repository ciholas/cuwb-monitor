# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

# Local libraries
from cdp import PingV5
from network_objects import *
from settings import *


class PlotPingV5(QtWidgets.QMainWindow):
    type = PingV5.type

    def __init__(self, serial):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QScrollArea()
        self.central.setWidgetResizable(True)
        self.central_inner_widget = QtWidgets.QWidget()
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Ping Plotter ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtWidgets.QGridLayout()
        self.type = PingV5.type
        self.running = True

        self.id_total = 0
        self.from_id_id_labels = dict()
        self.from_id_iid_cf_labels = dict()
        self.from_id_iid_checks = dict()
        self.id_iid_plotting = dict()
        self.from_id_iid_times = dict()
        self.from_id_frequency_deques = dict()
        self.from_id_iid_count = dict()
        self.from_id_iid_count_payloads = dict()
        self.from_id_iid_tp_data = dict()
        self.from_id_iid_fp_data = dict()
        self.from_id_iid_payload_sizes = dict()
        self.from_ids = np.array([])
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[PingV5.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[PingV5.type])

        self.plot_window = PlotPingWindow(self)
        self.plot_window.show()

        self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtWidgets.QLabel("ID0 P/# - Hz"), 0, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel("En"), 0, 2)

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
            self.killTimer(self.timer)
            self.close()
            return

        if self.plot_window.running:
            self.update_labels()
        else:
            self.killTimer(self.timer)
            self.close()

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)

    def update_labels(self):

        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[PingV5.type] - self.previous_count
        if _current_size > 1000: _current_size = 1000
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[PingV5.type]
        for idx in range(_current_size):
            _target_id = UwbNetwork.nodes[self.serial].cdp_pkts[PingV5.type][idx - _current_size].source_serial_number.as_int
            if not (_target_id in self.from_ids):
                self.from_id_id_labels.update([(self.id_total, QtWidgets.QLabel())])
                self.from_id_iid_cf_labels.update([(self.id_total, [QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel()])])
                self.from_id_iid_checks.update([(self.id_total, [QtWidgets.QCheckBox(), QtWidgets.QCheckBox(), QtWidgets.QCheckBox(), QtWidgets.QCheckBox(), QtWidgets.QCheckBox(), QtWidgets.QCheckBox()])])
                self.id_iid_plotting.update([(_target_id, [False, False, False, False, False, False])])
                self.from_id_iid_times.update([(_target_id, [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)])])
                self.from_id_iid_count.update([(_target_id, [0, 0, 0, 0, 0, 0])])
                self.from_id_iid_count_payloads.update([(_target_id, [0, 0, 0, 0, 0, 0])])
                self.from_id_frequency_deques.update([(_target_id, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
                self.from_id_iid_tp_data.update([(_target_id, [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)])])
                self.from_id_iid_fp_data.update([(_target_id, [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)])])
                self.from_id_iid_payload_sizes.update([(_target_id, [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)])])
                self.from_ids = np.sort(np.append(self.from_ids, _target_id))

                _row = self.id_total
                _column = 0
                self.grid_layout.addWidget(self.from_id_id_labels[self.id_total], _row + 1, _column + 0)
                self.grid_layout.addWidget(self.from_id_iid_cf_labels[self.id_total][0], _row + 1, _column + 1)
                self.grid_layout.addWidget(self.from_id_iid_checks[self.id_total][0], _row + 1, _column + 2)

                self.id_total += 1

            _iid = UwbNetwork.nodes[self.serial].cdp_pkts[PingV5.type][idx - _current_size].interface_id
            self.from_id_iid_times[_target_id][_iid].append(UwbNetwork.nodes[self.serial].cdp_pkts_time[PingV5.type][idx - _current_size])
            self.from_id_iid_count[_target_id][_iid] += 1
            if len(UwbNetwork.nodes[self.serial].cdp_pkts[PingV5.type][idx - _current_size].payload) > 0:
                self.from_id_iid_count_payloads[_target_id][_iid] += 1

            _fp = UwbNetwork.nodes[self.serial].cdp_pkts[PingV5.type][idx - _current_size].signal_strength.get_first_path(UwbNetwork.prf)
            _tp = UwbNetwork.nodes[self.serial].cdp_pkts[PingV5.type][idx - _current_size].signal_strength.get_total_path(UwbNetwork.prf)
            self.from_id_iid_fp_data[_target_id][_iid].append(_fp)
            self.from_id_iid_tp_data[_target_id][_iid].append(_tp)
            self.from_id_iid_payload_sizes[_target_id][_iid].append(len(UwbNetwork.nodes[self.serial].cdp_pkts[PingV5.type][idx - _current_size].payload))

        for _target_id in self.from_ids:
            self.from_id_frequency_deques[_target_id].append((self.from_id_iid_count[_target_id][0], time.monotonic()))

        for _row in range(self.id_total):
            _target_id = int(self.from_ids[_row])
            if self.from_id_id_labels[_row].text() != '0x{:08X}'.format(_target_id):
                self.from_id_id_labels[_row].setText('0x{:08X}'.format(_target_id))
                for _iid in range(6):
                    if self.id_iid_plotting[self.from_ids[_row]][_iid]:
                        self.from_id_iid_checks[_row][_iid].setCheckState(2) #Qt.Qt.Checked)
                    else:
                        self.from_id_iid_checks[_row][_iid].setCheckState(0) #Qt.Qt.Unchecked)

            for _iid in range(6):
                if len(self.from_id_iid_times[_target_id][_iid]) == 0: continue

                _freq = UwbNetwork.nodes[self.serial].calculate_frequency(self.from_id_frequency_deques[_target_id])
                self.from_id_iid_cf_labels[_row][_iid].setText('{:d}/{:d} - {:0.1f}Hz'.format(self.from_id_iid_count_payloads[_target_id][_iid],
                                                                                              self.from_id_iid_count[_target_id][_iid],
                                                                                              _freq))
                if self.from_id_iid_checks[_row][_iid].isChecked():
                    self.id_iid_plotting[_target_id][_iid] = True
                    self.plot_window.update_data('tp', '0x{:08X}:{:d}'.format(_target_id , _iid),
                                                 np.array(self.from_id_iid_tp_data[_target_id][_iid]),
                                                 np.array(self.from_id_iid_times[_target_id][_iid]))
                    self.plot_window.update_data('fp', '0x{:08X}:{:d}'.format(_target_id , _iid),
                                                 np.array(self.from_id_iid_fp_data[_target_id][_iid]),
                                                 np.array(self.from_id_iid_times[_target_id][_iid]))
                    self.plot_window.update_data('size', '0x{:08X}:{:d}'.format(_target_id, _iid),
                                                 np.array(self.from_id_iid_payload_sizes[_target_id][_iid]),
                                                 np.array(self.from_id_iid_times[_target_id][_iid]))

                else:
                    self.id_iid_plotting[_target_id][_iid] = False
                    self.plot_window.update_data('tp', '0x{:08X}:{:d}'.format(_target_id, _iid),
                                                 np.array([]),
                                                 np.array([]))
                    self.plot_window.update_data('fp', '0x{:08X}:{:d}'.format(_target_id, _iid),
                                                 np.array([]),
                                                 np.array([]))
                    self.plot_window.update_data('size', '0x{:08X}:{:d}'.format(_target_id, _iid),
                                                 np.array([]),
                                                 np.array([]))

    def reset(self):
        if self.plot_window.isVisible():
            for target_id in self.from_ids:
                self.from_id_iid_count[target_id] = [0, 0, 0, 0, 0, 0]
                self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
                self.from_id_iid_tp_data[target_id] = [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)]
                self.from_id_iid_fp_data[target_id] = [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)]
                self.from_id_iid_payload_sizes[target_id] = [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)]
                self.from_id_iid_times[target_id] = [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)]
                self.from_id_iid_count_payloads[target_id] = [0, 0, 0, 0, 0, 0]
            self.plot_window.color_offset = 0
            for row in range(self.id_total):
                target_id = int(self.from_ids[row])
                for iid in range(6):
                    self.plot_window.update_data('tp', '0x{:08X}:{:d}'.format(target_id, iid),
                                                 np.array([]),
                                                 np.array([]))
                    self.plot_window.update_data('fp', '0x{:08X}:{:d}'.format(target_id, iid),
                                                 np.array([]),
                                                 np.array([]))
                    self.plot_window.update_data('size', '0x{:08X}:{:d}'.format(target_id, iid),
                                                 np.array([]),
                                                 np.array([]))
            self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]

class PlotPingWindow(pg.GraphicsLayoutWidget):
    def __init__(self, parent, *args):
        pg.GraphicsLayoutWidget.__init__(self, *args)

        self.colors = ['r', 'g', 'b', 'c', 'm', 'y', 'w']
        self.color_offset = 0
        self.setWindowTitle("CUWB Monitor - Ping Packet Graphical Window")
        self.resize(900, 900)
        self.parent = parent

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

        self.tp_graph = self.addPlot(title='Total Path (dB)', row=0, col=0)
        self.fp_graph = self.addPlot(title='First Path (dB)', row=1, col=0)
        self.size_graph = self.addPlot(title='Packet Size', row=2, col=0)
        self.tp_graph.setYRange(-125, -60)
        self.fp_graph.setYRange(-125, -60)
        self.tp_graph.showGrid(x=True, y=True)
        self.fp_graph.showGrid(x=True, y=True)
        self.size_graph.showGrid(x=True, y=True)
        self.legend = self.size_graph.addLegend(size=(100,20), offset=(0,100))

        self.tp_data = dict()
        self.fp_data = dict()
        self.size_data = dict()


    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def update_data(self, plot_type, serial, data, time):

        if data.size == 0:
            if serial in self.tp_data:
                self.tp_data[serial].clear()
                self.fp_data[serial].clear()
                self.size_data[serial].clear()
                del self.tp_data[serial]
                del self.fp_data[serial]
                del self.size_data[serial]

                try:
                    self.legend.clear()
                except Exception as e: print(e)

                for _curve_serials in self.tp_data.keys():
                    self.legend.addItem(self.size_data[_curve_serials], _curve_serials)
            return

        if not (serial in self.tp_data):

            self.tp_data.update([(serial, self.tp_graph.plot(name=serial, pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.fp_data.update([(serial, self.fp_graph.plot(name=serial, pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.size_data.update([(serial, self.size_graph.plot(name=serial, pen=pg.mkPen(width=0), symbolBrush=self.colors[self.color_offset % len(self.colors)]))])
            self.color_offset += 1

        if len(time) > 1:
            if plot_type == 'tp'  : self.tp_data[serial].setData(time, data)
            if plot_type == 'fp'  : self.fp_data[serial].setData(time, data)
            if plot_type == 'size': self.size_data[serial].setData(time, data)

    def timerEvent(self, e):

        if not UwbNetwork.running or not self.parent.running:
            self.running = False
            self.close()
