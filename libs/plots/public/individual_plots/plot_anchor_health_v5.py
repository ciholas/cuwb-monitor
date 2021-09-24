# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from cdp import AnchorHealthV5, FullDeviceID
from network_objects import *
from settings import *


class PlotAnchorHealthV5(QtGui.QMainWindow):
    type = AnchorHealthV5.type

    def __init__(self, serial):

        QtGui.QMainWindow.__init__(self)

        self.central = QtGui.QScrollArea()
        self.central_inner_widget = QtGui.QWidget()
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Anchor Health V5 Plotter ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtGui.QGridLayout()
        self.running = True

        self.sub_windows = dict([])

        self.id_total = 0
        self.from_id_id_labels = dict()
        self.from_id_count_labels = dict()
        self.from_id_freq_labels = dict()
        self.from_id_enable_checks = dict()
        self.from_id_frequency_deques = dict()
        self.from_id_count = dict()
        self.from_ids = np.array([])
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[AnchorHealthV5.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[AnchorHealthV5.type])

        self.grid_layout.addWidget(QtGui.QLabel('Serial #'), 0, 0)
        self.grid_layout.addWidget(QtGui.QLabel('Packet Count'), 0, 1)
        self.grid_layout.addWidget(QtGui.QLabel('Frequency'), 0, 2)
        self.grid_layout.addWidget(QtGui.QLabel('Print'), 0, 3)

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
        self.killTimer(self.timer)
        self.running = False

    def update_labels(self):
        current_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
        current_size = current_count - self.previous_count
        if current_size > 1000:
            current_size = 1000
        self.previous_count = current_count
        for idx in range(current_size):
            target_id = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - current_size].serial_number.as_int
            if not (target_id in self.from_ids):
                self.from_id_id_labels.update([(self.id_total, QtGui.QLabel())])
                self.from_id_count_labels.update([(self.id_total, QtGui.QLabel())])
                self.from_id_freq_labels.update([(self.id_total, QtGui.QLabel())])
                self.from_id_enable_checks.update([(self.id_total, QtGui.QCheckBox())])
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
                    self.grid_layout.addWidget(QtGui.QLabel("Serial #"), row, column + 0)
                    self.grid_layout.addWidget(QtGui.QLabel("Packet Count"), row, column + 1)
                    self.grid_layout.addWidget(QtGui.QLabel("Frequency"), row, column + 2)
                    self.grid_layout.addWidget(QtGui.QLabel("Print"), row, column + 3)
                self.id_total += 1

            self.from_id_count[target_id] += 1

            if target_id in self.from_ids:
                row = np.where(self.from_ids == target_id)[0][0]
                if self.from_id_enable_checks[row].isChecked():
                    print(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - current_size])

            if target_id in self.sub_windows:
                packet = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - current_size]

                self.sub_windows[target_id].updateData(packet)

        for _target_id in self.from_ids:
            self.from_id_frequency_deques[_target_id].append((self.from_id_count[_target_id], time.time()))

        for row in range(self.id_total):
            target_id = int(self.from_ids[row])
            if self.from_id_id_labels[row].text() != '0x{:08X}'.format(target_id):
                self.from_id_id_labels[row].setText('0x{:08X}'.format(target_id))
                self.from_id_id_labels[row].setStyleSheet('color:blue')
                self.from_id_id_labels[row].mouseReleaseEvent = partial(self.labelClickEvent, target_id)

            freq = UwbNetwork.nodes[self.serial].calculate_frequency(self.from_id_frequency_deques[_target_id])
            self.from_id_count_labels[row].setText('{:5d}'.format(self.from_id_count[target_id]))
            self.from_id_freq_labels[row].setText('{:5.1f}Hz'.format(freq))

    def labelClickEvent(self, serial, e):
        self.sub_windows.update([(serial, PlotAnchorHealthV5SubWindow(serial, self))])

    def reset(self):
        for target_id in self.from_ids:
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
        for target_id in self.sub_windows:
            self.sub_windows[target_id].reset()

class PlotAnchorHealthV5SubWindow(pg.GraphicsWindow):

    def __init__(self, serial, parent):

        self.data_t = deque([], TRAIL_LENGTH)
        self.data_q = deque([], TRAIL_LENGTH)

        pg.GraphicsWindow.__init__(self)
        self.show()
        self.setWindowTitle('CUWB Monitor - Anchor Health V5 ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(900, 350)
        self.packets_received = 0
        self.parent = parent

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.graph_quality = self.addPlot(title='Average Quality', row=0, col=0, colspan=2)
        self.graph_quality.showGrid(x=True, y=True)
        self.graph_quality.setYRange(0, 10000)
        self.plot_quality = self.graph_quality.plot(pen=pg.mkPen('y', width=5))

        self.bad_anchors_label = self.addLabel(text='', row=2, col=0, colspan=2)
        self.error_code_label = self.addLabel(text='Interanchor Comms Error Code:', row=1, col=0, colspan=2)

    def updateData(self, packet):

        quality = packet.average_quality
        self.data_t.append(self.packets_received)
        self.data_q.append(quality)
        self.plot_quality.setData(self.data_t, self.data_q)
        self.packets_received += 1

        if packet.bad_paired_anchors:
            bad_anchors = 'Bad Paired Anchors: '
            for device_id in packet.bad_paired_anchors:
                bad_anchors += (str(device_id.serial_number) + ', ')
            self.bad_anchors_label.setText(bad_anchors[:-2])
        else:
            self.bad_anchors_label.setText('')

        error_code = 'Interanchor Comms Error Code: '
        if packet.interanchor_comms_error_code == 0:
            error_code += 'No Error'
        elif packet.interanchor_comms_error_code == 1:
            error_code += 'Blacklisting'
        elif packet.interanchor_comms_error_code == 2:
            error_code += 'Bad Survey'
        self.error_code_label.setText(error_code)

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def reset(self):
        self.data_t = deque([], TRAIL_LENGTH)
        self.data_q = deque([], TRAIL_LENGTH)
        self.plot_quality.setData(self.data_t, self.data_q)
        self.packets_received = 0
