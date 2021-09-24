# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from cdp import GyroscopeV2
from network_objects import *
from settings import *


class PlotGyroV2(QtGui.QMainWindow):
    type = GyroscopeV2.type

    def __init__(self, serial):

        QtGui.QMainWindow.__init__(self)

        self.central = QtGui.QWidget()  #This will be our central widget
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Gyroscope V2 Devices ID: 0x{:08X}'.format(serial))
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
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - len(UwbNetwork.nodes[self.serial].cdp_pkts[self.type])

        self.grid_layout.addWidget(QtGui.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtGui.QLabel("Packet Count"), 0, 1)
        self.grid_layout.addWidget(QtGui.QLabel("Frequency"), 0, 2)
        self.grid_layout.addWidget(QtGui.QLabel("Print"), 0, 3)

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
                    self.grid_layout.addWidget(QtGui.QLabel("Serial#"), _row, _column + 0)
                    self.grid_layout.addWidget(QtGui.QLabel("Packet Count"), _row, _column + 1)
                    self.grid_layout.addWidget(QtGui.QLabel("Frequency"), _row, _column + 2)
                    self.grid_layout.addWidget(QtGui.QLabel("Print"), _row, _column + 3)
                self.id_total += 1

            self.from_id_count[_target_id] += 1

            if _target_id in self.from_ids:
                _row = np.where(self.from_ids==_target_id)[0][0]
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
            self.from_id_frequency_deques[_target_id].append((self.from_id_count[_target_id], time.time()))

        for _row in range(self.id_total):
            _target_id = int(self.from_ids[_row])
            if self.from_id_id_labels[_row].text() != '0x{:08X}'.format(_target_id):
                self.from_id_id_labels[_row].setText('0x{:08X}'.format(_target_id))
                self.from_id_id_labels[_row].setStyleSheet('color:blue')
                self.from_id_id_labels[_row].mouseReleaseEvent = partial(self.labelClickEvent, _target_id)

            _freq = UwbNetwork.nodes[self.serial].calculate_frequency(self.from_id_frequency_deques[_target_id])
            self.from_id_count_labels[_row].setText('{:5d}'.format(self.from_id_count[_target_id]))
            self.from_id_freq_labels[_row].setText('{:5.1f}Hz'.format(_freq))

    def labelClickEvent(self, serial, e):
        self.sub_windows.update([(serial, PlotGyroV2SubWindow(serial, self))])

    def reset(self):
        for target_id in self.from_ids:
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
        for target_id in self.sub_windows:
            self.sub_windows[target_id].reset()
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]


