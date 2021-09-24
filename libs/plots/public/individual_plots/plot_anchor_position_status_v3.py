# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from cdp import AnchorPositionStatusV3
from network_objects import *
from settings import *


class PlotAnchorPositionStatusV3(pg.GraphicsWindow):
    type = AnchorPositionStatusV3.type

    def __init__(self, serial):

        pg.GraphicsWindow.__init__(self)

        self.setWindowTitle('CUWB Monitor - Position Stats Plot ID: 0x{:08X}'.format(serial))
        self.resize(900, 500)
        self.serial = serial

        self.graph = self.addPlot(title='')
        self.graph.showGrid(x=True, y=True)
        self.legend = self.graph.addLegend()
        self.num_good_plot = self.graph.plot(pen='g', name='Number of Good Anchors')
        self.num_fill_plot = self.graph.plot(pen='b', name='Number of Fill Anchors')
        self.num_bad_plot = self.graph.plot(pen='r', name='Number of Bad Anchors')

        self.timer = self.startTimer(QPLOT_FREQUENCY)

        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
        self.num_good_anchors = deque([], TRAIL_LENGTH)
        self.num_bad_anchors = deque([], TRAIL_LENGTH)
        self.num_fill_anchors = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - self.last_count
        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
        if _current_size == 0: return

        for idx in range(_current_size):
            _num_good_anchors = 0
            _num_bad_anchors = 0
            _num_fill_anchors = 0

            for anchor in UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].anchor_status_array:
                if anchor.status == 0:
                    _num_good_anchors += 1
                elif anchor.status == 7:
                    _num_fill_anchors += 1
                else:
                    _num_bad_anchors += 1

            self.num_good_anchors.append(_num_good_anchors)
            self.num_bad_anchors.append(_num_bad_anchors)
            self.num_fill_anchors.append(_num_fill_anchors)
            self.time.append(UwbNetwork.nodes[self.serial].cdp_pkts_time[self.type][idx - _current_size])

        _num_good_data = np.array(self.num_good_anchors)
        _num_fill_data = np.array(self.num_fill_anchors)
        _num_bad_data = np.array(self.num_bad_anchors)
        _times = np.array(self.time)
        self.num_good_plot.setData(_times, _num_good_data)
        self.num_fill_plot.setData(_times, _num_fill_data)
        self.num_bad_plot.setData(_times, _num_bad_data)


    def closeEvent(self, e):
        self.killTimer(self.timer)

    def reset(self):
        self.num_good_anchors = deque([], TRAIL_LENGTH)
        self.num_bad_anchors = deque([], TRAIL_LENGTH)
        self.num_fill_anchors = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)
