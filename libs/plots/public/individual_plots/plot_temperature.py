# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from cdp import LPSTemperatureV1
from network_objects import *
from settings import *


class PlotTemperature(pg.GraphicsWindow):
    type = LPSTemperatureV1.type

    def __init__(self, serial):

        pg.GraphicsWindow.__init__(self)

        self.setWindowTitle('CUWB Monitor - Temperature Plot ID: 0x{:08X}'.format(serial))
        self.resize(900,500)
        self.serial = serial

        self.graph_window = self.addPlot(title='C')
        self.graph_window.addLegend()
        self.graph_window.showGrid(x=True, y=True)
        self.temperature = self.graph_window.plot(pen=pg.mkPen('b', width=3), name='Temperature')

        self.timer = self.startTimer(QPLOT_FREQUENCY)

        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[LPSTemperatureV1.type]
        self.data = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)
        _current_size = len(UwbNetwork.nodes[self.serial].cdp_pkts[LPSTemperatureV1.type])
        for idx in range(_current_size):
            self.data.append(UwbNetwork.nodes[self.serial].cdp_pkts[LPSTemperatureV1.type][idx - _current_size].temperature / 480.0 + 42.5)
            self.time.append(UwbNetwork.nodes[self.serial].cdp_pkts_time[LPSTemperatureV1.type][idx - _current_size])


    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[LPSTemperatureV1.type] - self.last_count
        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[LPSTemperatureV1.type]
        if _current_size == 0: return

        for idx in range(_current_size):
            self.data.append(UwbNetwork.nodes[self.serial].cdp_pkts[LPSTemperatureV1.type][idx - _current_size].temperature / 480.0 + 42.5)
            self.time.append(UwbNetwork.nodes[self.serial].cdp_pkts_time[LPSTemperatureV1.type][idx - _current_size])

        self.temperature.setData(np.array(self.time), np.array(self.data))

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.close()
