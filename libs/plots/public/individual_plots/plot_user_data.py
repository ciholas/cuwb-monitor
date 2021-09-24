# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from cdp import UserDefinedV1
from network_objects import *
from settings import *


class PlotUserData(pg.GraphicsWindow):
    type = UserDefinedV1.type

    def __init__(self, serial):

        pg.GraphicsWindow.__init__(self)
        self.serial = serial

        self.setWindowTitle('CUWB Monitor - User Data Plot ID: 0x{:08X}'.format(self.serial))
        self.resize(800, 300)

        self.payload_size_graph = self.addPlot(title='Payload Data Size')
        self.payload_data = self.payload_size_graph.plot(pen=pg.mkPen(color='b', width=0), symbolBrush='b')

        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[UserDefinedV1.type]
        self.data = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[UserDefinedV1.type] - self.last_count
        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[UserDefinedV1.type]
        for idx in range(_current_size):
            self.data.append(len(UwbNetwork.nodes[self.serial].cdp_pkts[UserDefinedV1.type][idx - _current_size].payload))
            self.time.append(UwbNetwork.nodes[self.serial].cdp_pkts_time[UserDefinedV1.type][idx - _current_size])

        if _current_size > 0: self.payload_data.setData(np.array(self.time), np.array(self.data))

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.close()
