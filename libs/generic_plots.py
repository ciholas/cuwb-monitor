# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from functools import partial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from network_objects import *
from settings import *

class PlotStatMonitorSubWindow(pg.GraphicsWindow):

    def __init__(self, serial, type_name, data_label, feature):
        self.type_name = type_name
        self.feature = feature
        self.running = True

        pg.GraphicsWindow.__init__(self)
        length = 900
        width = 500

        self.setWindowTitle('Cuwb Monitor - {} Plot ID: 0x{:08X}'.format(data_label, serial))
        self.resize(length, width)
        self.serial = serial

        self.timer = self.startTimer(QPLOT_FREQUENCY)

        self.graph = self.addPlot(title='')
        self.graph.showGrid(x=True, y=True)
        self.plot= self.graph.plot(pen='b', name=data_label)

        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type_name.type]
        self.data = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)
        _current_size = len(UwbNetwork.nodes[self.serial].cdp_pkts[self.type_name.type])

        self.updateTime(_current_size)

    def timerEvent(self, e):
        if not self.running:
            self.killTimer(self.timer)
            self.close()
            return

        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type_name.type] - self.last_count
        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type_name.type]
        if _current_size == 0: return

        self.updateTime(_current_size)

        _data = np.array(self.data)
        _times = np.array(self.time)

        self.plot.setData(_times, _data)

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.close()

    def updateTime(self, _current_size):

        if _current_size > TRAIL_LENGTH: _current_size = TRAIL_LENGTH
        for idx in range(_current_size):
            self.data.append(getattr(UwbNetwork.nodes[self.serial].cdp_pkts[self.type_name.type][idx - _current_size], self.feature))
            self.time.append(UwbNetwork.nodes[self.serial].cdp_pkts_time[self.type_name.type][idx - _current_size])


def makeClickable(serial, label_to_change, data_label, feature, grid_row, type_name, sub_windows, col):
    label_to_change.setStyleSheet('color:blue')
    label_to_change.mouseReleaseEvent = partial(labelClickEvent, serial, data_label, feature, type_name, sub_windows)
    grid_row.addWidget(label_to_change, 0, col)

def labelClickEvent(serial, data_label, feature, type_name, sub_windows, e):
    sub_windows.update([(data_label, PlotStatMonitorSubWindow(serial, type_name, data_label, feature))])

def createRows(widgets_array, grid_rows, grid_main, row_idx, total_rows):
    while len(widgets_array) < total_rows:
        row_widget = QtGui.QWidget()
        grid_row_layout = QtGui.QGridLayout()
        grid_row_layout.setHorizontalSpacing(0)
        grid_row_layout.setVerticalSpacing(0)
        grid_row_layout.setMargin(0)
        row_widget.setLayout(grid_row_layout)
        widgets_array.append(row_widget)
        grid_rows.append(grid_row_layout)
        grid_main.addWidget(row_widget, row_idx, 0)
        row_idx += 1

def createLabels(label_array, total_clickable):
    while len(label_array) < total_clickable:
        label = QtGui.QLabel();
        label_array.append(label)

def assignLabelText(item_array, label_array):
    for item_idx in range(len(item_array)):
        label_array[item_idx].setText(item_array[item_idx])

def removeClickable(label_to_change_array, item_to_change_array):
    MISSING_INFO = '?'
    for changed_idx in range(len(label_to_change_array)):
        label_to_change_array[changed_idx].setStyleSheet('color:black')
        label_to_change_array[changed_idx].setEnabled(False)
        item_to_change_array[changed_idx] = MISSING_INFO

    assignLabelText(item_to_change_array, label_to_change_array)

def remakeClickable(label_to_change_array, item_to_change_array):
    for changed_idx in range(len(label_to_change_array)):
        label_to_change_array[changed_idx].setStyleSheet('color:blue')
        label_to_change_array[changed_idx].setEnabled(True)

    assignLabelText(item_to_change_array, label_to_change_array)