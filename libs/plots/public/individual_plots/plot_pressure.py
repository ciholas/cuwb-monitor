# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

# Local libraries
from cdp import LPSPressureV1
from network_objects import *
from settings import *


class PlotPressure(pg.GraphicsLayoutWidget):
    type = LPSPressureV1.type

    def __init__(self, serial):

        pg.GraphicsLayoutWidget.__init__(self)

        self.setWindowTitle('CUWB Monitor - Pressure Plot ID: 0x{:08X}'.format(serial))
        self.resize(900, 500)
        self.serial = serial

        self.graph_window = self.addPlot(title='milliBars')
        self.graph_window.addLegend()
        self.graph_window.showGrid(x=True, y=True)
        self.pressure = self.graph_window.plot(pen=pg.mkPen('b', width=3), name='Pressure')

        self.timer = self.startTimer(QPLOT_FREQUENCY)

        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[LPSPressureV1.type]
        self.data = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)
        _current_size = len(UwbNetwork.nodes[self.serial].cdp_pkts[LPSPressureV1.type])
        for idx in range(_current_size):
            self.data.append(UwbNetwork.nodes[self.serial].cdp_pkts[LPSPressureV1.type][idx - _current_size].pressure / 4096.0)
            self.time.append(UwbNetwork.nodes[self.serial].cdp_pkts_time[LPSPressureV1.type][idx - _current_size])


    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[LPSPressureV1.type] - self.last_count
        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[LPSPressureV1.type]
        if _current_size == 0: return

        for idx in range(_current_size):
            self.data.append(UwbNetwork.nodes[self.serial].cdp_pkts[LPSPressureV1.type][idx - _current_size].pressure / 4096.0)
            self.time.append(UwbNetwork.nodes[self.serial].cdp_pkts_time[LPSPressureV1.type][idx - _current_size])

        if len(self.time) > 1:
            self.pressure.setData(np.array(self.time), np.array(self.data))

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.close()

    def reset(self):
        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[LPSPressureV1.type]
        self.data.clear()
        self.time.clear()