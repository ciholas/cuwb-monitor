# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import binascii
import numpy as np
from pyqtgraph import QtCore, QtGui
import time

# Local libraries
from cdp import ImageDiscoveryV1
from network_objects import *
from settings import *

class ImageDiscoveryWindow(QtGui.QMainWindow):
    type = ImageDiscoveryV1.type

    def __init__(self, serial):
        QtGui.QMainWindow.__init__(self)

        self.central = QtGui.QWidget()  #This will be our central widget
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Image Discovery ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtGui.QGridLayout()

        self.manufacturer_label = QtGui.QLabel("Manufacturer:N/A")
        self.product_label = QtGui.QLabel("Product:N/A")
        self.running_label = QtGui.QLabel("Running:N/A")

        self.grid_layout.addWidget(self.manufacturer_label, 0, 0)
        self.grid_layout.addWidget(self.product_label, 0, 1)
        self.grid_layout.addWidget(self.running_label, 0, 2)

        self.type_label_list = list()
        self.version_label_list = list()
        self.sha1_label_list = list()

        # Create 3 of each type, version, and sha info labels
        for idx in range(3):
            self.type_label_list.append(QtGui.QLabel("Image:N/A"))
            self.grid_layout.addWidget(self.type_label_list[idx], idx+1, 0)
            self.grid_layout.itemAtPosition(idx+1, 0).widget().hide()
            self.sha1_label_list.append(QtGui.QLabel("SHA:N/A"))
            self.grid_layout.addWidget(self.sha1_label_list[idx], idx+1, 1)
            self.grid_layout.itemAtPosition(idx+1, 1).widget().hide()
            self.version_label_list.append(QtGui.QLabel("Version:N/A"))
            self.grid_layout.addWidget(self.version_label_list[idx], idx+1, 2)
            self.grid_layout.itemAtPosition(idx+1, 2).widget().hide()

        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        self.resize(825, 50)

        self.running = True

        self.show()

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        if self.running:
            discovery_pkt = UwbNetwork.nodes[self.serial].cdp_pkts[ImageDiscoveryV1.type][-1]

            # Use cp1525 instead of utf-8 because it utf-8 was causing some issues with unusual characters
            manufacturer_str = discovery_pkt.manufacturer
            product_str = discovery_pkt.product
            running_type = discovery_pkt.running_image_type

            type_list = list()
            version_list = list()
            sha_list = list()

            for image in discovery_pkt.image_information:
                type_list.append(image.type)
                sha_list.append(binascii.hexlify(image.sha1).decode('cp1252'))
                version_list.append(image.version)

            self.update_data(manufacturer_str, product_str, running_type, type_list, version_list, sha_list)

    def update_data(self, manufacturer, product, running_type, type_list, version_list, sha_list):
        self.manufacturer_label.setText("Manufacturer:"+manufacturer)
        self.product_label.setText("Product:"+product)
        self.running_label.setText("Running:"+self.firmware_type_to_str(running_type))

        num_info = len(type_list)

        # Currently only 3 info labels are made available
        if num_info > 3:
            num_info = 3

        # Set the text and show the information that was given
        for idx in range(num_info):
            self.type_label_list[idx].setText("Image:"+self.firmware_type_to_str(type_list[idx]))
            self.grid_layout.itemAtPosition(idx+1, 0).widget().show()
            self.sha1_label_list[idx].setText("SHA:"+sha_list[idx])
            self.grid_layout.itemAtPosition(idx+1, 1).widget().show()
            self.version_label_list[idx].setText("Version:"+version_list[idx])
            self.grid_layout.itemAtPosition(idx+1, 2).widget().show()

        # If there is less than the amount of available information labels, make sure the excess labels are hidden
        if num_info < 3:
            for idx in range(num_info, 3):
                self.grid_layout.itemAtPosition(idx+1, 0).widget().hide()
                self.grid_layout.itemAtPosition(idx+1, 1).widget().hide()
                self.grid_layout.itemAtPosition(idx+1, 2).widget().hide()

    def firmware_type_to_str(self, firmware):
        return {
            0:"Recovery",
            1:"Bootloader",
            2:"Firmware",
            3:"Almanac",
            4:"Application"
        }.get(firmware, "Unknown")


    def closeEvent(self, e):
        self.running = False
        self.close()
