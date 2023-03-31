# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

# Local libraries
from cdp import CommandWindowUsageReport
from network_objects import *
from settings import *
from generic_plots import *

class PlotCommandWindowUsageReport(QtWidgets.QMainWindow):
    type = CommandWindowUsageReport.type

    def __init__(self, serial):
        QtWidgets.QMainWindow.__init__(self)
        self.serial = serial

        self.central = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)

        self.setWindowTitle("CUWB Monitor- Command Window Usage Report")
        length = 500
        height = 190
        self.resize(length, height)

        self.sub_windows = {}
        self.createLayout()
        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

    def createLayout(self):
        type_name = CommandWindowUsageReport
        self.command_window_widgets = []
        self.command_window_label_array = []
        grid_rows = []
        curr_row = 0
        total_rows = 3
        spacer_size = 20
        command_window_row_idx = 0
        
        
        self.COMMAND_WINDOW_TOTAL_CLICKABLE = 6
        self.AVG_USED_WINDOWS_IDX = 0
        self.AVG_REUSED_TRANSMISSIONS_IDX = 1
        self.AVG_BYTES_PER_PACKET_IDX = 2
        self.AVG_COMMAND_DROPS_PER_SECOND_IDX = 3
        self.PRESCHEDULE_SIZE_IDX = 4
        self.CURRENT_USED_PRESCHEDULE_SLOTS_IDX = 5

        createRows(self.command_window_widgets, grid_rows, self.grid_layout, command_window_row_idx, total_rows)
        createLabels(self.command_window_label_array, self.COMMAND_WINDOW_TOTAL_CLICKABLE)

        #Row 0
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Average Used Windows: "), 0, 0)
        makeClickable(self.serial, self.command_window_label_array[self.AVG_USED_WINDOWS_IDX], 'Average Used Windows', 'average_used_windows', grid_rows[curr_row], type_name, self.sub_windows, col=1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), 0, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Average Reused Transmissions: "), 0, 3)
        makeClickable(self.serial, self.command_window_label_array[self.AVG_REUSED_TRANSMISSIONS_IDX], 'Average Reused Transmissions', 'average_reused_transmissions', grid_rows[curr_row], type_name, self.sub_windows, col=4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 5)
        curr_row += 1

        #Row 1
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Average Bytes per Packet: "), 0, 0)
        makeClickable(self.serial, self.command_window_label_array[self.AVG_BYTES_PER_PACKET_IDX], 'Average Bytes per Packet', 'average_bytes_per_packet', grid_rows[curr_row], type_name, self.sub_windows, col=1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), 0, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Average Command Drops per Second: "), 0, 3)
        makeClickable(self.serial, self.command_window_label_array[self.AVG_COMMAND_DROPS_PER_SECOND_IDX], 'Average Command Drops per Second', 'average_command_drops_per_second', grid_rows[curr_row], type_name, self.sub_windows, col=4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 5)
        curr_row += 1

        #Row 2
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Preschedule Size: "), 0, 0)
        makeClickable(self.serial, self.command_window_label_array[self.PRESCHEDULE_SIZE_IDX], 'Preschedule Size', 'preschedule_size', grid_rows[curr_row], type_name, self.sub_windows, col=1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), 0, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Currently Used Preschedule Slots: "), 0, 3)
        makeClickable(self.serial, self.command_window_label_array[self.CURRENT_USED_PRESCHEDULE_SLOTS_IDX], 'Currently Used Preschedule Slots', 'current_used_preschedule_slots', grid_rows[curr_row], type_name, self.sub_windows, col=4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 5)

    def updateLabels(self):
        command_window_item_array = [None] * self.COMMAND_WINDOW_TOTAL_CLICKABLE

        if CommandWindowUsageReport.type in UwbNetwork.nodes[self.serial].cdp_pkts_count and UwbNetwork.nodes[self.serial].cdp_pkts_count[CommandWindowUsageReport.type] != 0:
            packet = UwbNetwork.nodes[self.serial].cdp_pkts[CommandWindowUsageReport.type][-1]

            command_window_item_array[self.AVG_USED_WINDOWS_IDX] = "{:0.2}".format(packet.average_used_windows)
            command_window_item_array[self.AVG_REUSED_TRANSMISSIONS_IDX] = "{:0.2}".format(packet.average_reused_transmissions)
            command_window_item_array[self.AVG_BYTES_PER_PACKET_IDX] = "{:0.2}".format(packet.average_bytes_per_packet)
            command_window_item_array[self.AVG_COMMAND_DROPS_PER_SECOND_IDX] = "{:0.2e}".format(packet.average_command_drops_per_second)
            command_window_item_array[self.PRESCHEDULE_SIZE_IDX] = str(packet.preschedule_size)
            command_window_item_array[self.CURRENT_USED_PRESCHEDULE_SLOTS_IDX] = str(packet.current_used_preschedule_slots)

            remakeClickable(self.command_window_label_array, command_window_item_array)
        else:
            removeClickable(self.command_window_label_array, command_window_item_array)

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
        for window in self.sub_windows.values():
            if window.isVisible():
                window.close()
        self.close()

    def reset(self):
        for window in self.sub_windows:
            if self.sub_windows[window].running:
                sub_window_serial = self.sub_windows[window].serial
                sub_window_type_name = self.sub_windows[window].type_name
                sub_window_data_label = self.sub_windows[window].data_label
                sub_window_feature = self.sub_windows[window].feature
                self.sub_windows[window].close()
                self.sub_windows[window] = PlotStatMonitorSubWindow(sub_window_serial, sub_window_type_name, sub_window_data_label, sub_window_feature)
                self.sub_windows[window].show()
