# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

#System Libraries
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtWidgets, QtCore
from functools import partial

#Local Libraries
from device_data_items import PersistentPropertyGetPropertyResponse
from network_objects import *
from settings import *

class PlotPersistentPropertyGetPropertyResponse(QtWidgets.QMainWindow):
    type = PersistentPropertyGetPropertyResponse.type

    def __init__(self, device):
        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QScrollArea()
        self.central.setWidgetResizable(True)
        self.central_inner_widget = QtWidgets.QWidget()
        self.grid_main = QtWidgets.QGridLayout()
        self.setWindowTitle("CUWB Monitor- Persistent Property Get Types Response Device: 0x{:08X}".format(device.id))
        self.device = device
        self.running = True

        length = 700
        width = 200
        self.resize(length, width)

        self.prev_count = self.device.counts[PersistentPropertyGetPropertyResponse.type] - len(self.device.packets[PersistentPropertyGetPropertyResponse.type])
        self.present_properties = []
        self.labels = []
        self.curr_row = 0

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.updateLabels()

        self.central_inner_widget.setLayout(self.grid_main)
        self.central.setWidget(self.central_inner_widget)
        self.setCentralWidget(self.central)

    def updateLabels(self):
        curr_count = self.device.counts[PersistentPropertyGetPropertyResponse.type]
        if curr_count - self.prev_count > 1000: self.prev_count = curr_count - 1000
        while self.prev_count < curr_count:
            index = self.prev_count - curr_count
            packet = self.device.packets[PersistentPropertyGetPropertyResponse.type][index]
            if not packet.property_id in self.present_properties:
                self.present_properties.append(packet.property_id)
                self.addPropertyLabels()
            #Every 4 entries in self.labels is a new property
            property_idx = 4 * self.present_properties.index(packet.property_id)
            self.labels[property_idx].setText("0x{:04x}".format(packet.property_id))
            self.labels[property_idx+1].setText(str(packet.offset))
            self.labels[property_idx+2].setText(str(packet.total_size))
            unformatted_data = (packet.data).hex()
            formatted_data = ""
            while len(unformatted_data) > 1:
                formatted_data += unformatted_data[:2] + " "
                unformatted_data = unformatted_data[2:]
            self.labels[property_idx+3].setText(formatted_data)
            self.prev_count += 1

    def addPropertyLabels(self):
        spacer_size = 10

        info_row_widget = QtWidgets.QWidget()
        info_row_layout = QtWidgets.QGridLayout()
        info_row_layout.setHorizontalSpacing(0)
        info_row_layout.setVerticalSpacing(0)
        info_row_layout.setSpacing(0)
        info_row_widget.setLayout(info_row_layout)
        info_row_layout.addWidget(QtWidgets.QLabel("Property ID: "), 0, 0)
        pid_label = QtWidgets.QLabel("")
        self.labels.append(pid_label)
        info_row_layout.addWidget(pid_label, 0, 1)
        info_row_layout.addItem(QtWidgets.QSpacerItem(spacer_size, 0), 0, 2)
        info_row_layout.addWidget(QtWidgets.QLabel("Offset: "), 0, 3)
        offset_label = QtWidgets.QLabel("")
        self.labels.append(offset_label)
        info_row_layout.addWidget(offset_label, 0, 4)
        info_row_layout.addItem(QtWidgets.QSpacerItem(spacer_size, 0), 0, 5)
        info_row_layout.addWidget(QtWidgets.QLabel("Total Size: "), 0, 6)
        size_label = QtWidgets.QLabel("")
        self.labels.append(size_label)
        info_row_layout.addWidget(size_label, 0, 7)
        info_row_layout.addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 8)
        self.grid_main.addWidget(info_row_widget, self.curr_row, 0)
        self.curr_row += 1

        data_row_widget = QtWidgets.QWidget()
        data_row_layout = QtWidgets.QGridLayout()
        data_row_layout.setHorizontalSpacing(0)
        data_row_layout.setVerticalSpacing(0)
        data_row_layout.setSpacing(0)
        data_row_widget.setLayout(data_row_layout)
        data_row_layout.addWidget(QtWidgets.QLabel("Data: "), self.curr_row, 0)
        data_label = QtWidgets.QLabel("")
        self.labels.append(data_label)
        data_row_layout.addWidget(data_label, self.curr_row, 1)
        data_row_layout.addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), self.curr_row, 2)
        self.grid_main.addWidget(data_row_widget, self.curr_row, 0)
        self.curr_row += 1

        self.grid_main.addItem(QtWidgets.QSpacerItem(0, spacer_size, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding), self.curr_row, 0)
        self.curr_row += 1

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        if self.running:
            self.updateLabels()
        else:
            self.killTimer(self.timer)
            self.close()

    def closeEvent(self, e):
        self.running = False
        self.killTimer(self.timer)
        self.close()

    def reset(self):
        self.prev_count = 0
        for label in self.labels:
            label.setText("?")
