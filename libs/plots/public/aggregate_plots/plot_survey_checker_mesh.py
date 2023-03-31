# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

#System libraries
import numpy as np
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
#from pyqtgraph.opengl import shaders
from OpenGL.GL import *

#Local Libraries
from network_objects import *
from settings import *
from cdp import CiholasSerialNumber, DistanceV2, DeviceActivityState

class PlotSurveyCheckerMesh(QtWidgets.QMainWindow):
    type = 'SurveyCheckerMesh'
    #18 is the value for ShareOpenGLContexts and is mandatory in order for multiple GLViewWidgets to exist and have scatter data plot correctly.
    #Opening this window a second time is considered having multiple GLViewWidgets which makes this line a necessity.
    QtCore.QCoreApplication.setAttribute(18)

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        
        self.anchor_selector = QtWidgets.QComboBox()
        self.anchor_selector.addItem("-")
        self.anchor_selector.currentTextChanged.connect(self.updateModel)
        self.grid_layout.addWidget(self.anchor_selector, 0, 0)
        self.grid_layout.addWidget(QtWidgets.QLabel("Minimum Error to Show:"), 0, 1)
        self.minimum_editor = QtWidgets.QLineEdit()
        self.minimum_editor.editingFinished.connect(self.setMinBound)
        self.grid_layout.addWidget(self.minimum_editor, 0, 2)
        self.grid_layout.addWidget(QtWidgets.QLabel("Maximum Error to Show:"), 0, 3)
        self.maximum_editor = QtWidgets.QLineEdit()
        self.maximum_editor.editingFinished.connect(self.setMaxBound)
        self.grid_layout.addWidget(self.maximum_editor, 0, 4)
        self.toggle_labels = QtWidgets.QCheckBox("Hide Labels")
        self.toggle_labels.stateChanged.connect(self.updateModel)
        self.grid_layout.addWidget(self.toggle_labels, 0, 5)
        self.toggle_grid = QtWidgets.QCheckBox("Hide XY Plane")
        self.toggle_grid.stateChanged.connect(self.toggleGrid)
        self.grid_layout.addWidget(self.toggle_grid, 0, 6)
        
        only_double = boundValidator()
        self.minimum_editor.setValidator(only_double)
        self.maximum_editor.setValidator(only_double)

        self.view = gl.GLViewWidget()
        self.view.makeCurrent()
        self.grid_layout.addWidget(self.view, 1, 0, 1, 7)
        self.view.show()
        self.floor = gl.GLGridItem()
        self.view.addItem(self.floor)

        self.setWindowTitle("CUWB Monitor- Survey Checker Mesh")
        width = 900
        height = 900
        self.resize(width, height)

        self.anchor_mesh = gl.GLScatterPlotItem()
        self.view.addItem(self.anchor_mesh)
        self.anchor_labels = []
        self.lines = []

        self.prev_das_count = 0
        self.prev_dv2_count = 0
        self.distances = {}
        self.locations = {}
        self.anchor_names = {}
        self.min_bound = 0
        self.max_bound = 0
        self.use_min_bound = False
        self.use_max_bound = False
        self.MM_TO_M = 1000
        self.PACKET_TRAIL_LENGTH = 20

        self.running = True
        self.timer = self.startTimer(5000)
        self.updateModel()

    def updateModel(self):
        for node_id in UwbNetwork.nodes.keys():
            if DistanceV2.type in UwbNetwork.nodes[node_id].cdp_pkts_count:
                curr_count = UwbNetwork.nodes[node_id].cdp_pkts_count[DistanceV2.type]
                if curr_count - self.prev_dv2_count > 1000: self.prev_dv2_count = curr_count - 1000
                while self.prev_dv2_count < curr_count:
                    index = self.prev_dv2_count - curr_count
                    packet = UwbNetwork.nodes[node_id].cdp_pkts[DistanceV2.type][index]

                    serial_1 = packet.serial_number_1
                    if not serial_1.as_int in self.locations.keys():
                        self.locations[serial_1.as_int] = [deque([], self.PACKET_TRAIL_LENGTH),
                                                           deque([], self.PACKET_TRAIL_LENGTH),
                                                           deque([], self.PACKET_TRAIL_LENGTH)]
                        self.anchor_names[serial_1.as_int] = str(serial_1)
                        self.anchor_selector.addItem(str(serial_1))

                    serial_2 = packet.serial_number_2
                    if not serial_2.as_int in self.locations.keys():
                        self.locations[serial_2.as_int] = [deque([], self.PACKET_TRAIL_LENGTH),
                                                           deque([], self.PACKET_TRAIL_LENGTH),
                                                           deque([], self.PACKET_TRAIL_LENGTH)]
                        self.anchor_names[serial_2.as_int] = str(serial_2)
                        self.anchor_selector.addItem(str(serial_2))

                    #A tuple index of format (lower serial num, higher serial num) is used so that distance data for a pair only needs to be stored once.
                    if serial_1.as_int < serial_2.as_int:
                        anchor_pair = (serial_1.as_int, serial_2.as_int)
                    else:
                        anchor_pair = (serial_2.as_int, serial_1.as_int)
                    self.distances[anchor_pair] = deque([], self.PACKET_TRAIL_LENGTH)
                    self.distances[anchor_pair].append(packet.distance/1000)
                    self.prev_dv2_count += 1

            if DeviceActivityState.type in UwbNetwork.nodes[node_id].cdp_pkts_count:
                curr_count = UwbNetwork.nodes[node_id].cdp_pkts_count[DeviceActivityState.type]
                if curr_count - self.prev_das_count > 1000: self.prev_das_count = curr_count - 1000
                while self.prev_das_count < curr_count:
                    index = self.prev_das_count - curr_count
                    packet = UwbNetwork.nodes[node_id].cdp_pkts[DeviceActivityState.type][index]
                    serial = CiholasSerialNumber(packet.serial_number).as_int
                    if serial in self.locations.keys():
                        self.locations[serial][0].append(packet.x/1000)
                        self.locations[serial][1].append(packet.y/1000)
                        self.locations[serial][2].append(packet.z/1000)
                    self.prev_das_count += 1

        for old_label in self.anchor_labels:
            self.view.removeItem(old_label)
        self.anchor_labels.clear()
        
        for old_line in self.lines:
            self.view.removeItem(old_line)
        self.lines.clear()

        anchor_places = []
        update = False
        for serial in self.locations.keys():
            if len(self.locations[serial][0]) != 0:
                update = True
                x = np.mean(self.locations[serial][0])
                y = np.mean(self.locations[serial][1])
                z = np.mean(self.locations[serial][2])
                position = np.array([x,y,z])
                anchor_places.append(position)
                if not self.toggle_labels.isChecked():
                    text_item = gl.GLTextItem(pos = position, text = self.anchor_names[serial])
                    self.anchor_labels.append(text_item)
                    self.view.addItem(text_item)
        if update:
            self.anchor_mesh.setData(pos = np.array(anchor_places), color = (0.2,0.2,1,1), size = 1, pxMode = False)

        for anchor_pair in self.distances.keys():
            if anchor_pair[0] in self.locations.keys() and anchor_pair[1] in self.locations.keys():
                selected_anchor = self.anchor_selector.currentText()
                if selected_anchor=="-" or selected_anchor==str(CiholasSerialNumber(anchor_pair[0])) or selected_anchor==str(CiholasSerialNumber(anchor_pair[1])):
                    anchor_1_data = self.locations[anchor_pair[0]]
                    anchor_2_data = self.locations[anchor_pair[1]]
                    #Since the coords are set at the same time as long as x has a data point, the rest will.
                    if len(anchor_1_data[0])!=0 and len(anchor_2_data[0])!=0:
                        x1 = np.mean(anchor_1_data[0])
                        x2 = np.mean(anchor_2_data[0])
                        y1 = np.mean(anchor_1_data[1])
                        y2 = np.mean(anchor_2_data[1])
                        z1 = np.mean(anchor_1_data[2])
                        z2 = np.mean(anchor_2_data[2])
                        mag_distance = np.linalg.norm([x2-x1, y2-y1, z2-z1])
                        distance_error = np.mean(self.distances[anchor_pair])-mag_distance
                        distance_error_ratio = np.mean(self.distances[anchor_pair])/mag_distance
                        point1 = np.array([x1+(x2-x1)/2-((x2-x1)*distance_error_ratio*.5),
                                           y1+(y2-y1)/2-((y2-y1)*distance_error_ratio*.5),
                                           z1+(z2-z1)/2-((z2-z1)*distance_error_ratio*.5)])
                        point2 = np.array([x1+(x2-x1)/2+((x2-x1)*distance_error_ratio*.5),
                                           y1+(y2-y1)/2+((y2-y1)*distance_error_ratio*.5),
                                           z1+(z2-z1)/2+((z2-z1)*distance_error_ratio*.5)])
                        if (not self.use_min_bound or abs(distance_error) > self.min_bound) and (not self.use_max_bound or abs(distance_error) < self.max_bound):
                            if abs(distance_error) < 0.25:
                                line = gl.GLLinePlotItem(pos = np.array([point1, point2]), color = (0.2+2*distance_error, 1, 0.2, 0.3), width = 1, antialias = True, mode='lines')
                            elif abs(distance_error) < 1:
                                line = gl.GLLinePlotItem(pos = np.array([point1, point2]), color = (1, 1-0.4*distance_error, 0.2, 0.5), width = 1, antialias = True, mode='lines')
                            else:
                                line = gl.GLLinePlotItem(pos = np.array([point1, point2]), color = (1, 0.1, 0.1, 0.6), width = 3, antialias = True, mode='lines')
                            self.lines.append(line)
                            self.view.addItem(line)

    def setMinBound(self):
        if self.minimum_editor.text() == "":
            self.use_min_bound = False
        else:
            try:
                self.min_bound = abs(float(self.minimum_editor.text()))
                self.use_min_bound = True
            except ValueError:
                print("Bounds must be a float")
        self.updateModel()

    def setMaxBound(self):
        if self.maximum_editor.text() == "":
            self.use_max_bound = False
        else:
            try:
                self.max_bound = abs(float(self.maximum_editor.text()))
                self.use_max_bound = True
            except ValueError:
                print("Bounds must be a float")
        self.updateModel()

    def toggleGrid(self):
        if self.toggle_grid.isChecked(): self.view.removeItem(self.floor)
        else: self.view.addItem(self.floor)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        if self.running:
            self.updateModel()
        else:
            self.killTimer(self.timer)
            self.close()

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)
        self.close()

    def reset(self):
        self.prev_das_count = 0
        self.prev_dv2_count = 0
        self.locations.clear()
        self.distances.clear()
        self.anchor_labels.clear()
        self.lines.clear()
        self.view.clear()
        self.anchor_selector.blockSignals(True)
        self.anchor_selector.clear()
        self.anchor_selector.addItem("-")
        self.anchor_selector.blockSignals(False)
        if not self.toggle_grid.isChecked(): self.view.addItem(self.floor)
        self.anchor_mesh.setData(pos = np.array([np.nan, np.nan, np.nan]), color = (0.2,0.2,1,1), size = 1, pxMode = False)
        self.view.addItem(self.anchor_mesh)

class boundValidator(QtGui.QDoubleValidator):

    def __init__(self, *__args):
        super().__init__(*__args)

    def validate(self, input_num, length):
        if input_num == "":
            return QtGui.QValidator.Acceptable, input_num, length
        else:
            return QtGui.QDoubleValidator.validate(self, input_num, length)
