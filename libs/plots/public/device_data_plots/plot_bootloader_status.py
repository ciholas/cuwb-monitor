# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from functools import partial

# Local libraries
from device_data_items import BootloaderStatus
from network_objects import *
from settings import *
from generic_plots import *

class PlotBootloaderStatus(QtWidgets.QMainWindow):
    type = BootloaderStatus.type

    def __init__(self, device):
        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()
        self.setWindowTitle("CUWB Monitor- Bootloader Status Device: 0x{:08X}".format(device.id))
        self.device = device
        self.running = True

        self.grid_main = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_main)
        self.setCentralWidget(self.central)
        
        length = 400
        width = 150
        self.resize(length, width)

        self.createLayout()
        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def createLayout(self):
        self.bootload_widgets = []
        grid_rows = []
        first_row = 0
        total_rows = 3

        createRows(self.bootload_widgets, grid_rows, self.grid_main, first_row, total_rows)

        curr_row = 0
        spacer_size = 20

        #Row 0
        graphics = pg.GraphicsLayoutWidget(show = False)
        graphics.setFixedSize(380.0,70.0)
        grid_rows[curr_row].addWidget(graphics, 0, 0)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 1)
        graphics.ci.setContentsMargins(0,0,0,0)
        self.flags_progress = pg.ImageItem()
        #Pyqtgraph color schemes made it to where the unset flags are 1 and set flags are 0
        self.flags_progress.setImage(np.ones((200,1)))
        flags_viewer = graphics.addViewBox()
        flags_viewer.setMouseEnabled(False, False)
        flags_viewer.setAspectLocked(False)
        #flags_viewer.setRange(rect = graphics.ci.boundingRect())
        flags_viewer.addItem(self.flags_progress)
        color_scheme = pg.colormap.get("CET-D3")
        flags_color = pg.ColorBarItem(values = (0,1), colorMap = color_scheme)
        flags_color.setImageItem(self.flags_progress)
        curr_row += 1

        #Row 1
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Last Signal's Strength: "), curr_row, 0)
        self.last_packet_rssi_label = QtWidgets.QLabel("?")
        grid_rows[curr_row].addWidget(self.last_packet_rssi_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), curr_row, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Last Heard Packet Time: "), curr_row, 3)
        self.last_packet_time_label = QtWidgets.QLabel("?")
        grid_rows[curr_row].addWidget(self.last_packet_time_label, curr_row, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), curr_row, 5)
        curr_row += 1

        #Row 2
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Max # of Sectors per Flag: "), curr_row, 0)
        self.max_sectors_label = QtWidgets.QLabel("?")
        grid_rows[curr_row].addWidget(self.max_sectors_label, curr_row, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), curr_row, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Last Max Sector Flag: "), curr_row, 3)
        self.last_max_sector_label = QtWidgets.QLabel("?")
        grid_rows[curr_row].addWidget(self.last_max_sector_label, curr_row, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), curr_row, 5)
        curr_row += 1

        self.updateLabels()

    def updateLabels(self):
        if BootloaderStatus.type in self.device.names.keys() and self.device.counts[BootloaderStatus.type] != 0:
            packet = self.device.packets[BootloaderStatus.type][-1]
            MAX_SIGNAL_STRENGTH = 255
            self.last_packet_rssi_label.setText("{}%".format(((packet.last_total_path/MAX_SIGNAL_STRENGTH)*100)))
            self.last_packet_time_label.setText("{}s".format(packet.time_previous_packet))
            self.max_sectors_label.setText("{}".format(packet.max_sectors_per_flag))
            self.last_max_sector_label.setText("{}".format(packet.last_max_sector_flag))
            flags = []
            #Parse each byte down into a list of bool and then if the boolean is true that means the flag is set
            for byte in packet.sector_flags:
                flags_of_byte = [bool(byte & (1<<n)) for n in range(8)]
                for flag in flags_of_byte:
                    #Pyqtgraph color schemes made it to where the unset flags are 1 and set flags are 0
                    if flag:
                        flags.append([0])
                    else:
                        flags.append([1])
            flags_array = np.array(flags)
            self.flags_progress.setImage(flags_array)

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
        self.last_packet_rssi_label.setText("?")
        self.last_packet_time_label.setText("?")
        self.max_sectors_label.setText("?")
        self.last_max_sector_label.setText("?")
        self.flags_progress.setValue(0)
