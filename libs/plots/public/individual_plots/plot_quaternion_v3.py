# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtWidgets, QtCore
from OpenGL.GL import *

# Local libraries
from cdp import QuaternionV3
from network_objects import *
from settings import *


class PlotQuaternionV3(QtWidgets.QMainWindow):
    type = QuaternionV3.type

    def __init__(self, serial):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()  #This will be our central widget
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Quaternion V3 Devices ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtWidgets.QGridLayout()
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
        self.killTimer(self.timer)
        self.running = False

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
                    self.grid_layout.addWidget(QtWidgets.QLabel("Print"), _row, _column + 3)
                self.id_total += 1

            self.from_id_count[_target_id] += 1

            if _target_id in self.from_ids:
                _row = np.where(self.from_ids==_target_id)[0][0]
                if self.from_id_enable_checks[_row].isChecked():
                    print(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size])

            if _target_id in self.sub_windows.keys():
                _x = (UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].x * 1.0) / (2.0**30)
                _y = (UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].y * 1.0) / (2.0**30)
                _w = (UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].w * 1.0) / (2.0**30)
                _z = (UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].z * 1.0) / (2.0**30)
                _time = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].network_time * TICK

                self.sub_windows[_target_id].update_data(_x, _y, _z, _w, _time)

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
        self.sub_windows.update([(serial, PlotQuatV3SubWindow(serial, self))])

    def reset(self):
        for target_id in self.from_ids:
            self.from_id_count[target_id] = 0
            self.from_id_frequency_deques[target_id] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
        for target_id in self.sub_windows:
            self.sub_windows[target_id].reset()
        self.previous_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]


class PlotQuatV3SubWindow(QtWidgets.QMainWindow):
    def __init__(self, serial, parent):

        QtWidgets.QMainWindow.__init__(self)
        self.show()
        self.setWindowTitle('CUWB Monitor - Quat V3 Plot ID: 0x{:08X}'.format(serial))
        self.serial = serial
        self.parent = parent

        self.central = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)

        length = 1000
        height = 1200
        self.resize(length, height)

        self.plotter = pg.GraphicsLayoutWidget(show=True)
        self.grid_layout.addWidget(self.plotter, 0, 0)
        self.graph = self.plotter.addPlot(title='Quaternion XYZ', row=0, col=0)
        self.graph.setYRange(-1.0, 1.0)
        self.graph.showGrid(x=True, y=True)

        self.legend = self.graph.addLegend()
        self.plot_x = self.graph.plot(name='X', pen=pg.mkPen('r', width=2))
        self.plot_y = self.graph.plot(name='Y', pen=pg.mkPen('g', width=2))
        self.plot_z = self.graph.plot(name='Z', pen=pg.mkPen('b', width=2))
        self.plot_w = self.graph.plot(name='W', pen=pg.mkPen('w', width=2))

        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.w_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)

        self.view = gl.GLViewWidget()
        self.grid_layout.addWidget(self.view, 1, 0)
        self.axes = cuwbAxisItem()
        self.view.addItem(self.axes)
        x, y, z = self.axes.size()
        xlabel = gl.GLTextItem(pos = np.array([x,0,0]), text = "X")
        self.view.addItem(xlabel)
        ylabel = gl.GLTextItem(pos = np.array([0,y,0]), text = "Y")
        self.view.addItem(ylabel)
        zlabel = gl.GLTextItem(pos = np.array([0,0,z]), text = "Z")
        self.view.addItem(zlabel)

        vertices = np.array([[2,1,0.5],
                             [2,-1,0.5],
                             [-2,-1,0.5],
                             [-2,1,0.5],
                             [2,1,-0.5],
                             [2,-1,-0.5],
                             [-2,-1,-0.5],
                             [-2,1,-0.5]])
        surfaces = np.array([[4,5,7], #Back
                             [5,6,7],
                             [4,0,7], #Top
                             [0,3,7],
                             [5,1,6], #Bottom
                             [1,2,6],
                             [0,1,4], #Right
                             [1,5,4],
                             [3,2,7], #Left
                             [2,6,7],
                             [0,1,3], #Front
                             [1,2,3]])
        colors = np.array([[1.0,0.2,0.2, 1],
                           [1.0,0.2,0.2, 1],
                           [0.2,1.0,0.2, 1],
                           [0.2,1.0,0.2, 1],
                           [0.2,0.2,1.0, 1],
                           [0.2,0.2,1.0, 1],
                           [0.2,1.0,1.0, 1],
                           [0.2,1.0,1.0, 1],
                           [1.0,0.2,1.0, 1],
                           [1.0,0.2,1.0, 1],
                           [1.0,1.0,0.2, 1],
                           [1.0,1.0,0.2, 1]])
        self.cube = gl.GLMeshItem(vertexes=vertices, faces=surfaces, faceColors=colors, smooth = False)
        self.view.addItem(self.cube)

        #Necessary lines for the 3d plotter and 2d plotter to simultaneously be in the window
        self.plotter.sizeHint =  lambda: QtCore.QSize(100,100)
        self.view.sizeHint = lambda: QtCore.QSize(100, 100)
        self.view.setSizePolicy(self.plotter.sizePolicy())

        self.theta = 0
        self.x_angle = 0
        self.y_angle = 0
        self.z_angle = 0

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.running = False
            self.close()
            return

        if len(self.t_data) < 2: return

        self.plot_x.setData(self.t_data, self.x_data)
        self.plot_y.setData(self.t_data, self.y_data)
        self.plot_z.setData(self.t_data, self.z_data)
        self.plot_w.setData(self.t_data, self.w_data)

        _current_time = self.t_data[-1]

    def update_data(self, x, y, z, w, t):
        self.x_data.append(x)
        self.y_data.append(y)
        self.z_data.append(z)
        self.w_data.append(w)
        self.t_data.append(t)

        self.cube.rotate(-self.theta, self.x_angle, self.y_angle, self.z_angle)
        if w==1 or w==-1:
            self.theta = 0
            self.x_angle = 0
            self.y_angle = 0
            self.z_angle = 0
        else:
            new_x = x/(1-w**2)**(1/2)
            new_y = y/(1-w**2)**(1/2)
            new_z = z/(1-w**2)**(1/2)
            #If the shape attempts to rotate on an axis of 0,0,0 the shape will shrink. This check prevents that from happening.
            if not (new_x == 0.0 and new_y == 0.0 and new_z == 0.0):
                self.theta = 2*np.degrees(np.arccos(w))
                self.x_angle = new_x
                self.y_angle = new_y
                self.z_angle = new_z
                self.cube.rotate(self.theta, self.x_angle, self.y_angle, self.z_angle)

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def reset(self):
        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.w_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)

        self.cube.rotate(-self.theta, self.x_angle, self.y_angle, self.z_angle)
        self.theta = 0
        self.x_angle = 0
        self.y_angle = 0
        self.z_angle = 0

class cuwbAxisItem(gl.GLAxisItem):
    def __init__(self):
        gl.GLAxisItem.__init__(self)
        self.setSize(5,5,5)

    def paint(self):
        self.setupGLState()
        if self.antialias:
            glEnable(GL_LINE_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

        glBegin(GL_LINES)
        x, y, z = self.size()
        
        glColor4f(0,0,1, .6)
        glVertex3f(0,0,0)
        glVertex3f(0,0,z)

        glColor4f(0,1,0, .6)
        glVertex3f(0,0,0)
        glVertex3f(0,y,0)

        glColor4f(1,0,0, .6)
        glVertex3f(0,0,0)
        glVertex3f(x,0,0)
        glEnd()
