# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

from pyqtgraph import QtCore, QtGui

from displays import *
from plots import *


class AggregatePlotWindow(QtGui.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CUWB Monitor - Aggregate Plots")
        self.central = QtGui.QWidget()
        self.grid_layout = QtGui.QGridLayout()
        self.plot_windows = dict()

        self.plot_labels = dict()
        self.aggregate_plot_cnt = 0
        for plot_type in sorted(list(map_type_to_aggregate_plot.keys())):
            self.plot_labels.update([(plot_type, QtGui.QLabel(plot_type))])
            self.plot_labels[plot_type].setStyleSheet('color: blue')
            self.plot_labels[plot_type].mouseReleaseEvent = partial(self.plotClickEvent, plot_type)
            self.aggregate_plot_cnt += 1
            self.grid_layout.addWidget(self.plot_labels[plot_type], self.aggregate_plot_cnt, 0)

        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        self.resize(375, 20 + self.aggregate_plot_cnt * 20)

    def plotClickEvent(self, type_value, e):
        _tmp_plot = partial(map_type_to_aggregate_plot[type_value])
        self.plot_windows.update([(type_value, _tmp_plot())])
        self.plot_windows[type_value].show()

    def reset(self):
        for window in self.plot_windows.values():
            if window.isVisible():
                reset_method = getattr(window, 'reset', None)
                if callable(reset_method):
                    window.reset()

    def closeEvent(self, e):
        for window in self.plot_windows.values():
            if window.isVisible():
                window.close()
