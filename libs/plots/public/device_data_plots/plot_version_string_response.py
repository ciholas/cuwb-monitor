# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

#System Libraries
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtWidgets, QtCore
from functools import partial

#Local Libraries
from device_data_items import VersionStringResponse
from network_objects import *
from generic_plots import *
from settings import *

class PlotVersionStringResponse(QtWidgets.QMainWindow):
    type = VersionStringResponse.type

    def __init__(self, device):

        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()
        self.setWindowTitle("CUWB Monitor- Version String Response Device 0x{:08X}".format(device.id))
        self.device = device
        self.running = True

        self.grid_main = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_main)
        self.setCentralWidget(self.central)

        length = 200
        width = 100
        self.resize(length, width)

        upgrade_type_label = QtWidgets.QLabel("Upgrade Type: ")
        sha1_ending_label = QtWidgets.QLabel("SHA1 Ending: ")
        version_string_label = QtWidgets.QLabel("Version String :")
        self.upgrade_field_label = QtWidgets.QLabel("")
        self.sha1_field_label = QtWidgets.QLabel("")
        self.version_field_label = QtWidgets.QLabel("")

        self.grid_main.addWidget(upgrade_type_label, 0, 0)
        self.grid_main.addWidget(self.upgrade_field_label, 0, 1)
        self.grid_main.addWidget(sha1_ending_label, 1, 0)
        self.grid_main.addWidget(self.sha1_field_label, 1, 1)
        self.grid_main.addWidget(version_string_label, 2, 0)
        self.grid_main.addWidget(self.version_field_label, 2, 1)

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.updateLabels()

    def updateLabels(self):
        if VersionStringResponse.type in self.device.names.keys() and self.device.counts[VersionStringResponse.type] != 0:
            most_recent_packet = self.device.packets[VersionStringResponse.type][-1]
            self.upgrade_field_label.setText(str(most_recent_packet.upgrade_type))
            self.sha1_field_label.setText(hex(most_recent_packet.sha1_ending))
            self.version_field_label.setText(str(most_recent_packet.version))

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
        self.killTimer(self.timer)
        self.close()

    def reset(self):
        self.upgrade_field_label.setText("?")
        self.sha1_field_label.setText("?")
        self.version_field_label.setText("?")
