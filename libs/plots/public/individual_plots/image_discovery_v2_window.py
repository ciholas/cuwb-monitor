# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import binascii
import numpy as np
from pyqtgraph import QtCore, QtWidgets
import time

# Local libraries
from cdp import ImageDiscoveryV2
from cdp import ImageV2
from network_objects import *
from settings import *

class ImageDiscoveryV2Window(QtWidgets.QMainWindow):
    type = ImageDiscoveryV2.type
    MAX_NUM_TYPES = 9
    TLV_HEADER_SIZE = 2
    TLV_TYPE__IMAGE_INFORMATION_V2 = 4
    IMAGE_V2_SIZE = 59

    def __init__(self, serial):
        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()  #This will be our central widget
        self.serial = serial
        self.setWindowTitle('CUWB Monitor - Image Discovery v2 ID: 0x{:08X}'.format(serial))
        self.grid_layout = QtWidgets.QGridLayout()

        self.vid_label = QtWidgets.QLabel("VID:N/A")
        self.pid_label = QtWidgets.QLabel("PID:N/A")
        self.running_label = QtWidgets.QLabel("Running:N/A")

        self.grid_layout.addWidget(self.vid_label, 0, 0)
        self.grid_layout.addWidget(self.pid_label, 0, 1)
        self.grid_layout.addWidget(self.running_label, 0, 2)

        self.type_label_list = list()
        self.version_label_list = list()
        self.sha1_label_list = list()

        # Create 3 of each type, version, and sha info labels
        for idx in range(self.MAX_NUM_TYPES):
            self.type_label_list.append(QtWidgets.QLabel("Image:N/A"))
            self.grid_layout.addWidget(self.type_label_list[idx], idx+1, 0)
            self.grid_layout.itemAtPosition(idx+1, 0).widget().hide()
            self.sha1_label_list.append(QtWidgets.QLabel("SHA:N/A"))
            self.grid_layout.addWidget(self.sha1_label_list[idx], idx+1, 1)
            self.grid_layout.itemAtPosition(idx+1, 1).widget().hide()
            self.version_label_list.append(QtWidgets.QLabel("Version:N/A"))
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

        if self.running and UwbNetwork.nodes[self.serial].cdp_pkts_count[ImageDiscoveryV2.type] > 0:
            discovery_pkt = UwbNetwork.nodes[self.serial].cdp_pkts[ImageDiscoveryV2.type][-1]

            # Use cp1525 instead of utf-8 because it utf-8 was causing some issues with unusual characters
            vid_str = discovery_pkt.vid
            pid_str = discovery_pkt.pid
            running_type = discovery_pkt.running_image_type

            type_list = list()
            version_list = list()
            sha_list = list()

            cur_byte = 0
            tlvs_size = len(discovery_pkt.tlvs)
            while cur_byte + self.TLV_HEADER_SIZE < tlvs_size:
                cur_type = discovery_pkt.tlvs[cur_byte]
                cur_size = discovery_pkt.tlvs[cur_byte+1]
                cur_byte += self.TLV_HEADER_SIZE

                # only process image info V2 data for now
                if cur_type != self.TLV_TYPE__IMAGE_INFORMATION_V2:
                    cur_byte += cur_size
                    continue

                # not enough bytes left to parse this type
                if cur_byte + cur_size > tlvs_size:
                    break

                # don't try to parse an ImageV2 TLV with insufficient size
                if cur_size < self.IMAGE_V2_SIZE:
                    continue

                cur_end = cur_byte + cur_size
                cur_image = ImageV2(data=discovery_pkt.tlvs[cur_byte:cur_end])
                type_list.append(cur_image.image_type)
                sha_list.append(binascii.hexlify(cur_image.sha1).decode('cp1252'))
                version_list.append(cur_image.version)
                cur_byte += cur_size

            self.update_data(vid_str, pid_str, running_type, type_list, version_list, sha_list)

    def update_data(self, vid_str, pid_str, running_type, type_list, version_list, sha_list):
        self.vid_label.setText("VID:{:02X}".format(vid_str))
        self.pid_label.setText("PID:{:02X}".format(pid_str))
        self.running_label.setText("Running:"+self.firmware_type_to_str(running_type))

        num_info = len(type_list)

        # Currently only MAX_NUM_TYPES info labels are made available
        if num_info > self.MAX_NUM_TYPES:
            num_info = self.MAX_NUM_TYPES

        # Set the text and show the information that was given
        for idx in range(num_info):
            self.type_label_list[idx].setText("Image:"+self.firmware_type_to_str(type_list[idx]))
            self.grid_layout.itemAtPosition(idx+1, 0).widget().show()
            self.sha1_label_list[idx].setText("SHA:"+sha_list[idx])
            self.grid_layout.itemAtPosition(idx+1, 1).widget().show()
            self.version_label_list[idx].setText("Version:"+version_list[idx])
            self.grid_layout.itemAtPosition(idx+1, 2).widget().show()

        # If there is less than the amount of available information labels, make sure the excess labels are hidden
        if num_info < self.MAX_NUM_TYPES:
            for idx in range(num_info, self.MAX_NUM_TYPES):
                self.grid_layout.itemAtPosition(idx+1, 0).widget().hide()
                self.grid_layout.itemAtPosition(idx+1, 1).widget().hide()
                self.grid_layout.itemAtPosition(idx+1, 2).widget().hide()

    def firmware_type_to_str(self, firmware):
        return {
            0:"Recovery",
            1:"Bootloader",
            2:"Firmware",
            3:"Almanac",
            4:"Reserved",
            5:"Firmware2",
            6:"Etherware",
            7:"Wifi",
            8:"RAM Etherware"
        }.get(firmware, "Unknown")


    def closeEvent(self, e):
        self.running = False
        self.close()

    def reset(self):
        self.vid_label.setText("Manufacturer:N/A")
        self.pid_label.setText("Product:N/A")
        self.running_label.setText("Running:N/A")
        for idx in range(self.MAX_NUM_TYPES):
            self.type_label_list[idx].setText("Image:N/A")
            self.sha1_label_list[idx].setText("SHA:N/A")
            self.version_label_list[idx].setText("Version:N/A")
