# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

#System Libraries
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtWidgets, QtCore
from functools import partial

#Local Libraries
from device_data_items import PersistentPropertyGetTypesResponse
from network_objects import *
from settings import *

class PlotPersistentPropertyGetTypesResponse(QtWidgets.QMainWindow):
    type = PersistentPropertyGetTypesResponse.type

    def __init__(self, device):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()
        self.setWindowTitle("CUWB Monitor- Persistent Property Get Types Response Device 0x{:08X}".format(device.id))
        self.device = device
        self.running = True

        self.grid_main = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_main)
        self.setCentralWidget(self.central)

        length = 300
        width = 80
        self.resize(length, width)

        row_widget = QtWidgets.QWidget()
        row_layout = QtWidgets.QGridLayout()
        row_layout.setHorizontalSpacing(0)
        row_layout.setVerticalSpacing(0)
        row_layout.setSpacing(0)
        row_widget.setLayout(row_layout)
        row_layout.addWidget(QtWidgets.QLabel("Total Types: "), 0, 0)
        self.total_types_label = QtWidgets.QLabel("")
        row_layout.addWidget(self.total_types_label, 0, 1)
        row_layout.addItem(QtWidgets.QSpacerItem(5, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 2)
        self.grid_main.addWidget(row_widget, 0, 0)

        self.prev_count = self.device.counts[PersistentPropertyGetTypesResponse.type] - len(self.device.packets[PersistentPropertyGetTypesResponse.type])
        self.greatest_offset = -1
        self.offsets = []
        self.labels = []
        self.rows = []
        self.spacers = []
        self.curr_row = 1

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.updateLabels()

    def updateLabels(self):
        curr_count = self.device.counts[PersistentPropertyGetTypesResponse.type]
        if curr_count > 0: self.total_types_label.setText(str(self.device.packets[PersistentPropertyGetTypesResponse.type][-1].total_types))
        if curr_count - self.prev_count > 1000: self.prev_count = curr_count - 1000
        while self.prev_count < curr_count:
            index = self.prev_count - curr_count
            packet = self.device.packets[PersistentPropertyGetTypesResponse.type][index]

            #If the offset goes down it is assumed to be a new set of data and the previous set must be deleted first.
            if packet.offset < self.greatest_offset:
                self.greatest_offset = -1
                self.offsets.clear()
                self.labels.clear()
                for row in self.rows:
                    self.grid_main.removeWidget(row)
                    row.deleteLater()
                self.rows.clear()
                for spacer in self.spacers:
                    self.grid_main.removeItem(spacer)
                    del spacer
                self.spacers.clear()

            if not packet.offset in self.offsets:
                if packet.offset > self.greatest_offset: self.greatest_offset = packet.offset
                self.offsets.append(packet.offset)
                self.addOffsetLabels()
            #Every 2 entries in self.labels is a new offset
            offset_idx = 2 * self.offsets.index(packet.offset)
            self.labels[offset_idx].setText(str(packet.offset))
            types = ""
            for single_property in sorted(packet.types):
                types += "0x{:04X}, ".format(single_property)
            self.labels[offset_idx+1].setText(types)
            self.prev_count += 1
        

    def addOffsetLabels(self):
        spacer_size = 20

        row_widget = QtWidgets.QWidget()
        self.rows.append(row_widget)
        row_layout = QtWidgets.QGridLayout()
        row_layout.setHorizontalSpacing(0)
        row_layout.setVerticalSpacing(0)
        row_layout.setSpacing(0)
        row_widget.setLayout(row_layout)
        row_layout.addWidget(QtWidgets.QLabel("Offset: "), 0, 0)
        offset_label = QtWidgets.QLabel()
        self.labels.append(offset_label)
        row_layout.addWidget(offset_label, 0, 1)
        row_layout.addItem(QtWidgets.QSpacerItem(spacer_size, 0), 0, 2)
        row_layout.addWidget(QtWidgets.QLabel("Types: "), 0, 3)
        types_label = QtWidgets.QLabel()
        self.labels.append(types_label)
        row_layout.addWidget(types_label, 0, 4)
        row_layout.addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 5)
        self.grid_main.addWidget(row_widget, self.curr_row, 0)
        self.curr_row += 1

        spacer = QtWidgets.QSpacerItem(0, spacer_size, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.spacers.append(spacer)
        self.grid_main.addItem(spacer, self.curr_row, 0)
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
        self.total_types_label.setText("?")
        for label in self.labels:
            label.setText("?")
