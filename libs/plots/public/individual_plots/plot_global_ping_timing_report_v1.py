# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from cdp import GlobalPingTimingReportV1
from network_objects import *
from settings import *


class PlotGlobalPingTimingReportV1(pg.GraphicsWindow):
    type = GlobalPingTimingReportV1.type

    def UpdatePlot(self):
        pos_calc_delay = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][-1].position_calculation_delay
        time_counts = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][-1].arrival_time_counts

        self.plot.setData(self.indexes, time_counts)
        self.timeout_plot.setData([pos_calc_delay, pos_calc_delay], [0, np.max(time_counts)])

    def __init__(self, serial):

        pg.GraphicsWindow.__init__(self)

        self.setWindowTitle('CUWB Monitor - Global Ping Timing Report Plot ID: 0x{:08X}'.format(serial))
        self.resize(900, 500)
        self.serial = serial

        self.graph = self.addPlot()
        self.legend = self.graph.addLegend()
        self.plot = self.graph.plot(pen='b', fillLevel=1.0, name='Arrival Time Histogram')
        self.timeout_plot = self.graph.plot(pen='r', name='Timeout')
        self.graph.showGrid(x=True, y=True)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

        self.indexes = np.arange(GlobalPingTimingReportV1.num_time_count_indexes)
        self.data = deque([], GlobalPingTimingReportV1.num_time_count_indexes)

        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
        _current_size = len(UwbNetwork.nodes[self.serial].cdp_pkts[self.type])

        if (_current_size > 0):
            self.UpdatePlot()

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - self.last_count
        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]

        if _current_size > 0:
            self.UpdatePlot()

    def closeEvent(self, e):
        self.killTimer(self.timer)

    def reset(self):
        self.plot.clear()
        self.timeout_plot.clear()
