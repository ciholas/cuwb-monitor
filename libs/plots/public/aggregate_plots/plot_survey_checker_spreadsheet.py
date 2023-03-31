# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

#System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets

#Local Libraries
from network_objects import *
from settings import *
from cdp import CiholasSerialNumber, DistanceV2, DeviceActivityState

class PlotSurveyCheckerSpreadsheet(QtWidgets.QMainWindow):
    type = 'SurveyCheckerSpreadsheet'

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)

        self.setWindowTitle("CUWB Monitor- Survey Checker Spreadsheet")

        self.row_col_count = 0
        self.distance_error_table = QtWidgets.QTableWidget()
        self.grid_layout.addWidget(self.distance_error_table, 0, 0)
        self.locations = {}
        self.distances = {}
        self.prev_das_count = 0
        self.prev_dv2_count = 0
        self.MM_TO_M = 1000
        self.PACKET_TRAIL_LENGTH = 20

        self.running = True
        self.timer = self.startTimer(1000)
        self.updateTable()

        border_length = 100
        border_width = 40
        cell_length = 110
        cell_width = 40
        self.resize(border_length + (cell_length * len(self.distances)), border_width + (cell_width * len(self.distances)))

    def updateTable(self):
        for node_id in UwbNetwork.nodes.keys():
            if DistanceV2.type in UwbNetwork.nodes[node_id].cdp_pkts:
                curr_count = UwbNetwork.nodes[node_id].cdp_pkts_count[DistanceV2.type]
                if curr_count - self.prev_dv2_count > 1000: self.prev_dv2_count = curr_count - 1000
                greatest = -1
                while self.prev_dv2_count < curr_count:
                    index = self.prev_dv2_count - curr_count
                    packet = UwbNetwork.nodes[node_id].cdp_pkts[DistanceV2.type][index]

                    serial_1 = packet.serial_number_1
                    if not serial_1.as_int in self.locations.keys():
                        self.addAnchor(serial_1)

                    serial_2 = packet.serial_number_2
                    if not serial_2.as_int in self.locations.keys():
                        self.addAnchor(serial_2)

                    #A tuple index of format (lower serial num, higher serial num) is used so that distance data for a pair only needs to be stored once.
                    if serial_1.as_int < serial_2.as_int:
                        anchor_pair = (serial_1.as_int, serial_2.as_int)
                    else:
                        anchor_pair = (serial_2.as_int, serial_1.as_int)
                    if not anchor_pair in self.distances.keys():
                        self.distances[anchor_pair] = deque([], self.PACKET_TRAIL_LENGTH)
                    self.distances[anchor_pair].append(packet.distance/self.MM_TO_M)
                    self.prev_dv2_count += 1

            if DeviceActivityState.type in UwbNetwork.nodes[node_id].cdp_pkts:
                curr_count = UwbNetwork.nodes[node_id].cdp_pkts_count[DeviceActivityState.type]
                if curr_count - self.prev_das_count > 1000: self.prev_das_count = curr_count - 1000
                while self.prev_das_count < curr_count:
                    index = self.prev_das_count - curr_count
                    packet = UwbNetwork.nodes[node_id].cdp_pkts[DeviceActivityState.type][index]
                    serial = CiholasSerialNumber(packet.serial_number).as_int
                    if serial in self.locations.keys():
                        self.locations[serial][1].append(packet.x/self.MM_TO_M)
                        self.locations[serial][2].append(packet.y/self.MM_TO_M)
                        self.locations[serial][3].append(packet.z/self.MM_TO_M)
                    self.prev_das_count += 1

        for anchor_pair in self.distances.keys():
            #Make sure both anchors of the pair are in locations
            if anchor_pair[0] in self.locations and anchor_pair[1] in self.locations:
                anchor_1_data = self.locations[anchor_pair[0]]
                anchor_2_data = self.locations[anchor_pair[1]]
                #Since the coords are set at the same time as long as x has a data point, the rest will.
                if len(anchor_1_data[1])!=0 and len(anchor_2_data[1])!=0:
                    location_1 = self.distance_error_table.item(anchor_1_data[0], anchor_2_data[0])
                    location_2 = self.distance_error_table.item(anchor_2_data[0], anchor_1_data[0])
                    x1 = np.mean(anchor_1_data[1])
                    x2 = np.mean(anchor_2_data[1])
                    y1 = np.mean(anchor_1_data[2])
                    y2 = np.mean(anchor_2_data[2])
                    z1 = np.mean(anchor_1_data[3])
                    z2 = np.mean(anchor_2_data[3])
                    mag_distance = np.linalg.norm([x2-x1, y2-y1, z2-z1])
                    distance_error = np.mean(self.distances[anchor_pair]) - mag_distance

                    if distance_error < 0.25 and distance_error > -0.25:
                        #Using 600 * distance_error makes it to where a color can have an R value of 0-150.
                        brush = QtGui.QBrush(QtGui.QColor(600*abs(distance_error), 230, 0))
                        location_1.setBackground(brush)
                        location_2.setBackground(brush)
                    elif distance_error < 1 and distance_error > -1:
                        #Using 250-80*distance_error makes it to where the color can have a G value of 150-230.
                        brush = QtGui.QBrush(QtGui.QColor(230, 250-80*abs(distance_error), 0))
                        location_1.setBackground(brush)
                        location_2.setBackground(brush)
                    else:
                        brush = QtGui.QBrush(QtGui.QColor(230, 0, 0))
                        location_1.setBackground(brush)
                        location_2.setBackground(brush)
                    error_text = str(round(distance_error,2))
                    location_1.setText(error_text)
                    location_1.setTextAlignment(QtCore.Qt.AlignCenter)
                    location_2.setText(error_text)
                    location_2.setTextAlignment(QtCore.Qt.AlignCenter)

    def addAnchor(self, serial):
        self.row_col_count += 1
        new_item_1 = QtWidgets.QTableWidgetItem(str(serial))
        new_item_2 = QtWidgets.QTableWidgetItem(str(serial))
        self.distance_error_table.setRowCount(self.row_col_count)
        self.distance_error_table.setColumnCount(self.row_col_count)
        #list held in self.locations takes this format: (index, x coords, y coords, z coords)
        self.locations[serial.as_int] = [self.row_col_count-1,
                                         deque([], self.PACKET_TRAIL_LENGTH),
                                         deque([], self.PACKET_TRAIL_LENGTH),
                                         deque([], self.PACKET_TRAIL_LENGTH)]
        for idx in range(self.row_col_count):
            self.distance_error_table.setItem(self.row_col_count-1, idx, QtWidgets.QTableWidgetItem("-"))
            self.distance_error_table.item(self.row_col_count-1, idx).setTextAlignment(QtCore.Qt.AlignCenter)
            self.distance_error_table.setItem(idx, self.row_col_count-1, QtWidgets.QTableWidgetItem("-"))
            self.distance_error_table.item(idx, self.row_col_count-1).setTextAlignment(QtCore.Qt.AlignCenter)
        self.distance_error_table.setItem(self.row_col_count-1, self.row_col_count-1, QtWidgets.QTableWidgetItem("-"))
        self.distance_error_table.item(self.row_col_count-1, self.row_col_count-1).setTextAlignment(QtCore.Qt.AlignCenter)
        self.distance_error_table.setVerticalHeaderItem(self.row_col_count-1, new_item_1)
        self.distance_error_table.setHorizontalHeaderItem(self.row_col_count-1, new_item_2)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        if self.running:
            self.updateTable()
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
        for row in range(self.row_col_count):
            for col in range(self.row_col_count):
                if row != col:
                    self.distance_error_table.setItem(row, col, QtWidgets.QTableWidgetItem("-"))
                    self.distance_error_table.item(self.row_col_count-1, self.row_col_count-1).setTextAlignment(QtCore.Qt.AlignCenter)
        self.locations.clear()
        self.distances.clear()
        self.row_col_count = 0
        self.distance_error_table.setRowCount(self.row_col_count)
        self.distance_error_table.setColumnCount(self.row_col_count)