class PlotGyroV2SubWindow(pg.GraphicsWindow):
    def __init__(self, serial, parent):

        pg.GraphicsWindow.__init__(self)
        self.setWindowTitle('CUWB Monitor - Gyro V2 Plot ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(1200, 800)
        self.parent = parent

        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)

        self.x_azimuth = 0
        self.y_azimuth = 0
        self.z_azimuth = 0
        self.last_azimuth_update = time.time()

        self.graph = self.addPlot(title='GyroScope XYZ', row=0, col=0, colspan=3)
        self.graph.setYRange(-15, 15)
        self.graph.showGrid(x=True, y=True)

        self.legend = self.graph.addLegend()
        self.plot_x = self.graph.plot(name='X', pen=pg.mkPen('r', width=2))
        self.plot_y = self.graph.plot(name='Y', pen=pg.mkPen('g', width=2))
        self.plot_z = self.graph.plot(name='Z', pen=pg.mkPen('b', width=2))

        self.x_direction_graph = self.addPlot(title='XY Rotation', row=1, col=0, colspan=1)
        self.x_direction_graph.addLine(x=0, pen=0.2)
        self.x_direction_graph.addLine(y=0, pen=0.2)
        for r in range(2,20,2):
            _circle = pg.QtGui.QGraphicsEllipseItem(-r,-r,r * 2,r * 2)
            _circle.setPen(pg.mkPen(0.2))
            self.x_direction_graph.addItem(_circle)
        self.x_direction_arrow = pg.ArrowItem(angle=90, tipAngle=30, headLen=40, tailLen=150, tailWidth=5, brush='r', pen={'color':'r', 'width':1})
        self.x_direction_graph.addItem(self.x_direction_arrow)
        self.x_direction_arrow.setPos(0,20)
        self.x_direction_text = pg.TextItem(text="", color='w', anchor=(0,0))
        self.x_direction_graph.addItem(self.x_direction_text)

        self.y_direction_graph = self.addPlot(title='XZ Rotation', row=1, col=1, colspan=1)
        self.y_direction_graph.addLine(x=0, pen=0.2)
        self.y_direction_graph.addLine(y=0, pen=0.2)
        for r in range(2,20,2):
            _circle = pg.QtGui.QGraphicsEllipseItem(-r,-r,r * 2,r * 2)
            _circle.setPen(pg.mkPen(0.2))
            self.y_direction_graph.addItem(_circle)
        self.y_direction_arrow = pg.ArrowItem(angle=90, tipAngle=30, headLen=40, tailLen=150, tailWidth=5, brush='g', pen={'color':'g', 'width':1})
        self.y_direction_graph.addItem(self.y_direction_arrow)
        self.y_direction_arrow.setPos(0, 20)
        self.y_direction_text = pg.TextItem(text="", color='w', anchor=(0,0))
        self.y_direction_graph.addItem(self.y_direction_text)


        self.z_direction_graph = self.addPlot(title='YZ Rotation', row=1, col=2, colspan=1)
        self.z_direction_graph.addLine(x=0, pen=0.2)
        self.z_direction_graph.addLine(y=0, pen=0.2)
        for r in range(2, 20, 2):
            _circle = pg.QtGui.QGraphicsEllipseItem(-r,-r,r * 2,r * 2)
            _circle.setPen(pg.mkPen(0.2))
            self.z_direction_graph.addItem(_circle)
        self.z_direction_arrow = pg.ArrowItem(angle=90, tipAngle=30, headLen=40, tailLen=150, tailWidth=5, brush='b', pen={'color':'b', 'width':1})
        self.z_direction_graph.addItem(self.z_direction_arrow)
        self.z_direction_arrow.setPos(0, 20)
        self.z_direction_text = pg.TextItem(text="", color='w', anchor=(0,0))
        self.z_direction_graph.addItem(self.z_direction_text)

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.running = False
            self.close()
            return

        if len(self.t_data) == 0: return

        self.plot_x.setData(self.t_data, self.x_data)
        self.plot_y.setData(self.t_data, self.y_data)
        self.plot_z.setData(self.t_data, self.z_data)

        # _current_time = time.time()
        _current_time = self.t_data[-1]

        self.x_azimuth -= np.mean(np.array(self.x_data)[-20:]) * (_current_time - self.last_azimuth_update)
        x_azimuth_display = (360 - self.x_azimuth + 90) % 360
        self.x_direction_arrow.setRotation((90 - x_azimuth_display) % 360)
        self.x_direction_arrow.setPos(20.0 * np.cos(np.radians(x_azimuth_display)), 20.0 * np.sin(np.radians(x_azimuth_display)))
        self.x_direction_graph.setXRange(-20, 20)
        self.x_direction_graph.setYRange(-20, 20)
        self.x_direction_text.setText("{:0.2f}".format(self.x_azimuth % 360))

        self.y_azimuth -= np.mean(np.array(self.y_data)[-20:]) * (_current_time - self.last_azimuth_update)
        y_azimuth_display = (360 - self.y_azimuth + 90) % 360
        self.y_direction_arrow.setRotation((90 - y_azimuth_display) % 360)
        self.y_direction_arrow.setPos(20.0 * np.cos(np.radians(y_azimuth_display)), 20.0 * np.sin(np.radians(y_azimuth_display)))
        self.y_direction_graph.setXRange(-20, 20)
        self.y_direction_graph.setYRange(-20, 20)
        self.y_direction_text.setText("{:0.2f}".format(self.y_azimuth % 360))

        self.z_azimuth -= np.mean(np.array(self.z_data)[-20:]) * (_current_time - self.last_azimuth_update)
        z_azimuth_display = (360 - self.z_azimuth + 90) % 360
        self.z_direction_arrow.setRotation((90 - z_azimuth_display) % 360)
        self.z_direction_arrow.setPos(20.0 * np.cos(np.radians(z_azimuth_display)), 20.0 * np.sin(np.radians(z_azimuth_display)))
        self.z_direction_graph.setXRange(-20, 20)
        self.z_direction_graph.setYRange(-20, 20)
        self.z_direction_text.setText("{:0.2f}".format(self.z_azimuth % 360))

        self.last_azimuth_update = _current_time

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

        self.x_azimuth = 0
        self.y_azimuth = 0
        self.z_azimuth = 0
        self.last_azimuth_update = time.time()
