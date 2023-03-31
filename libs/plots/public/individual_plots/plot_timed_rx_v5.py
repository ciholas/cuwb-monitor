# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

# Local libraries
from cdp import TimedRxV5
from network_objects import *
from settings import *


class PlotTimedRxV5(QtWidgets.QMainWindow):
    type = TimedRxV5.type

    def __init__(self, serial):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()  #This will be our central widget
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Timed Reception Plotter ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtWidgets.QGridLayout()
        self.running = True

        self.id_total = 0
        self.from_id_id_labels = dict()
        self.from_id_iid_rxq_labels = dict()
        self.from_id_iid_cf_labels = dict()
        self.from_id_iid_checks = dict()
        self.id_iid_plotting = dict()
        self.from_id_iid_times = dict()
        self.from_id_iid_count = dict()
        self.from_id_iid_tp_data = dict()
        self.from_id_iid_fp_data = dict()
        self.from_id_iid_rx_qual = dict()
        self.from_id_frequency_deques = dict()
        self.from_ids = np.array([])
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[TimedRxV5.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[TimedRxV5.type])

        self.rf_plot_window = RfPlotSubWindow(self.serial, self)
        self.rf_plot_window.show()

        self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtWidgets.QLabel("RxQ"), 0, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel("#/Freq"),0, 2)
        self.grid_layout.addWidget(QtWidgets.QLabel("En"), 0, 3)

        self.update_labels()

        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        self.resize(400, 50)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        if self.rf_plot_window.running:
            self.update_labels()
        else:
            self.killTimer(self.timer)
            self.close()

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def update_labels(self):
        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[TimedRxV5.type] - self.previous_count
        if _current_size > 1000: _current_size = 1000
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[TimedRxV5.type]
        for idx in range(_current_size):
            _target_id = UwbNetwork.nodes[self.serial].cdp_pkts[TimedRxV5.type][idx - _current_size].source_serial_number.as_int
            if not (_target_id in self.from_ids):
                self.from_id_id_labels.update([(self.id_total, QtWidgets.QLabel())])
                self.from_id_iid_cf_labels.update([(self.id_total, [QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel()])])
                self.from_id_iid_rxq_labels.update([(self.id_total, [QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel(), QtWidgets.QLabel()])])
                self.from_id_iid_checks.update([(self.id_total, [QtWidgets.QCheckBox(), QtWidgets.QCheckBox(), QtWidgets.QCheckBox(), QtWidgets.QCheckBox(), QtWidgets.QCheckBox(), QtWidgets.QCheckBox()])])
                self.id_iid_plotting.update([(_target_id, [False, False, False, False, False, False])])
                self.from_id_iid_times.update([(_target_id, [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)])])
                self.from_id_frequency_deques.update([(_target_id, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
                self.from_id_iid_count.update([(_target_id, [0, 0, 0, 0, 0, 0])])
                self.from_id_iid_tp_data.update([(_target_id, [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)])])
                self.from_id_iid_fp_data.update([(_target_id, [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)])])
                self.from_id_iid_rx_qual.update([(_target_id, [0, 0, 0, 0, 0, 0])])
                self.from_ids = np.sort(np.append(self.from_ids, _target_id))

                _row = self.id_total
                _column = 0
                self.grid_layout.addWidget(self.from_id_id_labels[self.id_total], _row+1, _column + 0)
                self.grid_layout.addWidget(self.from_id_iid_rxq_labels[self.id_total][0], _row+1, _column + 1)
                self.grid_layout.addWidget(self.from_id_iid_cf_labels[self.id_total][0], _row+1, _column + 2)
                self.grid_layout.addWidget(self.from_id_iid_checks[self.id_total][0], _row+1, _column + 3)

                if _column > 0:
                    _row = 2
                    self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), _row, _column + 0)
                    self.grid_layout.addWidget(QtWidgets.QLabel("RxQ"), _row, _column + 1)
                    self.grid_layout.addWidget(QtWidgets.QLabel("#/Freq ID0"), _row, _column + 2)
                    self.grid_layout.addWidget(QtWidgets.QLabel("En"), _row, _column + 3)
                self.id_total += 1

            _iid = UwbNetwork.nodes[self.serial].cdp_pkts[TimedRxV5.type][idx - _current_size].interface_id
            self.from_id_iid_times[_target_id][_iid].append(UwbNetwork.nodes[self.serial].cdp_pkts_time[TimedRxV5.type][idx - _current_size])
            self.from_id_iid_count[_target_id][_iid] += 1

            _fp = UwbNetwork.nodes[self.serial].cdp_pkts[TimedRxV5.type][idx - _current_size].signal_strength.get_first_path(UwbNetwork.prf)
            _tp = UwbNetwork.nodes[self.serial].cdp_pkts[TimedRxV5.type][idx - _current_size].signal_strength.get_total_path(UwbNetwork.prf)
            self.from_id_iid_fp_data[_target_id][_iid].append(_fp)
            self.from_id_iid_tp_data[_target_id][_iid].append(_tp)

            self.from_id_iid_rx_qual[_target_id][_iid] = UwbNetwork.nodes[self.serial].cdp_pkts[TimedRxV5.type][idx - _current_size].rx_nt_quality

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
                self.from_id_iid_cf_labels[_row][_iid].setText('{:5d} / {:5.1f}Hz'.format(self.from_id_iid_count[_target_id][_iid], _freq))
                self.from_id_iid_rxq_labels[_row][_iid].setText('{:d}'.format(self.from_id_iid_rx_qual[_target_id][_iid]))
                if self.from_id_iid_checks[_row][_iid].isChecked():
                    self.id_iid_plotting[_target_id][_iid] = True
                    self.rf_plot_window.update_data('tp', '0x{:08X}:{:d}'.format(_target_id , _iid),
                                                        np.array(self.from_id_iid_tp_data[_target_id][_iid]),
                                                        np.array(self.from_id_iid_times[_target_id][_iid]))
                    self.rf_plot_window.update_data('fp', '0x{:08X}:{:d}'.format(_target_id , _iid),
                                                        np.array(self.from_id_iid_fp_data[_target_id][_iid]),
                                                        np.array(self.from_id_iid_times[_target_id][_iid]))
                else:
                    self.id_iid_plotting[_target_id][_iid] = False
                    self.rf_plot_window.update_data('tp', '0x{:08X}:{:d}'.format(_target_id, _iid),
                                                    np.array([]),
                                                    np.array([]))
                    self.rf_plot_window.update_data('fp', '0x{:08X}:{:d}'.format(_target_id, _iid),
                                                    np.array([]),
                                                    np.array([]))

    def reset(self):
        if self.isVisible():
            for target_id in self.from_ids:
                self.from_id_iid_times[target_id] = [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)]
                self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
                self.from_id_iid_tp_data[target_id] = [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)]
                self.from_id_iid_fp_data[target_id] = [deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH), deque([], TRAIL_LENGTH)]
                self.from_id_iid_count[target_id] = [0, 0, 0, 0, 0, 0]
                self.from_id_iid_rx_qual[target_id] = [0, 0, 0, 0, 0, 0]
            self.rf_plot_window.color_offset = 0
            for row in range(self.id_total):
                target_id = int(self.from_ids[row])
                for iid in range(6):
                    self.rf_plot_window.update_data('tp', '0x{:08X}:{:d}'.format(target_id, iid),
                                                    np.array([]),
                                                    np.array([]))
                    self.rf_plot_window.update_data('fp', '0x{:08X}:{:d}'.format(target_id, iid),
                                                    np.array([]),
                                                    np.array([]))
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[TimedRxV5.type]


