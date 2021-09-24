# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from cdp import MagnetometerV2
from network_objects import *
from rolling_std import *
from settings import *


class PlotMagnetometerV2(QtGui.QMainWindow):
    type = MagnetometerV2.type

    def __init__(self, serial):

        QtGui.QMainWindow.__init__(self)

        self.central = QtGui.QWidget()  #This will be our central widget
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Magnetometer V2 Devices ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtGui.QGridLayout()

        self.sub_windows = dict([])
        self.running = True

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

        self.updateLabels()

        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        self.resize(400, 50)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        self.updateLabels()

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)

    def updateLabels(self):
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

                self.sub_windows[_target_id].updateData(_x, _y, _z, _time)

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
        self.sub_windows.update([(serial, PlotMagnetV2SubWindow(serial, self))])

    def reset(self):
        for target_id in self.from_ids:
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
        for target_id in self.sub_windows:
            self.sub_windows[target_id].reset()
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]


class PlotMagnetV2SubWindow(pg.GraphicsWindow):

    def __init__(self, serial, parent):

        pg.GraphicsWindow.__init__(self)
        self.setWindowTitle('CUWB Monitor - Magnetometer V2 Plot ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.resize(1200, 1025)
        self.parent = parent

        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)
        self.magnitude_data = deque([], TRAIL_LENGTH)

        self.avg_magnitude = RollingStandardDeviationDeque(200)

        self.graph = self.addPlot(title='Magnetometer XYZ', row=0, col=0, colspan=3)
        self.graph.setYRange(-100, 100)
        self.graph.showGrid(x=True, y=True)

        self.legend = self.graph.addLegend()
        self.plot_x = self.graph.plot(name='X', pen=pg.mkPen('r', width=2))
        self.plot_y = self.graph.plot(name='Y', pen=pg.mkPen('y', width=2))
        self.plot_z = self.graph.plot(name='Z', pen=pg.mkPen('b', width=2))
        self.plot_mag = self.graph.plot(name='MagXYZ', pen=pg.mkPen('w', width=1))

        self.xy_graph = self.addPlot(title='XY', row=2, col=0, colspan=1)
        self.xy_direction_graph = self.addPlot(title='XY Angle', row=1, col=0, colspan=1)
        self.xy_direction_arrow = pg.ArrowItem(angle=90, tipAngle=30, headLen=40, tailLen=150, tailWidth=5, brush='r', pen={'color':(255,70,0), 'width':1})
        self.xy_direction_text = pg.TextItem(text="", color='w', anchor=(0,0))
        self.addTwoDimensionalPlots(self.xy_graph, self.xy_direction_graph, self.xy_direction_arrow, self.xy_direction_text)
        self.plot_xy = self.xy_graph.plot(name='XY', symbol='o', symbolSize=4, pen=None, symbolPen=pg.mkPen((255,70,0), width=2))

        self.xz_graph = self.addPlot(title='XZ', row=2, col=1, colspan=1)
        self.xz_direction_graph = self.addPlot(title='XZ Angle', row=1, col=1, colspan=1)
        self.xz_direction_arrow = pg.ArrowItem(angle=90, tipAngle=30, headLen=40, tailLen=150, tailWidth=5, brush='b', pen={'color':(160,32,240), 'width':1})
        self.xz_direction_text = pg.TextItem(text="", color='w', anchor=(0,0))
        self.addTwoDimensionalPlots(self.xz_graph, self.xz_direction_graph, self.xz_direction_arrow, self.xz_direction_text)
        self.plot_xz = self.xz_graph.plot(name='XZ', symbol='o', symbolSize=4, pen=None, symbolPen=pg.mkPen((160,32,240), width=2))

        self.yz_graph = self.addPlot(title='YZ', row=2, col=2, colspan=1)
        self.yz_direction_graph = self.addPlot(title='YZ Angle', row=1, col=2, colspan=1)
        self.yz_direction_arrow = pg.ArrowItem(angle=90, tipAngle=30, headLen=40, tailLen=150, tailWidth=5, brush='g', pen={'color':'g', 'width':1})
        self.yz_direction_text = pg.TextItem(text="", color='w', anchor=(0,0))
        self.addTwoDimensionalPlots(self.yz_graph, self.yz_direction_graph, self.yz_direction_arrow, self.yz_direction_text)
        self.plot_yz = self.yz_graph.plot(name='YZ', symbol='o', symbolSize=4, pen=None, symbolPen=pg.mkPen('g', width=2))

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

    def addTwoDimensionalPlots(self, graph, direction_graph, direction_arrow, direction_text):
        graph.setAspectLocked()
        graph.showGrid(x=True, y=True)
        direction_graph.setXRange(-20, 20)
        direction_graph.setYRange(-20, 20)
        direction_graph.setAspectLocked()
        direction_graph.addLine(x=0, pen=0.2)
        direction_graph.addLine(y=0, pen=0.2)
        for r in range(2,20,2):
            _circle = pg.QtGui.QGraphicsEllipseItem(-r,-r,r * 2,r * 2)
            _circle.setPen(pg.mkPen(0.2))
            direction_graph.addItem(_circle)
        direction_graph.addItem(direction_arrow)
        direction_arrow.setPos(0, 20)
        direction_graph.addItem(direction_text)

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.close()
            return

        self.plot_x.setData(self.t_data, self.x_data)
        self.plot_y.setData(self.t_data, self.y_data)
        self.plot_z.setData(self.t_data, self.z_data)
        self.plot_mag.setData(self.t_data, self.magnitude_data)

        self.plot_xy.setData(self.x_data, self.y_data)
        self.plot_xz.setData(self.x_data, self.z_data)
        self.plot_yz.setData(self.y_data, self.z_data)

        #Average last 8 values to smooth output
        if len(self.t_data) < 9 or np.isnan(self.avg_magnitude.get_meanvalue()): return               #Make sure there is enough data to work with
        _idx = np.where(np.abs(np.array(self.magnitude_data)[-8:] - self.avg_magnitude.get_meanvalue()) < 2.5)[0] -8
        if not _idx.any():
            _idx =np.array([-8, -7, -6, -5, -4, -3, -2, -1])
        _y_mean = np.nanmean(np.array(self.y_data)[_idx])
        _x_mean = np.nanmean(np.array(self.x_data)[_idx])
        _z_mean = np.nanmean(np.array(self.z_data)[_idx])

        self.findDirectionArrow(_x_mean, _y_mean, self.xy_direction_arrow, self.xy_direction_text)
        self.findDirectionArrow(_x_mean, _z_mean, self.xz_direction_arrow, self.xz_direction_text)
        self.findDirectionArrow(_y_mean, _z_mean, self.yz_direction_arrow, self.yz_direction_text)

    def findDirectionArrow(self, mean1, mean2, direction_arrow, direction_text):
        azimuth = (-np.arctan2(mean1, mean2)) % (2.0 * np.pi)
        azimuth_display = ((2 * np.pi - azimuth) + (np.pi/2)) % (2.0 * np.pi)
        direction_arrow.setRotation((90 - np.degrees(azimuth_display)) % 360)
        direction_arrow.setPos(20.0 * np.cos(azimuth_display), 20.0 * np.sin(azimuth_display))
        direction_text.setText("{:0.2f}".format(np.degrees(azimuth) % 360))

    def updateData(self, x, y, z, t):

        _magnitude = np.linalg.norm([x,y,z])
        self.x_data.append(x)
        self.y_data.append(y)
        self.z_data.append(z)
        self.t_data.append(t)
        self.magnitude_data.append(_magnitude)

        if _magnitude > 8 and _magnitude < 35:
            self.avg_magnitude.push(_magnitude)

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def reset(self):
        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)
        self.magnitude_data = deque([], TRAIL_LENGTH)