class RfPlotSubWindow(pg.GraphicsLayoutWidget):
    def __init__(self, serial, parent):

        pg.GraphicsLayoutWidget.__init__(self)
        self.setWindowTitle('CUWB Monitor - Timed Reception RF Plot ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(1024, 600)
        self.parent = parent

        self.colors = ['r', 'g', 'b', 'c', 'm', 'y', 'w']
        self.color_offset = 0

        self.tp_graph = self.addPlot(title='Total Path (dB)', row=0, col=0)
        self.tp_graph.setYRange(-125, -60)
        self.tp_graph.showGrid(x=True, y=True)

        self.fp_graph = self.addPlot(title='First Path (dB)', row=1, col=0)
        self.fp_graph.setYRange(-125, -60)
        self.fp_graph.showGrid(x=True, y=True)

        self.legend_graph = self.addPlot(title='Legend', row=2, col=0)
        self.legend = self.legend_graph.addLegend()

        self.tp_data = dict()
        self.fp_data = dict()
        self.legend_data = dict()

        self.timer = self.startTimer(300)
        self.running = True

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()

    def update_data(self, plot_type, serial, data, time):

        if data.size == 0:
            if serial in self.tp_data:
                self.tp_data[serial].clear()
                self.fp_data[serial].clear()
                self.legend_data[serial].clear()
                del self.tp_data[serial]
                del self.fp_data[serial]
                del self.legend_data[serial]
            return

        if not (serial in self.tp_data):
            try:
                self.legend.clear()
                self.legend_graph.removeItem(self.legend)
            except Exception as e: print(e)

            self.tp_data.update([(serial, self.tp_graph.plot(name=serial, pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.fp_data.update([(serial, self.fp_graph.plot(name=serial, pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.legend_data.update([(serial, self.fp_graph.plot(name=serial, pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.color_offset += 1

            self.legend = self.legend_graph.addLegend()
            for _curve_serials in self.tp_data.keys():
                self.legend.addItem(self.legend_data[_curve_serials], _curve_serials)

        if plot_type in ['tx_nt', 'rx_nt', 'rx_dt']:
            data = np.diff(np.float64(data))
            _idx = np.where(np.abs(data) > 10000.)
            data[_idx] = np.nan
            time = time[1::]

        if len(time) > 1:
            if   plot_type == 'tp'    : self.tp_data[serial].setData(time, data)
            elif plot_type == 'fp'    : self.fp_data[serial].setData(time, data)

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False
        self.close()
